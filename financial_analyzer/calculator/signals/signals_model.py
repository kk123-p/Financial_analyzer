"""
模型预警信号（全新）
=====================
整合 M-score、Z-score、signal_detector 的矛盾信号。
将深度分析模型的结果转化为审计信号。
"""
from ..audit_engine import (
    Signal, SignalLevel, SignalCategory, SignalRegistry,
    AuditThresholds, DEFAULT_THRESHOLDS,
)
from ...utils.helpers import val_from_row as _v
from ...logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# 1. M-score 盈余管理预警
# ============================================================================
@SignalRegistry.register("model_mscore", SignalCategory.MODEL,
                         "M-score盈余管理预警", "Beneish M-score检测到盈余管理嫌疑")
def check_mscore(current, previous, ctx):
    """
    M-score > -1.78 表示存在盈余管理嫌疑。
    从context中获取已计算的M-score结果。
    """
    mscore_data = ctx.get("mscore")
    if not mscore_data:
        return None

    m_score = mscore_data.get("m_score")
    if m_score is None:
        return None

    if m_score > -1.78:
        components = mscore_data.get("components", {})
        detail_parts = []
        if components.get("DSRI_应收天数指数", 1) > 1.4:
            detail_parts.append("应收天数异常增长")
        if components.get("SGI_营收增长指数", 1) > 1.5:
            detail_parts.append("营收增速异常")
        if components.get("TATA_应计比率", 0) > 0.05:
            detail_parts.append("应计利润占比高")

        detail = "；".join(detail_parts) if detail_parts else "多项指标综合触发"

        return Signal(
            id="model_mscore",
            name="M-score盈余管理预警",
            category=SignalCategory.MODEL,
            level=SignalLevel.HIGH if m_score > -1.0 else SignalLevel.MEDIUM,
            value=f"M-score = {m_score:.2f}（阈值 > -1.78）",
            threshold="M-score < -1.78",
            conclusion=f"存在盈余管理嫌疑。{detail}",
            detail=detail,
            raw_value=m_score,
            threshold_value=-1.78,
        )
    return None


# ============================================================================
# 2. Z-score 破产预警
# ============================================================================
@SignalRegistry.register("model_zscore", SignalCategory.MODEL,
                         "Z-score破产预警", "Altman Z-score进入危险区")
def check_zscore(current, previous, ctx):
    """
    Z-score < 1.81 进入危险区（制造业）。
    从context中获取已计算的Z-score结果。
    """
    zscore_data = ctx.get("zscore")
    if not zscore_data:
        return None

    z_score = zscore_data.get("z_score")
    zone = zscore_data.get("zone", "")
    zone_cn = zscore_data.get("zone_cn", "")

    if z_score is None:
        return None

    if zone == "distress":
        return Signal(
            id="model_zscore",
            name="Z-score破产预警",
            category=SignalCategory.MODEL,
            level=SignalLevel.HIGH,
            value=f"Z-score = {z_score:.2f}（{zone_cn}，阈值 < 1.81）",
            threshold="Z-score > 2.99（安全区）",
            conclusion="财务困境风险较高，破产概率大",
            raw_value=z_score,
            threshold_value=1.81,
        )
    elif zone == "grey":
        return Signal(
            id="model_zscore",
            name="Z-score灰色预警",
            category=SignalCategory.MODEL,
            level=SignalLevel.MEDIUM,
            value=f"Z-score = {z_score:.2f}（{zone_cn}，1.81-2.99）",
            threshold="Z-score > 2.99（安全区）",
            conclusion="财务状况不确定，需持续关注",
            raw_value=z_score,
            threshold_value=2.99,
        )
    return None


# ============================================================================
# 3. 盈利质量预警（来自signal_detector）
# ============================================================================
@SignalRegistry.register("model_profit_quality", SignalCategory.MODEL,
                         "盈利质量矛盾预警", "利润增长缺乏现金流支撑")
def check_profit_quality_signal(current, previous, ctx):
    """
    signal_detector信号：(净利润增速 > 20%) & (经营CF/净利润 < 0.5)
    利润增长缺乏现金流支撑。
    """
    if not previous:
        return None

    np_cur = _v(current, ["net_profit", "n_income", "n_income_attr_p"])
    np_prev = _v(previous, ["net_profit", "n_income", "n_income_attr_p"])
    op_cf = _v(current, ["op_cashflow", "n_cashflow_act"])

    if not (np_cur and np_prev and np_prev != 0 and op_cf is not None):
        return None

    np_growth = (np_cur - np_prev) / abs(np_prev)
    cf_ratio = op_cf / np_cur if np_cur != 0 else 0

    if np_growth > 0.20 and cf_ratio < 0.5:
        return Signal(
            id="model_profit_quality",
            name="盈利质量矛盾预警",
            category=SignalCategory.MODEL,
            level=SignalLevel.HIGH,
            value=f"净利润增速={np_growth:.1%}，经营CF/净利润={cf_ratio:.2f}",
            threshold="净利润增速>20% 且 CF/NP>0.5",
            conclusion="利润高增长但缺乏现金流支撑，可能是应计利润，需识别拖累科目（应收增加？存货积压？一次性收益？）",
            raw_value=cf_ratio,
            threshold_value=0.5,
        )
    return None


# ============================================================================
# 4. 增长透支预警（来自signal_detector）
# ============================================================================
@SignalRegistry.register("model_growth_overdraft", SignalCategory.MODEL,
                         "增长透支预警", "高增长依赖放宽信用政策")
def check_growth_overdraft(current, previous, ctx):
    """
    signal_detector信号：(营收增速 > 30%) & (应收增速/营收增速 > 1.5)
    """
    if not previous:
        return None

    rev_cur = _v(current, ["revenue", "total_revenue"])
    rev_prev = _v(previous, ["revenue", "total_revenue"])
    ar_cur = _v(current, ["accounts_receivable", "accounts_receiv"])
    ar_prev = _v(previous, ["accounts_receivable", "accounts_receiv"])

    if not all([rev_cur, rev_prev, ar_cur, ar_prev]):
        return None
    if rev_prev == 0 or ar_prev == 0:
        return None

    rev_growth = (rev_cur - rev_prev) / abs(rev_prev)
    ar_growth = (ar_cur - ar_prev) / abs(ar_prev)

    if rev_growth > 0:
        ar_rev_ratio = ar_growth / rev_growth
    else:
        return None

    if rev_growth > 0.30 and ar_rev_ratio > 1.5:
        return Signal(
            id="model_growth_overdraft",
            name="增长透支预警",
            category=SignalCategory.MODEL,
            level=SignalLevel.HIGH,
            value=f"营收增速={rev_growth:.1%}，应收增速/营收增速={ar_rev_ratio:.2f}",
            threshold="营收增速>30% 且 应收/营收增速<1.5",
            conclusion="高增长依赖放宽信用政策，如果坏账计提增加1个百分点，对净利润冲击较大",
            raw_value=ar_rev_ratio,
            threshold_value=1.5,
        )
    return None


# ============================================================================
# 5. 纸面富贵预警（来自signal_detector）
# ============================================================================
@SignalRegistry.register("model_paper_wealth", SignalCategory.MODEL,
                         "纸面富贵预警", "高ROE完全由杠杆驱动")
def check_paper_wealth(current, previous, ctx):
    """
    signal_detector信号：ROE > 20% & 杠杆贡献率 > 60%
    """
    dupont = ctx.get("dupont_analysis")
    if not dupont:
        return None

    improved = dupont.get("improved", [])
    if not improved:
        return None

    latest = improved[0]
    roe = latest.get("roe")
    lev_contrib = latest.get("leverage_contribution")

    if roe is None or lev_contrib is None:
        return None
    if roe == 0:
        return None

    lev_ratio = abs(lev_contrib) / abs(roe)

    if roe > 20 and lev_ratio > 0.6:
        return Signal(
            id="model_paper_wealth",
            name="纸面富贵预警",
            category=SignalCategory.MODEL,
            level=SignalLevel.HIGH,
            value=f"ROE={roe:.2f}%，杠杆贡献占比={lev_ratio:.1%}",
            threshold="ROE>20% 且 杠杆贡献<60%",
            conclusion="高ROE完全由杠杆驱动，如果利率上升100bp，利息覆盖倍数将显著恶化",
            raw_value=lev_ratio,
            threshold_value=0.6,
        )
    return None


# ============================================================================
# 6. 财务粉饰预警（来自signal_detector）
# ============================================================================
@SignalRegistry.register("model_financial_dress", SignalCategory.MODEL,
                         "财务粉饰预警", "同时存在盈余操纵可能和破产风险")
def check_financial_dress(current, previous, ctx):
    """
    signal_detector信号：M-score > -1.78 且 Z-score < 1.8
    """
    mscore_data = ctx.get("mscore", {})
    zscore_data = ctx.get("zscore", {})

    m_score = mscore_data.get("m_score")
    z_score = zscore_data.get("z_score")

    if m_score is None or z_score is None:
        return None

    if m_score > -1.78 and z_score < 1.8:
        return Signal(
            id="model_financial_dress",
            name="财务粉饰预警",
            category=SignalCategory.MODEL,
            level=SignalLevel.HIGH,
            value=f"M-score={m_score:.2f}（>-1.78），Z-score={z_score:.2f}（<1.8）",
            threshold="M-score<-1.78 且 Z-score>1.8",
            conclusion="同时存在盈余操纵可能和破产风险，需交叉验证收入确认政策与现金流的背离",
        )
    return None
