"""
分析结果数据类 — FA Pro v11
========================
所有分析器返回的结构化数据，用于：
  - 统一评分接口
  - 综合报告生成
  - 数据可视化（雷达图等）
  - AI分析数据输入
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


# ============================================================================
# L1: 基础市场画像
# ============================================================================

@dataclass
class MarketResult:
    """市场行情分析结果"""
    stock_code: str = ""
    company_name: str = ""
    industry: str = ""
    current_price: float = 0.0
    price_change_pct: float = 0.0
    volume: float = 0.0
    market_cap_yi: float = 0.0       # 总市值（亿元）
    pe_ttm: float = 0.0
    pb: float = 0.0
    turnover_rate: float = 0.0       # 换手率%
    volatility_annual: float = 0.0   # 年化波动率%
    beta_estimated: float = 0.0      # 估算Beta


# ============================================================================
# L2: 会计质量 + 欺诈检测
# ============================================================================

@dataclass
class AuditStructuredResult:
    """财务审计结构化结果"""
    total_score: float = 0.0          # 综合审计评分 0-100
    risk_level: str = ""              # 风险等级
    risk_icon: str = ""               # 风险图标
    total_signals: int = 0            # 总信号数
    high_signals: int = 0             # 高风险信号数
    medium_signals: int = 0           # 中风险信号数
    low_signals: int = 0              # 低风险信号数
    dimensions: dict[str, Any] = field(default_factory=dict)  # 各维度评分明细
    signals_detail: list[dict] = field(default_factory=list)   # 信号详情
    radar_data: dict[str, float] = field(default_factory=dict) # 雷达图数据
    heatmap_data: list[dict] = field(default_factory=list)     # 热力图数据
    recommendations: list[str] = field(default_factory=list)   # 排查建议


# ============================================================================
# L3: 财务健康 — 比率分析
# ============================================================================

@dataclass
class FinancialHealthResult:
    """财务健康综合评分"""
    profitability_score: float = 0.0   # 盈利能力评分
    solvency_score: float = 0.0        # 偿债能力评分
    efficiency_score: float = 0.0      # 营运能力评分
    growth_score: float = 0.0          # 成长能力评分
    composite_score: float = 0.0       # 综合评分
    rating: str = ""                   # 综合评级

    # 明细
    ratios: dict[str, dict] = field(default_factory=dict)
    trend_scores: dict[str, float] = field(default_factory=dict)
    peer_scores: dict[str, float] = field(default_factory=dict)

    # 杜邦驱动分类
    dupont_driver: str = ""           # "高利润率驱动"/"高周转驱动"/"高杠杆驱动"


# ============================================================================
# L4: 盈利能力 + 杜邦
# ============================================================================

@dataclass
class ProfitabilityResult:
    """盈利能力深度分析"""
    roe: float = 0.0
    roe_trend: list[float] = field(default_factory=list)
    roa: float = 0.0
    gross_margin: float = 0.0
    net_margin: float = 0.0
    operating_margin: float = 0.0

    # 杜邦分解
    dupont_3factor: dict[str, float] = field(default_factory=dict)
    dupont_driver: str = ""

    # ROIC
    roic: float = 0.0
    roic_spread: float = 0.0         # ROIC - WACC

    # 评分
    score: float = 0.0
    rating: str = ""

    # 诊断
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)


# ============================================================================
# L5: 成长 + 现金流质量
# ============================================================================

@dataclass
class GrowthQualityResult:
    """成长与质量分析"""
    # 成长性
    revenue_growth: float = 0.0        # 近5年营收CAGR%
    profit_growth: float = 0.0         # 近5年净利润CAGR%
    asset_growth: float = 0.0
    growth_score: float = 0.0

    # 盈利质量
    cf_to_profit: float = 0.0         # 经营现金流/净利润
    revenue_cash_ratio: float = 0.0   # 销售回款/营收
    accrual_ratio: float = 0.0        # 应计利润/总资产

    # 现金流画像 (参照教材第8章)
    cashflow_portrait: str = ""       # 妖精型/老母鸡型/蛮牛型/奶牛型/危险型
    cashflow_portrait_stability: str = ""  # 画像稳定性评价

    # FCF
    fcf: float = 0.0                  # 自由现金流（亿元）
    fcf_yield: float = 0.0            # FCF收益率%
    fcf_trend: list[float] = field(default_factory=list)

    # 评分
    quality_score: float = 0.0
    overall_score: float = 0.0
    rating: str = ""


# ============================================================================
# L6: 估值
# ============================================================================

@dataclass
class ValuationResult:
    """估值分析结果"""
    # 当前市场定价
    current_pe: float = 0.0
    current_pb: float = 0.0
    current_ps: float = 0.0
    ev_ebitda: float = 0.0

    # PE
    pe_percentile: float = 0.0        # 历史PE分位数%
    pe_avg_5y: float = 0.0

    # DCF估值
    dcf_fair_price: float = 0.0
    dcf_wacc: float = 0.0
    dcf_upside: float = 0.0

    # 相对估值
    peer_pe_median: float = 0.0
    peer_pb_median: float = 0.0
    relative_discount_pct: float = 0.0  # 相对同业的折价/溢价%

    # 综合
    fair_value_range: tuple = (0, 0)   # 公允价值区间
    valuation_rating: str = ""         # 低估/合理/高估
    valuation_score: float = 0.0       # 估值吸引力评分 0-100

    # 敏感性
    sensitivity: dict = field(default_factory=dict)
    scenarios: dict = field(default_factory=dict)


# ============================================================================
# L7: 综合投资建议
# ============================================================================

@dataclass
class InvestmentThesis:
    """综合投资分析报告"""
    stock_code: str = ""
    company_name: str = ""
    industry: str = ""

    # 综合评级
    overall_rating: str = ""          # 强烈推荐/推荐/中性/回避/强烈回避
    overall_score: float = 0.0        # 综合评分 0-100
    star_rating: str = ""             # ★★★★☆

    # 7维评分
    business_score: float = 0.0       # L1 商业模式
    accounting_quality_score: float = 0.0  # L2 会计质量
    financial_health_score: float = 0.0    # L3 财务健康
    profitability_score: float = 0.0       # L4 盈利能力
    growth_quality_score: float = 0.0      # L5 成长质量
    valuation_score: float = 0.0           # L6 估值吸引力

    # 估值概述
    fair_value_range: tuple = (0, 0)
    current_price: float = 0.0
    upside_potential: float = 0.0

    # 关键亮点与风险
    strengths: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    catalysts: list[str] = field(default_factory=list)

    # 核心指标
    key_metrics: dict[str, Any] = field(default_factory=dict)
    peer_ranking: dict[str, int] = field(default_factory=dict)

    # 雷达图数据
    radar_data: dict[str, float] = field(default_factory=dict)
