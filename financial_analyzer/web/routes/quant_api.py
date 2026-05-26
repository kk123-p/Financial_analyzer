"""量化策略 API 路由"""
import logging
from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from financial_analyzer.quant.universe import UniverseManager
from financial_analyzer.quant.factors.value import PEFactor, PBFactor, PSFactor, FCFYieldFactor
from financial_analyzer.quant.factors.quality import ROEFactor, ROICFactor, GrossMarginFactor, NetMarginFactor
from financial_analyzer.quant.factors.growth import RevenueGrowthFactor, NetProfitGrowthFactor, CashflowGrowthFactor
from financial_analyzer.quant.factors.momentum import PriceMomentum3M, PriceMomentum6M, PriceMomentum12M
from financial_analyzer.quant.factors.sentiment import NorthBoundFlowFactor, MarginChangeFactor
from financial_analyzer.quant.factors.low_vol import Volatility60D, MaxDrawdown120D
from financial_analyzer.quant.factors.risk import DebtRatioFactor, CurrentRatioFactor
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

DEFAULT_FACTOR_CONFIGS = [
    FactorConfig(name="pe", label="PE", category="value", weight=1.0),
    FactorConfig(name="pb", label="PB", category="value", weight=1.0),
    FactorConfig(name="ps", label="PS", category="value", weight=0.5),
    FactorConfig(name="fcf_yield", label="FCF收益率", category="value", weight=0.5),
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
]

ALL_FACTORS = [
    PEFactor(), PBFactor(), PSFactor(), FCFYieldFactor(),
    ROEFactor(), ROICFactor(), GrossMarginFactor(), NetMarginFactor(),
    RevenueGrowthFactor(), NetProfitGrowthFactor(), CashflowGrowthFactor(),
    PriceMomentum3M(), PriceMomentum6M(), PriceMomentum12M(),
    NorthBoundFlowFactor(), MarginChangeFactor(),
    Volatility60D(), MaxDrawdown120D(),
    DebtRatioFactor(), CurrentRatioFactor(),
]


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


@router.post("/run")
async def run_signal_generation(
    pool: str = Query("沪深300", description="选股池名称"),
    top_n: int = Query(30, description="TOP-N 排名数量"),
):
    """运行完整的信号生成管道"""
    try:
        adapter = get_adapter()
        mgr = UniverseManager(adapter)
        stocks = mgr.get_universe(pool)

        if not stocks:
            return JSONResponse({
                "success": False,
                "error": f"选股池 [{pool}] 无可用股票，请检查Tushare连接",
            }, status_code=400)

        # Phase 1: 无实际数据获取 — 管道结构就位，因子计算依赖外部数据
        stock_data = {}

        builder = FactorMatrixBuilder(factors=ALL_FACTORS)
        matrix = builder.build(stocks, stock_data)

        normalizer = CrossSectionalNormalizer(method="zscore")
        matrix = normalizer.normalize(matrix)

        scorer = WeightedScorer(DEFAULT_FACTOR_CONFIGS)
        composite_scores = scorer.score(matrix)

        ranker = Ranker(top_n=top_n, max_price=15.0)
        ranked = ranker.rank(matrix, composite_scores, stocks)

        optimizer = ConstraintOptimizer()
        optimized = optimizer.optimize(ranked, composite_scores)

        signal_gen = SignalGenerator()
        trade_list = signal_gen.generate(
            optimized_stocks=optimized,
            scores=composite_scores,
            current_holdings=set(),
            universe=pool,
        )

        return JSONResponse({
            "success": True,
            "date": str(trade_list.date),
            "universe": pool,
            "total_stocks_analyzed": len(stocks),
            "top_10": [
                {
                    "rank": i + 1,
                    "code": s.code,
                    "name": s.name,
                    "industry": s.industry,
                    "score": round(composite_scores.get(s.code, 0), 4),
                }
                for i, s in enumerate(ranked[:10])
            ],
            "signals": [
                {
                    "code": s.stock_code,
                    "name": s.stock_name,
                    "action": s.action,
                    "score": round(s.composite_score, 4),
                    "weight": round(s.target_weight, 4),
                    "reason": s.reason,
                }
                for s in trade_list.signals
            ],
        })
    except Exception as e:
        logger.error(f"信号生成失败: {e}", exc_info=True)
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
