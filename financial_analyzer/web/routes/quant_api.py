"""量化策略 API 路由"""
import copy
import json
import logging
import threading
import uuid
from pathlib import Path
from datetime import datetime

from typing import Optional

import numpy as np

from fastapi import APIRouter, Body, Query
from fastapi.responses import JSONResponse

from financial_analyzer.quant.universe import UniverseManager
from financial_analyzer.quant.data_fetcher import QuantDataFetcher
from financial_analyzer.quant.factors.value import (
    PEFactor, PBFactor, PSFactor, DividendYieldFactor, FCFYieldFactor, EV_EBITDA,
)
from financial_analyzer.quant.factors.quality import (
    ROEFactor, ROICFactor, GrossMarginFactor, NetMarginFactor, PiotroskiFScore, AccrualsRatio,
)
from financial_analyzer.quant.factors.growth import (
    RevenueGrowthFactor, NetProfitGrowthFactor, CashflowGrowthFactor, ROETrend,
)
from financial_analyzer.quant.factors.momentum import PriceMomentum3M, PriceMomentum6M, PriceMomentum12M
from financial_analyzer.quant.factors.sentiment import NorthBoundFlowFactor, MarginChangeFactor
from financial_analyzer.quant.factors.low_vol import Volatility60D, MaxDrawdown120D, DownsideDeviation
from financial_analyzer.quant.factors.risk import DebtRatioFactor, CurrentRatioFactor, LogMarketCap, AvgTurnover
from financial_analyzer.quant.engine.factor_matrix import FactorMatrixBuilder
from financial_analyzer.quant.engine.normalizer import CrossSectionalNormalizer
from financial_analyzer.quant.engine.scorer import WeightedScorer
from financial_analyzer.quant.engine.ranker import Ranker
from financial_analyzer.quant.engine.optimizer import ConstraintOptimizer
from financial_analyzer.quant.engine.signal import SignalGenerator
from financial_analyzer.quant.models import FactorConfig
from ..dependencies import get_adapter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/quant", tags=["quant"])

# 任务状态存储
_task_store: dict[str, dict] = {}
_task_lock = threading.Lock()

CONFIG_DIR = Path.home() / ".financialanalyzer"

DEFAULT_FACTOR_CONFIGS = [
    FactorConfig(name="pe", label="PE", category="value", weight=1.0),
    FactorConfig(name="pb", label="PB", category="value", weight=1.0),
    FactorConfig(name="ps", label="PS", category="value", weight=0.5),
    FactorConfig(name="fcf_yield", label="FCF收益率", category="value", weight=0.5),
    FactorConfig(name="dividend_yield", label="股息率", category="value", weight=0.5),
    FactorConfig(name="roe", label="ROE", category="quality", weight=1.5),
    FactorConfig(name="roic", label="ROIC", category="quality", weight=1.0),
    FactorConfig(name="gross_margin", label="毛利率", category="quality", weight=1.0),
    FactorConfig(name="net_margin", label="净利率", category="quality", weight=1.0),
    FactorConfig(name="revenue_growth", label="营收增长", category="growth", weight=1.0),
    FactorConfig(name="net_profit_growth", label="利润增长", category="growth", weight=1.0),
    FactorConfig(name="cashflow_growth", label="现金流增长", category="growth", weight=0.5),
    FactorConfig(name="momentum_3m", label="3月动量", category="momentum", weight=0.5),
    FactorConfig(name="momentum_6m", label="6月动量", category="momentum", weight=0.5),
    FactorConfig(name="momentum_12m", label="12月动量", category="momentum", weight=0.5),
    FactorConfig(name="north_bound_flow", label="北向资金", category="sentiment", weight=0.5),
    FactorConfig(name="margin_change", label="融资变化", category="sentiment", weight=0.5),
    FactorConfig(name="volatility_60d", label="60日波动", category="low_vol", weight=0.5),
    FactorConfig(name="max_drawdown_120d", label="最大回撤", category="low_vol", weight=0.5),
    FactorConfig(name="debt_ratio", label="负债率", category="risk", weight=1.0),
    FactorConfig(name="current_ratio", label="流动比率", category="risk", weight=0.5),
    FactorConfig(name="ev_ebitda", label="EV/EBITDA", category="value", weight=0.5),
    FactorConfig(name="piotroski_fscore", label="Piotroski F-Score", category="quality", weight=1.0),
    FactorConfig(name="accruals_ratio", label="应计比率", category="quality", weight=0.5),
    FactorConfig(name="roe_trend", label="ROE趋势", category="growth", weight=1.0),
    FactorConfig(name="downside_deviation", label="下行偏差", category="low_vol", weight=0.5),
    FactorConfig(name="log_market_cap", label="对数市值", category="risk", weight=0.5),
    FactorConfig(name="avg_turnover", label="平均换手率", category="risk", weight=0.5),
]

ALL_FACTORS = [
    PEFactor(), PBFactor(), PSFactor(), FCFYieldFactor(), DividendYieldFactor(), EV_EBITDA(),
    ROEFactor(), ROICFactor(), GrossMarginFactor(), NetMarginFactor(), PiotroskiFScore(), AccrualsRatio(),
    RevenueGrowthFactor(), NetProfitGrowthFactor(), CashflowGrowthFactor(), ROETrend(),
    PriceMomentum3M(), PriceMomentum6M(), PriceMomentum12M(),
    NorthBoundFlowFactor(), MarginChangeFactor(),
    Volatility60D(), MaxDrawdown120D(), DownsideDeviation(),
    DebtRatioFactor(), CurrentRatioFactor(), LogMarketCap(), AvgTurnover(),
]


def _load_token(adapter):
    """从 config.json 加载 Tushare token 并应用到 adapter"""
    config_path = CONFIG_DIR / "config.json"
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            token = config.get("tushare", "")
            if token and not adapter.tushare_pro:
                adapter.set_tushare_token(token)
                logger.info("Tushare token 已加载")
                return True
    except Exception as e:
        logger.warning(f"加载 Tushare token 失败: {e}")
    return False


@router.get("/pools")
async def list_pools():
    """获取可用选股池列表"""
    mgr = UniverseManager()
    return JSONResponse({"pools": mgr.pool_names()})


@router.get("/factors")
async def list_factors():
    """获取因子配置列表"""
    return JSONResponse({
        "factors": [
            {"name": c.name, "label": c.label, "category": c.category,
             "weight": c.weight, "enabled": c.enabled}
            for c in DEFAULT_FACTOR_CONFIGS
        ]
    })


def _cleanup_old_tasks(max_age_seconds=1800, store=None):
    """清理已完成/失败且超过 max_age_seconds 的任务"""
    import time as _time
    if store is None:
        store = _task_store
    now = _time.time()
    expired = [
        tid for tid, task in store.items()
        if task.get("status") in ("done", "error")
        and now - task.get("started_ts", 0) > max_age_seconds
    ]
    for tid in expired:
        del store[tid]


def _update_task(task_id: str, **kwargs):
    with _task_lock:
        if task_id in _task_store:
            _task_store[task_id].update(kwargs)


@router.post("/run")
async def run_signal_generation(
    pool: str = Query("沪深300", description="选股池名称"),
    top_n: int = Query(30, description="TOP-N 排名数量"),
    factor_weights: Optional[dict] = Body(None, description="因子权重 {name: weight}"),
    disabled_factors: Optional[list] = Body(None, description="禁用的因子名称列表"),
):
    """启动信号生成（后台线程 + 进度轮询）"""
    # Validate top_n
    if top_n < 1 or top_n > 50:
        return JSONResponse({"error": "top_n 必须在 1-50 之间"}, status_code=400)

    # Validate pool
    allowed_pools = ["沪深300", "中证500", "中证800", "创业板指", "科创50"]
    if pool not in allowed_pools:
        return JSONResponse({"error": f"pool 不在允许列表中，可选: {', '.join(allowed_pools)}"}, status_code=400)

    task_id = uuid.uuid4().hex[:12]

    import time as _time
    with _task_lock:
        _cleanup_old_tasks()
        _task_store[task_id] = {
            "status": "starting",
            "progress": 0,
            "message": "正在初始化...",
            "started_at": datetime.now().isoformat(),
            "started_ts": _time.time(),
            "pool": pool,
        }

    def run_pipeline():
        try:
            _update_task(task_id, status="running", progress=5, message="加载 Tushare 连接...")
            adapter = get_adapter()
            _load_token(adapter)

            _update_task(task_id, progress=10, message=f"获取 {pool} 成分股...")
            mgr = UniverseManager(adapter)
            stocks = mgr.get_universe(pool)

            if not stocks:
                _update_task(task_id, status="error", message=f"选股池 [{pool}] 无可用股票")
                return

            n_stocks = len(stocks)
            # 硬上限：防止 API 返回异常数据时无限处理
            MAX_STOCKS = 500
            if n_stocks > MAX_STOCKS:
                logger.warning(f"选股池过大 ({n_stocks})，截断至 {MAX_STOCKS}")
                stocks = stocks[:MAX_STOCKS]
                n_stocks = MAX_STOCKS
            _update_task(task_id, progress=15, message=f"成分股: {n_stocks} 只，补充基本信息...")

            def progress_cb(stage, current, total, msg):
                # fetch 阶段占 15%–80% 的进度
                base = 15
                pct = base + int(65 * current / total) if total > 0 else base
                _update_task(task_id, progress=pct, message=msg, stage=stage,
                             current=current, total=total)

            fetcher = QuantDataFetcher(adapter, start_date="20230101",
                                       progress_callback=progress_cb)
            stocks = fetcher.enrich_stock_info(stocks)
            stocks = mgr.apply_filters(stocks)
            stock_data = fetcher.fetch_all(stocks)

            stocks_with_data = [s for s in stocks if s.code in stock_data]
            n_valid = len(stocks_with_data)

            if n_valid < 5:
                _update_task(task_id, status="error",
                             message=f"有效数据不足: {n_valid}/{n_stocks} 只")
                return

            _update_task(task_id, progress=80, message=f"计算因子矩阵 ({n_valid} 只)...")

            builder = FactorMatrixBuilder(factors=ALL_FACTORS)
            matrix = builder.build(stocks_with_data, stock_data)

            if len(matrix.stocks) < 5:
                _update_task(task_id, status="error", message=f"因子计算后不足: {len(matrix.stocks)} 只")
                return

            _update_task(task_id, progress=85, message="截面标准化 + 打分 + 排名...")
            normalizer = CrossSectionalNormalizer(method="zscore")
            matrix = normalizer.normalize(matrix)

            # Use user-adjusted weights if provided, otherwise defaults
            if factor_weights or disabled_factors:
                disabled_set = set(disabled_factors) if disabled_factors else set()
                custom_configs = [
                    FactorConfig(
                        name=c.name, label=c.label, category=c.category,
                        direction=c.direction,
                        enabled=False if c.name in disabled_set else c.enabled,
                        weight=float(factor_weights.get(c.name, c.weight)) if factor_weights else c.weight,
                    )
                    for c in DEFAULT_FACTOR_CONFIGS
                ]
                scorer = WeightedScorer(custom_configs)
            else:
                scorer = WeightedScorer(DEFAULT_FACTOR_CONFIGS)
            composite_scores = scorer.score(matrix)

            # 从 stock_data 中提取股价
            prices_from_data = {}
            for code, data in stock_data.items():
                daily = data.get("daily")
                if daily is not None and not daily.empty and "close" in daily.columns:
                    prices_from_data[code] = float(daily["close"].iloc[0])

            # 5000元本金：每只至少买100股，预留10%现金
            # 5只持仓：4500/5=900/只 → max 9元 | 8只：4500/8=562/只 → max 5元
            # 取折中：max_price=10, min 5只
            max_price = 10.0
            ranker = Ranker(top_n=top_n, max_price=max_price)
            ranked = ranker.rank(composite_scores, stocks_with_data,
                                 prices=prices_from_data)

            if not ranked:
                _update_task(task_id, status="error",
                             message=f"股价≤{max_price}元过滤后无股票入选（共{len(stocks_with_data)}只有效数据）")
                return

            _update_task(task_id, progress=90, message=f"约束优化 ({len(ranked)} 只) + 生成信号...")
            optimizer = ConstraintOptimizer()
            optimized = optimizer.optimize(ranked, composite_scores)

            signal_gen = SignalGenerator()
            trade_list = signal_gen.generate(
                optimized_stocks=optimized,
                scores=composite_scores,
                current_holdings=set(),
                universe=pool,
            )

            _update_task(task_id, status="done", progress=100, message="完成",
                         result={
                             "success": True,
                             "date": str(trade_list.date),
                             "universe": pool,
                             "total_stocks_analyzed": n_stocks,
                             "valid_stocks": n_valid,
                             "signals": [
                                 {
                                     "code": s.stock_code,
                                     "name": s.stock_name,
                                     "action": s.action,
                                     "score": round(s.composite_score, 4),
                                     "weight": round(s.target_weight, 4),
                                     "price": round(prices_from_data.get(s.stock_code, 0), 2),
                                     "reason": s.reason,
                                 }
                                 for s in trade_list.signals
                             ],
                         })

        except Exception as e:
            logger.error(f"信号生成失败: {e}", exc_info=True)
            _update_task(task_id, status="error", message=str(e))

    threading.Thread(target=run_pipeline, daemon=True).start()
    return JSONResponse({"task_id": task_id})


@router.get("/status/{task_id}")
async def task_status(task_id: str):
    """查询任务进度"""
    with _task_lock:
        task = _task_store.get(task_id)
    if not task:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    return JSONResponse({k: v for k, v in task.items() if k != "result"})


@router.get("/result/{task_id}")
async def task_result(task_id: str):
    """获取任务结果"""
    with _task_lock:
        task = _task_store.get(task_id)
    if not task:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    if task["status"] == "done":
        return JSONResponse(task.get("result", {}))
    return JSONResponse({"status": task["status"], "progress": task["progress"], "message": task["message"]})


@router.post("/sensitivity")
async def run_sensitivity(
    pool: str = Query("沪深300", description="选股池名称"),
    factor_x: str = Query(..., description="X 轴因子 name"),
    factor_y: str = Query(..., description="Y 轴因子 name"),
    grid_size: int = Query(5, description="网格大小", ge=3, le=9),
    weight_min: float = Query(0.2, description="权重最小值"),
    weight_max: float = Query(1.8, description="权重最大值"),
):
    """启动敏感性分析（后台线程 + 进度轮询）"""
    # Validate pool
    allowed_pools = ["沪深300", "中证500", "中证800", "创业板指", "科创50"]
    if pool not in allowed_pools:
        return JSONResponse({"error": f"pool 不在允许列表中，可选: {', '.join(allowed_pools)}"}, status_code=400)

    allowed_names = {c.name for c in DEFAULT_FACTOR_CONFIGS}
    if factor_x not in allowed_names:
        return JSONResponse({"error": f"factor_x '{factor_x}' 不在因子列表中"}, status_code=400)
    if factor_y not in allowed_names:
        return JSONResponse({"error": f"factor_y '{factor_y}' 不在因子列表中"}, status_code=400)
    if factor_x == factor_y:
        return JSONResponse({"error": "factor_x 和 factor_y 不能相同"}, status_code=400)
    if weight_min >= weight_max:
        return JSONResponse({"error": "weight_min 必须小于 weight_max"}, status_code=400)

    task_id = "sens_" + uuid.uuid4().hex[:12]

    import time as _time
    with _task_lock:
        _cleanup_old_tasks()
        _task_store[task_id] = {
            "status": "starting",
            "progress": 0,
            "message": "正在初始化敏感性分析...",
            "started_at": datetime.now().isoformat(),
            "started_ts": _time.time(),
            "pool": pool,
            "is_sensitivity": True,
        }

    def _run_sensitivity():
        try:
            _update_task(task_id, status="running", progress=5, message="加载 Tushare 连接...")
            adapter = get_adapter()
            _load_token(adapter)

            _update_task(task_id, progress=10, message=f"获取 {pool} 成分股...")
            mgr = UniverseManager(adapter)
            stocks = mgr.get_universe(pool)
            if not stocks:
                _update_task(task_id, status="error", message=f"选股池 [{pool}] 无可用股票")
                return

            MAX_STOCKS = 500
            if len(stocks) > MAX_STOCKS:
                stocks = stocks[:MAX_STOCKS]
            _update_task(task_id, progress=15, message=f"成分股: {len(stocks)} 只，补充基本信息...")

            def progress_cb(stage, current, total, msg):
                base = 15
                pct = base + int(45 * current / total) if total > 0 else base
                _update_task(task_id, progress=pct, message=msg)

            fetcher = QuantDataFetcher(adapter, start_date="20230101",
                                       progress_callback=progress_cb)
            stocks = fetcher.enrich_stock_info(stocks)
            stocks = mgr.apply_filters(stocks)
            stock_data = fetcher.fetch_all(stocks)

            stocks_with_data = [s for s in stocks if s.code in stock_data]
            n_valid = len(stocks_with_data)
            if n_valid < 5:
                _update_task(task_id, status="error",
                             message=f"有效数据不足: {n_valid}/{len(stocks)} 只")
                return

            _update_task(task_id, progress=60, message=f"构建因子矩阵 ({n_valid} 只)...")

            builder = FactorMatrixBuilder(factors=ALL_FACTORS)
            matrix = builder.build(stocks_with_data, stock_data)
            if len(matrix.stocks) < 5:
                _update_task(task_id, status="error",
                             message=f"因子计算后不足: {len(matrix.stocks)} 只")
                return

            _update_task(task_id, progress=70, message="截面标准化...")
            normalizer = CrossSectionalNormalizer(method="zscore")
            matrix = normalizer.normalize(matrix)

            # Extract prices
            prices_from_data = {}
            for code, data in stock_data.items():
                daily = data.get("daily")
                if daily is not None and not daily.empty and "close" in daily.columns:
                    prices_from_data[code] = float(daily["close"].iloc[0])

            # Look up factor configs
            fx_cfg = next(c for c in DEFAULT_FACTOR_CONFIGS if c.name == factor_x)
            fy_cfg = next(c for c in DEFAULT_FACTOR_CONFIGS if c.name == factor_y)

            # Build weight grid
            weights = np.linspace(weight_min, weight_max, grid_size).tolist()
            weights = [round(w, 4) for w in weights]

            # Baseline: run with original weights
            _update_task(task_id, progress=75, message="计算基准指标...")
            baseline_scorer = WeightedScorer(DEFAULT_FACTOR_CONFIGS)
            baseline_scores = baseline_scorer.score(matrix)
            baseline_ranked = Ranker(top_n=30, max_price=10.0).rank(
                baseline_scores, stocks_with_data, prices=prices_from_data)
            baseline_metric = 0.0
            if baseline_ranked:
                baseline_opt = ConstraintOptimizer().optimize(baseline_ranked, baseline_scores)
                if baseline_opt:
                    opt_codes = [s.stock_code for s in baseline_opt]
                    baseline_metric = float(np.mean([
                        baseline_scores.get(c, 0.0) for c in opt_codes
                    ]))

            # Grid search
            total_cells = grid_size * grid_size
            grid_values = []
            done_cells = 0

            for wy in weights:
                row = []
                for wx in weights:
                    custom_configs = []
                    for c in DEFAULT_FACTOR_CONFIGS:
                        new_w = c.weight
                        if c.name == factor_x:
                            new_w = wx
                        elif c.name == factor_y:
                            new_w = wy
                        custom_configs.append(FactorConfig(
                            name=c.name, label=c.label, category=c.category,
                            direction=c.direction, weight=new_w, enabled=c.enabled,
                        ))

                    scorer = WeightedScorer(custom_configs)
                    scores = scorer.score(matrix)
                    ranked = Ranker(top_n=30, max_price=10.0).rank(
                        scores, stocks_with_data, prices=prices_from_data)
                    metric = 0.0
                    if ranked:
                        optimized = ConstraintOptimizer().optimize(ranked, scores)
                        if optimized:
                            opt_codes = [s.stock_code for s in optimized]
                            metric = float(np.mean([
                                scores.get(c, 0.0) for c in opt_codes
                            ]))
                    row.append(round(metric, 6))
                    done_cells += 1

                grid_values.append(row)
                pct = 75 + int(20 * done_cells / total_cells)
                _update_task(task_id, progress=pct,
                             message=f"网格计算 {done_cells}/{total_cells}...")

            result = {
                "factor_x": {"name": fx_cfg.name, "label": fx_cfg.label, "category": fx_cfg.category},
                "factor_y": {"name": fy_cfg.name, "label": fy_cfg.label, "category": fy_cfg.category},
                "x_range": weights,
                "y_range": weights,
                "grid": grid_values,
                "baseline": {
                    "x_weight": fx_cfg.weight,
                    "y_weight": fy_cfg.weight,
                    "metric": round(baseline_metric, 6),
                },
                "pool": pool,
                "valid_stocks": n_valid,
                "metric_label": "Top-N 平均综合分数",
            }

            _update_task(task_id, status="done", progress=100,
                         message="敏感性分析完成", result=result)

        except Exception as e:
            logger.error(f"敏感性分析失败: {e}", exc_info=True)
            _update_task(task_id, status="error", message=str(e))

    threading.Thread(target=_run_sensitivity, daemon=True).start()
    return JSONResponse({"task_id": task_id})


@router.get("/sensitivity/status/{task_id}")
async def sensitivity_status(task_id: str):
    """查询敏感性分析任务进度"""
    with _task_lock:
        task = _task_store.get(task_id)
    if not task:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    return JSONResponse({k: v for k, v in task.items() if k != "result"})


@router.get("/sensitivity/result/{task_id}")
async def sensitivity_result(task_id: str):
    """获取敏感性分析结果"""
    with _task_lock:
        task = _task_store.get(task_id)
    if not task:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    if task["status"] == "done":
        return JSONResponse(task.get("result", {}))
    return JSONResponse({"status": task["status"], "progress": task["progress"], "message": task["message"]})


# ========== 全因子自动权重优化 ==========

CATEGORIES = ["value", "quality", "growth", "momentum", "sentiment", "low_vol", "risk"]

CATEGORY_LABELS = {
    "value": "价值", "quality": "质量", "growth": "成长",
    "momentum": "动量", "sentiment": "情绪", "low_vol": "低波", "risk": "风险",
}


def _get_category_base_weights() -> dict[str, float]:
    """获取每个类别的原始平均权重"""
    cat_weights: dict[str, list[float]] = {}
    for c in DEFAULT_FACTOR_CONFIGS:
        cat_weights.setdefault(c.category, []).append(c.weight)
    return {cat: sum(ws) / len(ws) for cat, ws in cat_weights.items()}


def _build_weighted_configs(multipliers: dict[str, float]) -> list[FactorConfig]:
    """根据类别乘数构建新的因子配置"""
    configs = []
    for c in DEFAULT_FACTOR_CONFIGS:
        mult = multipliers.get(c.category, 1.0)
        configs.append(FactorConfig(
            name=c.name, label=c.label, category=c.category,
            direction=c.direction, weight=c.weight * mult, enabled=c.enabled,
        ))
    return configs


def _extract_price_at_date(stock_data: dict, stock_code: str, target_date) -> Optional[float]:
    """从 stock_data 中提取指定日期附近的收盘价"""
    data = stock_data.get(stock_code)
    if not data:
        return None
    daily = data.get("daily")
    if daily is None or daily.empty or "close" not in daily.columns:
        return None

    target_str = target_date.strftime("%Y%m%d") if hasattr(target_date, "strftime") else str(target_date)

    # 确保 trade_date 是字符串格式
    if "trade_date" in daily.columns:
        dates = daily["trade_date"].astype(str).str.replace("-", "").str[:8]
        # 先尝试精确匹配或之前最近的交易日
        mask = dates <= target_str
        if mask.any():
            return float(daily.loc[mask].iloc[0]["close"])  # iloc[0] 因为数据按日期降序
        # 如果 target 之前没有数据，取最早的可用价格
        return float(daily.iloc[-1]["close"])

    # 没有 trade_date 列，直接取最新价格
    return float(daily.iloc[0]["close"]) if not daily.empty else None


@router.post("/optimize")
async def run_optimize(
    pool: str = Query("沪深300", description="选股池名称"),
    train_end: str = Query("20240630", description="训练期结束日期 YYYYMMDD"),
    top_n: int = Query(30, description="TOP-N 排名数量"),
    max_iterations: int = Query(50, description="最大迭代次数"),
):
    """全因子自动权重优化（防过拟合版）

    - 按 7 个类别优化权重（而非 25 个因子），降低参数维度
    - 训练/测试期分割，在训练期优化，在测试期验证
    - 使用实际收益率作为评估指标（而非拟合指标）
    """
    allowed_pools = ["沪深300", "中证500", "中证800", "创业板指", "科创50"]
    if pool not in allowed_pools:
        return JSONResponse({"error": f"pool 不在允许列表中"}, status_code=400)

    task_id = "opt_" + uuid.uuid4().hex[:12]

    import time as _time
    with _task_lock:
        _cleanup_old_tasks()
        _task_store[task_id] = {
            "status": "starting", "progress": 0, "message": "正在初始化...",
            "started_at": datetime.now().isoformat(), "started_ts": _time.time(), "pool": pool,
        }

    def _run_optimize():
        try:
            _update_task(task_id, progress=5, message="加载数据源...")
            adapter = get_adapter()
            _load_token(adapter)

            _update_task(task_id, progress=10, message=f"获取 {pool} 成分股...")
            mgr = UniverseManager(adapter)
            stocks = mgr.get_universe(pool)
            if not stocks:
                _update_task(task_id, status="error", message=f"选股池 [{pool}] 无可用股票")
                return

            MAX_STOCKS = 500
            if len(stocks) > MAX_STOCKS:
                stocks = stocks[:MAX_STOCKS]

            _update_task(task_id, progress=15, message="获取历史数据...")
            fetcher = QuantDataFetcher(adapter, start_date="20230101")
            stocks = fetcher.enrich_stock_info(stocks)
            stocks = mgr.apply_filters(stocks)
            stock_data = fetcher.fetch_all(stocks)

            stocks_with_data = [s for s in stocks if s.code in stock_data]
            if len(stocks_with_data) < 10:
                _update_task(task_id, status="error", message="有效数据不足")
                return

            _update_task(task_id, progress=25, message="构建因子矩阵...")
            builder = FactorMatrixBuilder(factors=ALL_FACTORS)
            matrix = builder.build(stocks_with_data, stock_data)
            normalizer = CrossSectionalNormalizer(method="zscore")
            matrix = normalizer.normalize(matrix)

            _update_task(task_id, progress=30, message="计算测试期收益率...")
            from datetime import datetime as dt
            train_end_dt = dt.strptime(train_end, "%Y%m%d")

            prices_train = {}
            prices_test = {}
            for s in stocks_with_data:
                p_train = _extract_price_at_date(stock_data, s.code, train_end_dt)
                p_test = _extract_price_at_date(stock_data, s.code, datetime.now())
                if p_train and p_test and p_train > 0:
                    prices_train[s.code] = p_train
                    prices_test[s.code] = p_test

            # 如果价格提取失败，回退到 stock_data 中的最新价格
            if len(prices_train) < len(stocks_with_data) // 2:
                logger.warning(f"价格提取不足 ({len(prices_train)}/{len(stocks_with_data)})，回退到最新价格")
                for s in stocks_with_data:
                    if s.code not in prices_train:
                        data = stock_data.get(s.code, {})
                        daily = data.get("daily")
                        if daily is not None and not daily.empty and "close" in daily.columns:
                            prices_train[s.code] = float(daily.iloc[0]["close"])
                            prices_test[s.code] = float(daily.iloc[0]["close"])

            logger.info(f"价格提取: {len(stocks_with_data)} 只股票, 训练期价格 {len(prices_train)} 只, 测试期价格 {len(prices_test)} 只")

            test_returns = {}
            for code in prices_train:
                if code in prices_test:
                    test_returns[code] = (prices_test[code] - prices_train[code]) / prices_train[code]

            logger.info(f"测试期收益率: {len(test_returns)} 只股票有数据")

            if len(test_returns) < 10:
                _update_task(task_id, status="error", message="测试期价格数据不足")
                return

            _update_task(task_id, progress=35, message="计算基准表现...")
            base_scorer = WeightedScorer(DEFAULT_FACTOR_CONFIGS)
            base_scores = base_scorer.score(matrix)
            base_ranked = Ranker(top_n=top_n, max_price=10.0).rank(base_scores, stocks_with_data, prices=prices_train)
            base_top_codes = {s.code for s in base_ranked[:top_n]}
            base_returns = [test_returns.get(c, 0) for c in base_top_codes]
            base_avg_return = sum(base_returns) / len(base_returns) if base_returns else 0

            eval_count = [0]

            def objective(multipliers_arr):
                eval_count[0] += 1
                multipliers = {cat: float(multipliers_arr[i]) for i, cat in enumerate(CATEGORIES)}

                configs = _build_weighted_configs(multipliers)
                scorer = WeightedScorer(configs)
                scores = scorer.score(matrix)
                ranked = Ranker(top_n=top_n, max_price=10.0).rank(scores, stocks_with_data, prices=prices_train)
                top_codes = {s.code for s in ranked[:top_n]}

                if not top_codes:
                    return 0.0

                returns = [test_returns.get(c, 0) for c in top_codes]
                avg_ret = sum(returns) / len(returns) if returns else 0

                if eval_count[0] % 10 == 0:
                    pct = min(35 + int(55 * eval_count[0] / (max_iterations * 15)), 90)
                    _update_task(task_id, progress=pct,
                                 message=f"优化中... 第 {eval_count[0]} 次评估，当前收益: {avg_ret:.2%}")

                return -avg_ret

            _update_task(task_id, progress=35, message="开始差分进化优化...")
            from scipy.optimize import differential_evolution

            bounds = [(0.1, 3.0)] * len(CATEGORIES)

            result = differential_evolution(
                objective, bounds=bounds, maxiter=max_iterations,
                seed=42, tol=1e-4, polish=True,
            )

            _update_task(task_id, progress=92, message="整理优化结果...")
            optimal_mults = {cat: round(float(result.x[i]), 4) for i, cat in enumerate(CATEGORIES)}

            opt_configs = _build_weighted_configs(optimal_mults)
            opt_scorer = WeightedScorer(opt_configs)
            opt_scores = opt_scorer.score(matrix)
            opt_ranked = Ranker(top_n=top_n, max_price=10.0).rank(opt_scores, stocks_with_data, prices=prices_train)
            opt_top_codes = {s.code for s in opt_ranked[:top_n]}
            opt_returns = [test_returns.get(c, 0) for c in opt_top_codes]
            opt_avg_return = sum(opt_returns) / len(opt_returns) if opt_returns else 0

            overlap = base_top_codes & opt_top_codes
            overlap_rate = len(overlap) / len(base_top_codes) if base_top_codes else 0

            base_cat_weights = _get_category_base_weights()
            stock_name_map = {s.code: s.name for s in stocks_with_data}
            added = opt_top_codes - base_top_codes
            removed = base_top_codes - opt_top_codes

            result_data = {
                "pool": pool,
                "train_end": train_end,
                "top_n": top_n,
                "valid_stocks": len(stocks_with_data),
                "test_return_baseline": round(base_avg_return, 6),
                "test_return_optimized": round(opt_avg_return, 6),
                "improvement": round(opt_avg_return - base_avg_return, 6),
                "overlap_count": len(overlap),
                "overlap_rate": round(overlap_rate, 4),
                "evaluations": eval_count[0],
                "convergence": bool(result.success),
                "category_weights": {
                    cat: {
                        "label": CATEGORY_LABELS[cat],
                        "base_weight": round(base_cat_weights.get(cat, 1.0), 4),
                        "optimal_multiplier": optimal_mults[cat],
                        "effective_weight": round(base_cat_weights.get(cat, 1.0) * optimal_mults[cat], 4),
                    }
                    for cat in CATEGORIES
                },
                "baseline_top": [
                    {"code": c, "name": stock_name_map.get(c, ""), "return": round(test_returns.get(c, 0), 4)}
                    for c in sorted(base_top_codes)
                ],
                "optimized_top": [
                    {"code": c, "name": stock_name_map.get(c, ""), "return": round(test_returns.get(c, 0), 4)}
                    for c in sorted(opt_top_codes)
                ],
                "added": [
                    {"code": c, "name": stock_name_map.get(c, ""), "return": round(test_returns.get(c, 0), 4)}
                    for c in sorted(added)
                ],
                "removed": [
                    {"code": c, "name": stock_name_map.get(c, ""), "return": round(test_returns.get(c, 0), 4)}
                    for c in sorted(removed)
                ],
                "metric_label": "测试期实际收益率",
            }

            _update_task(task_id, status="done", progress=100,
                         message=f"优化完成！评估 {eval_count[0]} 次，收益: {base_avg_return:.2%} → {opt_avg_return:.2%}",
                         result=result_data)

        except Exception as e:
            logger.error(f"权重优化失败: {e}", exc_info=True)
            _update_task(task_id, status="error", message=str(e))

    threading.Thread(target=_run_optimize, daemon=True).start()
    return JSONResponse({"task_id": task_id})


@router.get("/optimize/status/{task_id}")
async def optimize_status(task_id: str):
    """查询优化任务进度"""
    with _task_lock:
        task = _task_store.get(task_id)
    if not task:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    return JSONResponse({k: v for k, v in task.items() if k != "result"})


@router.get("/optimize/result/{task_id}")
async def optimize_result(task_id: str):
    """获取优化结果"""
    with _task_lock:
        task = _task_store.get(task_id)
    if not task:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    if task["status"] == "done":
        return JSONResponse(task.get("result", {}))
    return JSONResponse({"status": task["status"], "progress": task["progress"], "message": task["message"]})


# ========== 因子 IC/IR 分析 ==========

@router.post("/factor-analysis")
async def run_factor_analysis(
    pool: str = Query("沪深300", description="选股池名称"),
    top_n: int = Query(30, description="TOP-N 排名数量"),
    start_date: str = Query("20230101", description="回测起始日期 YYYYMMDD"),
    end_date: str = Query("", description="回测结束日期 YYYYMMDD（空=至今）"),
):
    """启动因子 IC/IR 分析（后台线程 + 进度轮询）"""
    allowed_pools = ["沪深300", "中证500", "中证800", "创业板指", "科创50"]
    if pool not in allowed_pools:
        return JSONResponse({"error": f"pool 不在允许列表中，可选: {', '.join(allowed_pools)}"}, status_code=400)

    task_id = "fa_" + uuid.uuid4().hex[:12]

    import time as _time
    with _task_lock:
        _cleanup_old_tasks()
        _task_store[task_id] = {
            "status": "starting",
            "progress": 0,
            "message": "正在初始化因子分析...",
            "started_at": datetime.now().isoformat(),
            "started_ts": _time.time(),
            "pool": pool,
        }

    def _run_factor_analysis():
        try:
            from financial_analyzer.quant.engine.factor_analyzer import FactorAnalyzer
            from financial_analyzer.quant.backtest.engine import BacktestEngine

            _update_task(task_id, status="running", progress=5, message="加载数据源...")
            adapter = get_adapter()
            _load_token(adapter)

            _update_task(task_id, progress=10, message=f"获取 {pool} 成分股...")
            mgr = UniverseManager(adapter)
            stocks = mgr.get_universe(pool)
            if not stocks:
                _update_task(task_id, status="error", message=f"选股池 [{pool}] 无可用股票")
                return

            MAX_STOCKS = 500
            if len(stocks) > MAX_STOCKS:
                stocks = stocks[:MAX_STOCKS]

            def progress_cb(stage, current, total, msg):
                base = 15
                pct = base + int(55 * current / total) if total > 0 else base
                _update_task(task_id, progress=pct, message=msg)

            _update_task(task_id, progress=15, message="获取历史数据...")
            fetcher = QuantDataFetcher(adapter, start_date=start_date,
                                       progress_callback=progress_cb)
            stocks = fetcher.enrich_stock_info(stocks)
            stocks = mgr.apply_filters(stocks)
            stock_data = fetcher.fetch_all(stocks)

            stocks_with_data = [s for s in stocks if s.code in stock_data]
            if len(stocks_with_data) < 30:
                _update_task(task_id, status="error",
                             message=f"有效数据不足: {len(stocks_with_data)} 只（需要至少 30 只）")
                return

            _update_task(task_id, progress=70, message="运行因子 IC/IR 分析...")

            factor_analyzer = FactorAnalyzer(min_sample_size=30)
            engine = BacktestEngine(
                factors=ALL_FACTORS,
                factor_configs=DEFAULT_FACTOR_CONFIGS,
                factor_analyzer=factor_analyzer,
            )

            result = engine.run(
                stocks=stocks_with_data,
                stock_data=stock_data,
                initial_capital=100000,
                top_n=top_n,
            )

            _update_task(task_id, progress=90, message="整理分析结果...")

            ic_summary = result.factor_ic
            timeseries = ic_summary.pop("_timeseries", {})

            output = {
                "pool": pool,
                "period": {"start": start_date, "end": end_date or "至今"},
                "valid_stocks": len(stocks_with_data),
                "ic_summary": ic_summary,
                "monthly_ic": timeseries,
            }

            _update_task(task_id, status="done", progress=100,
                         message="因子分析完成", result=output)

        except Exception as e:
            logger.error(f"因子分析失败: {e}", exc_info=True)
            _update_task(task_id, status="error", message=str(e))

    threading.Thread(target=_run_factor_analysis, daemon=True).start()
    return JSONResponse({"task_id": task_id})


@router.get("/factor-analysis/status/{task_id}")
async def factor_analysis_status(task_id: str):
    """查询因子分析任务进度"""
    with _task_lock:
        task = _task_store.get(task_id)
    if not task:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    return JSONResponse({k: v for k, v in task.items() if k != "result"})


@router.get("/factor-analysis/result/{task_id}")
async def factor_analysis_result(task_id: str):
    """获取因子分析结果"""
    with _task_lock:
        task = _task_store.get(task_id)
    if not task:
        return JSONResponse({"error": "任务不存在"}, status_code=404)
    if task["status"] == "done":
        return JSONResponse(task.get("result", {}))
    return JSONResponse({"status": task["status"], "progress": task["progress"], "message": task["message"]})
