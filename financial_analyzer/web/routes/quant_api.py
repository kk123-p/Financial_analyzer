"""量化策略 API 路由"""
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from financial_analyzer.quant.universe import UniverseManager
from financial_analyzer.quant.data_fetcher import QuantDataFetcher
from financial_analyzer.quant.factors.value import (
    PEFactor, PBFactor, PSFactor, DividendYieldFactor, FCFYieldFactor,
)
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
]

ALL_FACTORS = [
    PEFactor(), PBFactor(), PSFactor(), FCFYieldFactor(), DividendYieldFactor(),
    ROEFactor(), ROICFactor(), GrossMarginFactor(), NetMarginFactor(),
    RevenueGrowthFactor(), NetProfitGrowthFactor(), CashflowGrowthFactor(),
    PriceMomentum3M(), PriceMomentum6M(), PriceMomentum12M(),
    NorthBoundFlowFactor(), MarginChangeFactor(),
    Volatility60D(), MaxDrawdown120D(),
    DebtRatioFactor(), CurrentRatioFactor(),
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


@router.post("/run")
async def run_signal_generation(
    pool: str = Query("沪深300", description="选股池名称"),
    top_n: int = Query(30, description="TOP-N 排名数量"),
    skip_data_fetch: bool = Query(False, description="跳过数据获取（仅测试管道结构）"),
):
    """运行完整的信号生成管道"""
    try:
        adapter = get_adapter()
        _load_token(adapter)

        mgr = UniverseManager(adapter)
        stocks = mgr.get_universe(pool)

        if not stocks:
            return JSONResponse({
                "success": False,
                "error": f"选股池 [{pool}] 无可用股票，请检查Tushare连接",
            }, status_code=400)

        logger.info(f"选股池 [{pool}]: {len(stocks)} 只成分股")

        # P0: 批量获取因子数据
        if skip_data_fetch:
            stock_data = {}
            logger.warning("跳过数据获取，管道将产生空结果")
        else:
            fetcher = QuantDataFetcher(adapter, start_date="20230101")
            stocks = fetcher.enrich_stock_info(stocks)
            stock_data = fetcher.fetch_all(stocks)

        stocks_with_data = [
            s for s in stocks if s.code in stock_data
        ]
        logger.info(
            f"数据获取完成: {len(stocks_with_data)}/{len(stocks)} 只有效数据"
        )
        if len(stocks_with_data) < 5:
            return JSONResponse({
                "success": False,
                "error": (
                    f"有效数据不足: {len(stocks_with_data)} 只股票"
                    f"（共 {len(stocks)} 只在池中）。请检查 Tushare 权限和网络。"
                ),
                "total_stocks_analyzed": len(stocks),
                "valid_stocks": len(stocks_with_data),
            }, status_code=400)

        # 构建因子矩阵
        builder = FactorMatrixBuilder(factors=ALL_FACTORS)
        matrix = builder.build(stocks_with_data, stock_data)
        logger.info(
            f"因子矩阵: {len(matrix.stocks)} 只股票, "
            f"{len(matrix.scores.get(matrix.stocks[0], {}) if matrix.stocks else 0)} 个因子/只"
        )

        if len(matrix.stocks) < 5:
            return JSONResponse({
                "success": False,
                "error": f"因子计算后有效股票不足: {len(matrix.stocks)} 只",
                "total_stocks_analyzed": len(stocks),
            }, status_code=400)

        # 截面标准化
        normalizer = CrossSectionalNormalizer(method="zscore")
        matrix = normalizer.normalize(matrix)

        # 加权打分
        scorer = WeightedScorer(DEFAULT_FACTOR_CONFIGS)
        composite_scores = scorer.score(matrix)

        # 排名 + 硬过滤
        ranker = Ranker(top_n=top_n, max_price=15.0)
        ranked = ranker.rank(matrix, composite_scores, stocks_with_data)
        logger.info(f"排名过滤后: {len(ranked)} 只进入TOP-{top_n}")

        if not ranked:
            return JSONResponse({
                "success": False,
                "error": "没有股票通过排名和过滤条件",
                "total_stocks_analyzed": len(stocks),
            }, status_code=400)

        # 约束优化
        optimizer = ConstraintOptimizer()
        optimized = optimizer.optimize(ranked, composite_scores)
        logger.info(f"约束优化后: {len(optimized)} 只")

        if not optimized:
            return JSONResponse({
                "success": False,
                "error": "约束优化后无股票入选",
                "total_stocks_analyzed": len(stocks),
            }, status_code=400)

        # 信号生成
        signal_gen = SignalGenerator()
        trade_list = signal_gen.generate(
            optimized_stocks=optimized,
            scores=composite_scores,
            current_holdings=set(),
            universe=pool,
        )

        # 构建响应中的排名列表（含股价信息）
        prices_from_data = {}
        for code, data in stock_data.items():
            daily = data.get("daily")
            if daily is not None and not daily.empty and "close" in daily.columns:
                prices_from_data[code] = float(daily["close"].iloc[0])

        return JSONResponse({
            "success": True,
            "date": str(trade_list.date),
            "universe": pool,
            "total_stocks_analyzed": len(stocks),
            "valid_stocks": len(stocks_with_data),
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
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
