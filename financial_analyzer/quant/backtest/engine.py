"""月频调仓回测引擎"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from ..models import FactorMatrix, StockInfo
from ..universe import UniverseManager
from ..data_fetcher import QuantDataFetcher, FACTOR_DATA_TYPES
from ..engine.factor_matrix import FactorMatrixBuilder
from ..engine.normalizer import CrossSectionalNormalizer
from ..engine.scorer import WeightedScorer
from ..engine.ranker import Ranker
from ..engine.optimizer import ConstraintOptimizer
from ..engine.signal import SignalGenerator
from ..engine.factor_analyzer import FactorAnalyzer
from .metrics import MetricsCalculator, PerformanceMetrics
from .attribution import FactorAttribution
from .benchmark import BenchmarkComparator
from .models import BacktestResult, PortfolioSnapshot

logger = logging.getLogger(__name__)

# 默认交易成本
DEFAULT_COMMISSION_RATE = 0.001  # 0.1%


class BacktestEngine:
    """月频调仓回测循环"""

    def __init__(self,
                 universe_manager: UniverseManager,
                 data_fetcher: QuantDataFetcher,
                 factor_matrix_builder: FactorMatrixBuilder,
                 normalizer: CrossSectionalNormalizer,
                 scorer: WeightedScorer,
                 ranker: Ranker,
                 optimizer: ConstraintOptimizer,
                 signal_generator: SignalGenerator,
                 commission_rate: float = DEFAULT_COMMISSION_RATE,
                 factor_analyzer: Optional[FactorAnalyzer] = None,
                 benchmark_code: Optional[str] = None):
        self.universe_manager = universe_manager
        self.data_fetcher = data_fetcher
        self.factor_matrix_builder = factor_matrix_builder
        self.normalizer = normalizer
        self.scorer = scorer
        self.ranker = ranker
        self.optimizer = optimizer
        self.signal_generator = signal_generator
        self.commission_rate = commission_rate
        self.factor_analyzer = factor_analyzer
        self.benchmark_code = benchmark_code

    def run(self,
            start_date: str,
            end_date: str,
            pool: str = "沪深300",
            initial_capital: float = 5000.0,
            progress_callback=None) -> BacktestResult:
        """运行回测

        Args:
            start_date: 回测起始日期 YYYYMMDD
            end_date: 回测结束日期 YYYYMMDD
            pool: 选股池名称
            initial_capital: 初始资金
            progress_callback: 可选的进度回调，接收 0.0-1.0 浮点数
        """
        logger.info(f"回测启动: {start_date} ~ {end_date}, 选股池={pool}, 初始资金={initial_capital}")

        # 1. 获取月末交易日序列
        month_ends = self._generate_month_ends(start_date, end_date)
        if not month_ends:
            logger.warning("无有效月末日期，返回空结果")
            return BacktestResult(
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                final_value=initial_capital,
            )

        logger.info(f"共 {len(month_ends)} 个月末调仓日")

        # 2. 初始化组合状态
        cash = initial_capital
        holdings: dict[str, float] = {}  # {stock_code: shares}
        portfolio_values: list[float] = []
        snapshots: list[PortfolioSnapshot] = []
        all_trades: list = []
        factor_matrix_history: list[FactorMatrix] = []
        factor_scores_history: list[tuple[date, dict[str, dict[str, float]]]] = []
        monthly_forward_returns: list[tuple[date, dict[str, float]]] = []

        # 2.5 预取全量数据（一次性获取，后续按日期切片）
        logger.info("预取全量数据（一次性获取，避免逐月重复调用 API）...")
        if progress_callback:
            progress_callback(0.0)
        stocks_all = self.universe_manager.get_universe(pool)
        if stocks_all:
            if len(stocks_all) > 500:
                stocks_all = stocks_all[:500]
            stocks_all = self.data_fetcher.enrich_stock_info(stocks_all)
            self._prefetched_data = self.data_fetcher.fetch_all(stocks_all)
            self._prefetched_stocks = stocks_all
            logger.info(f"预取完成: {len(self._prefetched_data)} 只股票数据已加载到内存")
        else:
            self._prefetched_data = {}
            self._prefetched_stocks = []

        # 3. 逐月回测
        for i, rebal_date in enumerate(month_ends):
            if progress_callback:
                progress_callback(i / len(month_ends))
            ref_date_str = rebal_date.strftime("%Y%m%d")
            logger.info(f"[{i+1}/{len(month_ends)}] 调仓日: {ref_date_str}")

            # 3a. 获取选股池成分股（使用回测日期的历史成分股）
            stocks = self._get_universe_at_date(pool, rebal_date)
            if not stocks:
                logger.warning(f"  选股池为空，跳过")
                # 记录当前组合价值（不变）
                portfolio_values.append(self._calc_portfolio_value(holdings, cash, {}, rebal_date))
                continue

            # 3b. 补充股票信息并获取历史数据
            stocks = self.data_fetcher.enrich_stock_info(stocks)
            stock_data = self._fetch_data_for_date(stocks, rebal_date)

            # 提取最新价格（用于排名过滤和组合估值）
            prices = self._extract_prices(stock_data)

            # 应用硬过滤
            stocks = self.universe_manager.apply_filters(
                stocks, prices=prices, today=rebal_date
            )

            if not stocks:
                logger.warning(f"  过滤后无有效股票")
                portfolio_values.append(self._calc_portfolio_value(holdings, cash, prices, rebal_date))
                continue

            # 3c. 构建因子矩阵
            matrix = self.factor_matrix_builder.build(stocks, stock_data)
            if not matrix.stocks:
                logger.warning(f"  因子矩阵为空")
                portfolio_values.append(self._calc_portfolio_value(holdings, cash, prices, rebal_date))
                continue

            # 记录因子矩阵用于归因分析
            factor_matrix_history.append(matrix)
            factor_scores_history.append(
                (rebal_date, {stock: dict(scores) for stock, scores in matrix.scores.items()})
            )

            # 3d. 标准化 → 打分 → 排名 → 优化
            matrix = self.normalizer.normalize(matrix)

            # 3d-ic. 计算前瞻收益（用于 IC 分析和年度表现）
            fwd_returns: dict[str, float] = {}
            if self.factor_analyzer and i + 1 < len(month_ends):
                next_date = month_ends[i + 1]
                fwd_returns = self._compute_forward_returns(
                    stocks, rebal_date, next_date
                )
                if fwd_returns:
                    monthly_forward_returns.append((rebal_date, fwd_returns))
                    self.factor_analyzer.compute_monthly_ic(
                        matrix, fwd_returns, ref_date=rebal_date
                    )

            # 存储因子截面数据用于相关性矩阵和年度分组
            if self.factor_analyzer:
                self.factor_analyzer.store_monthly_matrix(
                    {stock: dict(scores) for stock, scores in matrix.scores.items()},
                    ref_date=rebal_date,
                    market_returns=fwd_returns if fwd_returns else None,
                )

            scores = self.scorer.score(matrix)
            ranked = self.ranker.rank(scores, stocks, prices=prices)
            optimized = self.optimizer.optimize(ranked, scores)

            # 3e. 生成调仓信号
            current_codes = set(holdings.keys())
            trade_list = self.signal_generator.generate(
                optimized, scores, current_codes, pool, ref_date=rebal_date
            )
            all_trades.append(trade_list)

            # 3f. 执行交易
            cash = self._execute_trades(
                trade_list, holdings, cash, prices, rebal_date
            )

            # 3g. 记录组合快照
            total_value = self._calc_portfolio_value(holdings, cash, prices, rebal_date)
            portfolio_values.append(total_value)

            weights = self._calc_weights(holdings, cash, prices, total_value)
            snapshots.append(PortfolioSnapshot(
                date=ref_date_str,
                holdings=weights,
                cash=round(cash, 2),
                total_value=round(total_value, 2),
            ))

            logger.info(f"  组合市值: {total_value:.2f}, 持仓: {len(holdings)} 只, 现金: {cash:.2f}")

        # 4. 计算绩效指标
        metrics = MetricsCalculator.compute(portfolio_values)

        # 5. 因子归因
        attribution = {}
        if factor_matrix_history and metrics.monthly_returns:
            fa = FactorAttribution()
            attribution = fa.compute_attribution(
                factor_matrix_history, metrics.monthly_returns
            )

        # 6. 因子 IC 汇总
        factor_ic = {}
        if self.factor_analyzer:
            ic_summaries = self.factor_analyzer.compute_ic_summary()
            factor_ic = {
                name: {
                    "mean_ic": round(s.mean_ic, 6),
                    "std_ic": round(s.std_ic, 6),
                    "ir": round(s.ir, 4),
                    "ic_positive_pct": round(s.ic_positive_pct, 4),
                    "t_stat": round(s.t_stat, 4),
                    "n_months": s.n_months,
                }
                for name, s in ic_summaries.items()
            }
            factor_ic["_timeseries"] = self.factor_analyzer.get_ic_timeseries()

        # 7. 因子衰减分析
        factor_decay = {}
        if self.factor_analyzer and factor_scores_history and month_ends:
            horizons = [1, 2, 3, 6]
            for ref_date, factor_vals in factor_scores_history:
                fwd_by_horizon: dict[int, dict[str, float]] = {}
                for h in horizons:
                    target_idx = month_ends.index(ref_date) + h if ref_date in month_ends else -1
                    if 0 <= target_idx < len(month_ends):
                        fwd = self._compute_forward_returns(
                            self._prefetched_stocks if hasattr(self, '_prefetched_stocks') else [],
                            ref_date, month_ends[target_idx],
                        )
                        if fwd:
                            fwd_by_horizon[h] = fwd
                if fwd_by_horizon:
                    self.factor_analyzer.compute_multi_horizon_ic(
                        factor_vals, fwd_by_horizon, ref_date=ref_date
                    )
            decay_curves = self.factor_analyzer.compute_decay_curve()
            factor_decay = {
                name: {
                    "horizons": curve.horizons,
                    "mean_ic": [round(v, 6) for v in curve.mean_ic_by_horizon],
                    "ic_positive_pct": [round(v, 4) for v in curve.ic_positive_pct_by_horizon],
                    "n_months": curve.n_months_by_horizon,
                }
                for name, curve in decay_curves.items()
            }

        # 8. 因子相关性矩阵
        correlation_matrix = {}
        if self.factor_analyzer:
            labels, matrix_data = self.factor_analyzer.compute_correlation_matrix()
            if labels:
                correlation_matrix = {"labels": labels, "matrix": matrix_data}

        # 9. 年度因子表现 + 综合评分
        annual_performance = {}
        composite_score_list = []
        if self.factor_analyzer:
            annual_performance = self.factor_analyzer.compute_annual_performance(
                monthly_forward_returns
            )
            composite_score_list = self.factor_analyzer.compute_composite_score()

        final_value = portfolio_values[-1] if portfolio_values else initial_capital

        # 4.5 基准指数对比
        benchmark_returns_list = []
        excess_returns_list = []
        information_ratio = 0.0
        tracking_error = 0.0
        benchmark_code_str = ""
        if self.benchmark_code and metrics.monthly_returns:
            try:
                benchmark_monthly = self._compute_benchmark_monthly_returns(
                    self.benchmark_code, start_date, end_date, month_ends
                )
                if benchmark_monthly:
                    benchmark_code_str = self.benchmark_code
                    benchmark_returns_list = [round(r, 6) for r in benchmark_monthly]
                    port_series = pd.Series(metrics.monthly_returns)
                    bench_series = pd.Series(benchmark_monthly)
                    comparator = BenchmarkComparator(self.benchmark_code)
                    comparison = comparator.compute_full_comparison(port_series, bench_series)
                    excess_returns_list = comparison["excess_returns"]
                    information_ratio = comparison["information_ratio"]
                    tracking_error = comparison["tracking_error"]
                    logger.info(
                        f"基准对比({self.benchmark_code}): "
                        f"信息比率={information_ratio}, 跟踪误差={tracking_error}"
                    )
            except Exception as e:
                logger.warning(f"基准对比失败（降级为无基准模式）: {e}")

        logger.info(
            f"回测完成: 总收益率={metrics.total_return:.2%}, "
            f"年化={metrics.annualized_return:.2%}, "
            f"夏普={metrics.sharpe_ratio:.2f}, "
            f"最大回撤={metrics.max_drawdown:.2%}"
        )

        return BacktestResult(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            final_value=round(final_value, 2),
            metrics=metrics,
            snapshots=snapshots,
            trades=all_trades,
            attribution=attribution,
            factor_ic=factor_ic,
            factor_decay=factor_decay,
            correlation_matrix=correlation_matrix,
            annual_performance=annual_performance,
            composite_score=composite_score_list,
            benchmark_returns=benchmark_returns_list,
            excess_returns=excess_returns_list,
            information_ratio=information_ratio,
            tracking_error=tracking_error,
            benchmark_code=benchmark_code_str,
        )

    def _generate_month_ends(self, start_date: str, end_date: str) -> list[date]:
        """生成月末日期序列（自然月最后一天）"""
        start = self._parse_date(start_date)
        end = self._parse_date(end_date)

        month_ends = []
        current = start.replace(day=1)

        while current <= end:
            # 找到当月最后一天
            if current.month == 12:
                last_day = current.replace(year=current.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                last_day = current.replace(month=current.month + 1, day=1) - timedelta(days=1)

            if start <= last_day <= end:
                month_ends.append(last_day)

            # 移到下个月
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        return month_ends

    def _get_universe_at_date(self, pool: str, ref_date: date) -> list[StockInfo]:
        """获取指定日期的选股池成分股（避免幸存者偏差）

        优先使用预取的成分股列表（避免重复 API 调用）。
        如果没有预取数据，回退到逐月查询。
        """
        if hasattr(self, '_prefetched_stocks') and self._prefetched_stocks:
            return self._prefetched_stocks

        stocks = self.universe_manager.get_universe_at_date(pool, ref_date)
        if not stocks:
            return []
        return list(stocks)

    def _fetch_data_for_date(self,
                             stocks: list[StockInfo],
                             ref_date: date) -> dict[str, dict[str, pd.DataFrame]]:
        """获取截至 ref_date 的历史数据

        如果有预取数据（self._prefetched_data），直接从内存切片，不调用 API。
        否则回退到逐只获取（兼容无预取的场景）。
        """
        end = ref_date.strftime("%Y%m%d")

        # 优先使用预取数据（内存切片，零 API 调用）
        if hasattr(self, '_prefetched_data') and self._prefetched_data:
            result: dict[str, dict[str, pd.DataFrame]] = {}
            for stock in stocks:
                if stock.code not in self._prefetched_data:
                    continue
                stock_data = self._prefetched_data[stock.code]
                filtered = {}
                for data_type, df in stock_data.items():
                    if df is None or df.empty:
                        continue
                    # 按日期切片：只保留 ref_date 之前的数据
                    if "trade_date" in df.columns:
                        mask = df["trade_date"].astype(str) <= end
                        sliced = df.loc[mask]
                        if not sliced.empty:
                            filtered[data_type] = sliced
                    else:
                        filtered[data_type] = df
                if filtered:
                    result[stock.code] = filtered
            return result

        # 回退：逐只获取（无预取时的兼容路径）
        result: dict[str, dict[str, pd.DataFrame]] = {}
        tasks = [
            (stock.code, data_type)
            for stock in stocks
            for data_type in FACTOR_DATA_TYPES
        ]

        fetcher = self.data_fetcher

        def fetch_one(code: str, data_type: str):
            try:
                df = fetcher._rate_limited_fetch(code, data_type, end_date=end)
                return code, data_type, df
            except Exception as e:
                logger.debug(f"获取 {code} {data_type} 失败: {e}")
                return code, data_type, None

        with ThreadPoolExecutor(max_workers=fetcher.max_workers) as executor:
            futures = {
                executor.submit(fetch_one, c, d): (c, d)
                for c, d in tasks
            }
            for future in as_completed(futures):
                code, data_type, df = future.result()
                if df is not None and not df.empty:
                    if code not in result:
                        result[code] = {}
                    result[code][data_type] = df

        return result

    def _compute_forward_returns(
        self,
        stocks: list[StockInfo],
        current_date: date,
        next_date: date,
    ) -> dict[str, float]:
        """计算从 current_date 到 next_date 的收益率。

        Returns:
            {stock_code: 收益率}，无数据的股票会被跳过
        """
        returns: dict[str, float] = {}
        if not hasattr(self, '_prefetched_data') or not self._prefetched_data:
            return returns

        current_str = current_date.strftime("%Y%m%d")
        next_str = next_date.strftime("%Y%m%d")

        for stock in stocks:
            stock_data = self._prefetched_data.get(stock.code)
            if not stock_data:
                continue
            daily = stock_data.get("daily")
            if daily is None or daily.empty or "close" not in daily.columns:
                continue

            try:
                if "trade_date" in daily.columns:
                    dates = daily["trade_date"].astype(str).str.replace("-", "").str[:8]
                    # current_date 当日或之前最近的价格
                    mask_cur = dates <= current_str
                    mask_next = dates <= next_str
                    if not mask_cur.any() or not mask_next.any():
                        continue
                    p_cur = float(daily.loc[mask_cur].iloc[0]["close"])
                    p_next = float(daily.loc[mask_next].iloc[0]["close"])
                else:
                    # 无日期列，取最新和次新
                    if len(daily) < 2:
                        continue
                    p_cur = float(daily.iloc[0]["close"])
                    p_next = float(daily.iloc[1]["close"])

                if p_cur > 0:
                    returns[stock.code] = (p_next - p_cur) / p_cur
            except (ValueError, TypeError, IndexError):
                continue

        return returns

    def _extract_prices(self,
                        stock_data: dict[str, dict[str, pd.DataFrame]]) -> dict[str, float]:
        """从 daily 数据中提取最新收盘价"""
        prices: dict[str, float] = {}
        for code, data in stock_data.items():
            daily = data.get("daily")
            if daily is not None and not daily.empty:
                try:
                    close_col = "close" if "close" in daily.columns else None
                    if close_col:
                        # Sort by date descending to ensure iloc[0] is the latest
                        date_col = "trade_date" if "trade_date" in daily.columns else None
                        if date_col:
                            daily_sorted = daily.sort_values(date_col, ascending=False)
                        else:
                            daily_sorted = daily.sort_index(ascending=False)
                        prices[code] = float(daily_sorted.iloc[0][close_col])
                except (ValueError, TypeError, IndexError):
                    pass
        return prices

    def _execute_trades(self,
                        trade_list,
                        holdings: dict[str, float],
                        cash: float,
                        prices: dict[str, float],
                        ref_date: date) -> float:
        """执行交易，更新持仓和现金

        Returns:
            更新后的现金余额
        """
        # 先卖出
        for signal in trade_list.sells:
            code = signal.stock_code
            if code in holdings:
                price = prices.get(code, 0)
                if price <= 0:
                    logger.warning(f"  跳过卖出 {code}: 价格为 {price}，无法确定合理卖出价")
                    continue
                shares = holdings.pop(code)
                proceeds = shares * price
                commission = proceeds * self.commission_rate
                cash += proceeds - commission
                logger.debug(f"  卖出 {code}: {shares}股 x {price} = {proceeds:.2f}, 佣金 {commission:.2f}")

        # 再买入
        buys = trade_list.buys
        if not buys:
            return cash

        # 可用资金（扣除现金储备后）
        available_cash = cash * (1 - self.signal_generator.cash_reserve)
        per_stock_budget = available_cash / len(buys) if buys else 0

        for signal in buys:
            code = signal.stock_code
            price = prices.get(code, 0)
            if price <= 0:
                continue

            shares = int(per_stock_budget / price / 100) * 100  # 整手（100股）
            if shares <= 0:
                continue

            cost = shares * price
            commission = cost * self.commission_rate
            total_cost = cost + commission

            if total_cost > cash:
                shares = int((cash * 0.99) / price / 100) * 100
                if shares <= 0:
                    continue
                cost = shares * price
                commission = cost * self.commission_rate
                total_cost = cost + commission

            holdings[code] = holdings.get(code, 0) + shares
            cash -= total_cost
            logger.debug(f"  买入 {code}: {shares}股 x {price} = {cost:.2f}, 佣金 {commission:.2f}")

        return cash

    def _calc_portfolio_value(self,
                              holdings: dict[str, float],
                              cash: float,
                              prices: dict[str, float],
                              ref_date: date) -> float:
        """计算组合总市值"""
        stock_value = sum(
            shares * prices.get(code, 0)
            for code, shares in holdings.items()
        )
        return cash + stock_value

    def _calc_weights(self,
                      holdings: dict[str, float],
                      cash: float,
                      prices: dict[str, float],
                      total_value: float) -> dict[str, float]:
        """计算持仓权重"""
        if total_value <= 0:
            return {}
        weights = {}
        for code, shares in holdings.items():
            price = prices.get(code, 0)
            w = (shares * price) / total_value
            if w > 0:
                weights[code] = round(w, 4)
        weights["_cash"] = round(cash / total_value, 4)
        return weights

    @staticmethod
    def _parse_date(date_str: str) -> date:
        """解析 YYYYMMDD 格式日期"""
        s = date_str.replace("-", "").strip()[:8]
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))

    def _compute_benchmark_monthly_returns(
        self,
        benchmark_code: str,
        start_date: str,
        end_date: str,
        month_ends: list[date],
    ) -> list[float]:
        """获取基准指数的月度收益率序列

        从 adapter 获取基准指数日线数据，提取月末收盘价，计算月度收益率。
        如果数据不可用，返回空列表（降级为无基准模式）。
        """
        try:
            df = self.data_fetcher.adapter.get_stock_data(
                benchmark_code, start_date, end_date, data_type="daily"
            )
            if df is None or df.empty or "close" not in df.columns:
                logger.warning(f"基准指数 {benchmark_code} 无可用数据")
                return []

            # 确保有 trade_date 列
            if "trade_date" not in df.columns:
                logger.warning(f"基准指数 {benchmark_code} 数据缺少 trade_date 列")
                return []

            df = df.copy()
            df["_date_str"] = df["trade_date"].astype(str).str.replace("-", "").str[:8]
            df = df.sort_values("_date_str", ascending=True).reset_index(drop=True)

            # 提取每月末的收盘价
            month_end_prices = []
            for me in month_ends:
                me_str = me.strftime("%Y%m%d")
                mask = df["_date_str"] <= me_str
                if mask.any():
                    month_end_prices.append(float(df.loc[mask].iloc[-1]["close"]))

            if len(month_end_prices) < 2:
                return []

            # 计算月度收益率
            monthly_returns = []
            for i in range(1, len(month_end_prices)):
                prev = month_end_prices[i - 1]
                if prev > 0:
                    monthly_returns.append(month_end_prices[i] / prev - 1)
                else:
                    monthly_returns.append(0.0)

            return monthly_returns

        except Exception as e:
            logger.warning(f"获取基准指数 {benchmark_code} 数据失败: {e}")
            return []
