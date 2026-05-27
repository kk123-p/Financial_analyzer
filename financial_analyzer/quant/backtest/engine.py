"""月频调仓回测引擎"""
import logging
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
from .metrics import MetricsCalculator, PerformanceMetrics
from .attribution import FactorAttribution
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
                 commission_rate: float = DEFAULT_COMMISSION_RATE):
        self.universe_manager = universe_manager
        self.data_fetcher = data_fetcher
        self.factor_matrix_builder = factor_matrix_builder
        self.normalizer = normalizer
        self.scorer = scorer
        self.ranker = ranker
        self.optimizer = optimizer
        self.signal_generator = signal_generator
        self.commission_rate = commission_rate

    def run(self,
            start_date: str,
            end_date: str,
            pool: str = "沪深300",
            initial_capital: float = 5000.0) -> BacktestResult:
        """运行回测

        Args:
            start_date: 回测起始日期 YYYYMMDD
            end_date: 回测结束日期 YYYYMMDD
            pool: 选股池名称
            initial_capital: 初始资金
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

        # 3. 逐月回测
        for i, rebal_date in enumerate(month_ends):
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
            from datetime import date as date_type
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

            # 3d. 标准化 → 打分 → 排名 → 优化
            matrix = self.normalizer.normalize(matrix)
            scores = self.scorer.score(matrix)
            ranked = self.ranker.rank(matrix, scores, stocks, prices=prices)
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

        final_value = portfolio_values[-1] if portfolio_values else initial_capital

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
        """获取指定日期的选股池成分股

        注意: 当前实现使用 Tushare index_weight 获取最新成分股。
        严格的历史成分股需要按 trade_date 查询，这里做简化处理。
        """
        stocks = self.universe_manager.get_universe(pool)
        if not stocks:
            return []
        return list(stocks)

    def _fetch_data_for_date(self,
                             stocks: list[StockInfo],
                             ref_date: date) -> dict[str, dict[str, pd.DataFrame]]:
        """获取截至 ref_date 的历史数据

        使用 data_fetcher 的 adapter 直接获取，end_date 设为回测日期。
        """
        start = self.data_fetcher.start_date
        end = ref_date.strftime("%Y%m%d")
        result: dict[str, dict[str, pd.DataFrame]] = {}

        for stock in stocks:
            stock_data: dict[str, pd.DataFrame] = {}
            for data_type in FACTOR_DATA_TYPES:
                try:
                    df = self.data_fetcher.adapter.get_stock_data(
                        stock.code, start, end, data_type
                    )
                    if df is not None and not df.empty:
                        stock_data[data_type] = df
                except Exception as e:
                    logger.debug(f"获取 {stock.code} {data_type} 失败: {e}")

            if stock_data:
                result[stock.code] = stock_data

        return result

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
                        prices[code] = float(daily.iloc[0][close_col])
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
                shares = holdings.pop(code)
                price = prices.get(code, 0)
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
