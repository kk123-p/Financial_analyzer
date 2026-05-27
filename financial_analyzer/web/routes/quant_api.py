"""量化策略 API 路由"""
import json
import logging
import threading
import uuid
from pathlib import Path
from datetime import datetime

from typing import Optional

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
    return JSONResponse(task)


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
