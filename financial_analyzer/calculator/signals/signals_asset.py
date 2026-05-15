"""
资产端审计信号
=====================
包含原有6个信号 + 新增2个信号，共8个资产端检测。
"""
from ..audit_engine import (
    Signal, SignalLevel, SignalCategory, SignalRegistry,
    AuditThresholds, DEFAULT_THRESHOLDS,
)
import pandas as pd
from ...logging_config import get_logger

logger = get_logger(__name__)


def _v(row: dict, keys: list, default=None):
    """从dict中按多个key名取值"""
    if row is None:
        return default
    for k in keys:
        if k in row and row[k] is not None:
            try:
                v = float(row[k])
                if not pd.isna(v):
                    return v
            except (ValueError, TypeError):
                pass
    return default


# ============================================================================
# 1. 存贷双高
# ============================================================================
@SignalRegistry.register("asset_cash_debt", SignalCategory.ASSET,
                         "存贷双高", "账面货币资金充裕却有大量有息负债")
def check_cash_debt(current, previous, ctx):
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    total_assets = _v(current, ["total_assets"])
    cash = _v(current, ["money_cap", "cash"])
    short_loan = _v(current, ["short_loan", "short_term_loans"], 0)
    long_loan = _v(current, ["long_loan", "long_term_loans"], 0)
    bonds = _v(current, ["bonds_payable"], 0)
    interest_debt = short_loan + long_loan + bonds

    if not (cash and total_assets and total_assets > 0):
        return None

    cash_ratio = cash / total_assets
    debt_ratio = interest_debt / total_assets if interest_debt else 0

    if cash_ratio > th.cash_debt_cash_ratio and debt_ratio > th.cash_debt_debt_ratio:
        # 进一步计算利息收入/货币资金比率
        interest_income = _v(current, ["interest_income"])
        interest_rate_info = ""
        if interest_income and cash > 0:
            ir = interest_income / cash
            if ir < 0.02:
                interest_rate_info = f"，利息收入/货币资金={ir:.2%}（极低，疑似假存款）"

        level = SignalLevel.HIGH if debt_ratio > 0.4 else SignalLevel.MEDIUM
        return Signal(
            id="asset_cash_debt",
            name="存贷双高",
            category=SignalCategory.ASSET,
            level=level,
            value=f"现金占总资产 {cash_ratio:.1%}，有息负债占总资产 {debt_ratio:.1%}",
            threshold=f"现金>{th.cash_debt_cash_ratio:.0%} 且 有息负债>{th.cash_debt_debt_ratio:.0%}",
            conclusion="账面资金充裕却大量举债，可能存在虚假存款或资金被占用" + interest_rate_info,
            raw_value=cash_ratio,
            threshold_value=th.cash_debt_cash_ratio,
        )
    return None


# ============================================================================
# 2. 应收账款异常
# ============================================================================
@SignalRegistry.register("asset_ar_anomaly", SignalCategory.ASSET,
                         "应收账款异常", "应收账款增速远超营收增速")
def check_ar_anomaly(current, previous, ctx):
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    if not previous:
        return None

    ar = _v(current, ["accounts_receivable", "accounts_receiv", "acc_receivable"])
    ar_prev = _v(previous, ["accounts_receivable", "accounts_receiv", "acc_receivable"])
    revenue = _v(current, ["revenue", "total_revenue"])
    revenue_prev = _v(previous, ["revenue", "total_revenue"])

    if not all([ar, ar_prev, ar_prev > 0, revenue, revenue_prev, revenue_prev > 0]):
        return None

    ar_growth = (ar - ar_prev) / ar_prev
    rev_growth = (revenue - revenue_prev) / revenue_prev
    gap = ar_growth - rev_growth

    if gap > th.ar_revenue_gap:
        level = SignalLevel.HIGH if gap > 0.3 else SignalLevel.MEDIUM
        return Signal(
            id="asset_ar_anomaly",
            name="应收账款异常增长",
            category=SignalCategory.ASSET,
            level=level,
            value=f"应收增速 {ar_growth:.1%}，营收增速 {rev_growth:.1%}，差异 {gap:.1%}",
            threshold=f"应收增速-营收增速 > {th.ar_revenue_gap:.0%}",
            conclusion="应收账款增速远超营收，可能存在虚增收入形成不可收回的白条",
            raw_value=gap,
            threshold_value=th.ar_revenue_gap,
        )
    return None


# ============================================================================
# 3. 存货周转异常
# ============================================================================
@SignalRegistry.register("asset_inventory", SignalCategory.ASSET,
                         "存货周转异常", "存货增速远超成本增速")
def check_inventory(current, previous, ctx):
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    if not previous:
        return None

    inv = _v(current, ["inventories", "inventory"])
    inv_prev = _v(previous, ["inventories", "inventory"])
    cost = _v(current, ["oper_cost", "operating_cost"])
    cost_prev = _v(previous, ["oper_cost", "operating_cost"])

    if not (inv and inv_prev and inv_prev > 0):
        return None

    inv_growth = (inv - inv_prev) / inv_prev
    cost_growth = (cost - cost_prev) / cost_prev if cost and cost_prev and cost_prev > 0 else 0
    gap = inv_growth - cost_growth

    if gap > th.inventory_cost_gap:
        level = SignalLevel.HIGH if gap > 0.5 else SignalLevel.MEDIUM
        return Signal(
            id="asset_inventory",
            name="存货周转异常",
            category=SignalCategory.ASSET,
            level=level,
            value=f"存货增速 {inv_growth:.1%}，成本增速 {cost_growth:.1%}，差异 {gap:.1%}",
            threshold=f"存货增速-成本增速 > {th.inventory_cost_gap:.0%}",
            conclusion="存货增速远超成本增速，可能存在虚构存货或延期摊销成本",
            raw_value=gap,
            threshold_value=th.inventory_cost_gap,
        )
    return None


# ============================================================================
# 4. 商誉风险
# ============================================================================
@SignalRegistry.register("asset_goodwill", SignalCategory.ASSET,
                         "商誉减值风险", "商誉占净资产比重过高")
def check_goodwill(current, previous, ctx):
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    goodwill = _v(current, ["goodwill"])
    equity = _v(current, ["total_hldr_eqy_exc_min_int", "total_equity", "equity"])

    if not (goodwill and equity and equity > 0):
        return None

    gw_ratio = goodwill / equity
    if gw_ratio > th.goodwill_equity_ratio:
        level = SignalLevel.HIGH if gw_ratio > 0.5 else SignalLevel.MEDIUM
        return Signal(
            id="asset_goodwill",
            name="商誉减值风险",
            category=SignalCategory.ASSET,
            level=level,
            value=f"商誉/净资产 = {gw_ratio:.1%}",
            threshold=f"商誉/净资产 > {th.goodwill_equity_ratio:.0%}",
            conclusion="高额并购商誉，后续减值测试主观性强，存在利润蓄水池风险",
            raw_value=gw_ratio,
            threshold_value=th.goodwill_equity_ratio,
        )
    return None


# ============================================================================
# 5. 在建工程异常
# ============================================================================
@SignalRegistry.register("asset_cip", SignalCategory.ASSET,
                         "在建工程异常", "在建工程金额大且增速异常")
def check_cip(current, previous, ctx):
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    total_assets = _v(current, ["total_assets"])
    cip = _v(current, ["construction_in_process", "cip"])

    if not (cip and total_assets and total_assets > 0):
        return None

    cip_ratio = cip / total_assets
    if cip_ratio > th.cip_asset_ratio and previous:
        cip_prev = _v(previous, ["construction_in_process", "cip"])
        if cip_prev and cip_prev > 0:
            cip_growth = (cip - cip_prev) / cip_prev
            if cip_growth > th.cip_growth:
                return Signal(
                    id="asset_cip",
                    name="在建工程异常",
                    category=SignalCategory.ASSET,
                    level=SignalLevel.MEDIUM,
                    value=f"在建工程/总资产={cip_ratio:.1%}，增速={cip_growth:.1%}",
                    threshold=f"在建工程/总资产>{th.cip_asset_ratio:.0%} 且 增速>{th.cip_growth:.0%}",
                    conclusion="在建工程占比高且快速增长，可能存在虚增工程造价或延迟转固",
                    raw_value=cip_ratio,
                    threshold_value=th.cip_asset_ratio,
                )
    return None


# ============================================================================
# 6. 预付账款异常
# ============================================================================
@SignalRegistry.register("asset_prepayment", SignalCategory.ASSET,
                         "预付账款异常", "预付账款占总资产比例过高")
def check_prepayment(current, previous, ctx):
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    total_assets = _v(current, ["total_assets"])
    prepay = _v(current, ["prepayment", "prepayment_for_assets"])

    if not (prepay and total_assets and total_assets > 0):
        return None

    pp_ratio = prepay / total_assets
    if pp_ratio > th.prepayment_asset_ratio:
        return Signal(
            id="asset_prepayment",
            name="预付账款异常",
            category=SignalCategory.ASSET,
            level=SignalLevel.MEDIUM,
            value=f"预付账款/总资产 = {pp_ratio:.1%}",
            threshold=f"预付账款/总资产 > {th.prepayment_asset_ratio:.0%}",
            conclusion="预付账款占比高，可能存在通过预付款项体外循环套取资金",
            raw_value=pp_ratio,
            threshold_value=th.prepayment_asset_ratio,
        )
    return None


# ============================================================================
# 7. [新增] 利息收入/货币资金异常（假存款识别）
# ============================================================================
@SignalRegistry.register("asset_interest_income", SignalCategory.ASSET,
                         "利息收入异常", "利息收入/货币资金比率过低，疑似假存款")
def check_interest_income(current, previous, ctx):
    """
    参考文档：计算"利息收入/货币资金"比率，若极低（如<2%），则为危险信号。
    存款大概率是假的，或资金被大股东占用。
    """
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    cash = _v(current, ["money_cap", "cash"])
    interest_income = _v(current, ["interest_income"])

    if not (cash and cash > 0 and interest_income is not None):
        return None

    ir = interest_income / cash
    if ir < th.interest_income_rate:
        level = SignalLevel.HIGH if ir < 0.01 else SignalLevel.MEDIUM
        return Signal(
            id="asset_interest_income",
            name="利息收入/货币资金异常偏低",
            category=SignalCategory.ASSET,
            level=level,
            value=f"利息收入/货币资金 = {ir:.2%}（利息收入={interest_income:.0f}，货币资金={cash:.0f}）",
            threshold=f"利息收入/货币资金 > {th.interest_income_rate:.0%}",
            conclusion="大量货币资金却产生极少利息收入，疑似虚假存款或资金被占用",
            raw_value=ir,
            threshold_value=th.interest_income_rate,
        )
    return None


# ============================================================================
# 8. [新增] 应收账款账龄分析
# ============================================================================
@SignalRegistry.register("asset_ar_aging", SignalCategory.ASSET,
                         "应收账款账龄恶化", "长账龄应收占比过高")
def check_ar_aging(current, previous, ctx):
    """
    参考文档：检查账龄，警惕长账龄款项占比过高。
    数据来源：应收账款账龄明细（如有）
    """
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)

    # 尝试从context获取账龄数据（可能由上层预处理）
    aging_data = ctx.get("ar_aging_data")
    if not aging_data:
        return None

    total_ar = aging_data.get("total_ar", 0)
    long_term_ar = aging_data.get("long_term_ar", 0)  # 1年以上

    if not (total_ar and total_ar > 0):
        return None

    long_ratio = long_term_ar / total_ar
    if long_ratio > th.ar_aging_high_ratio:
        level = SignalLevel.HIGH if long_ratio > 0.5 else SignalLevel.MEDIUM
        return Signal(
            id="asset_ar_aging",
            name="应收账款账龄恶化",
            category=SignalCategory.ASSET,
            level=level,
            value=f"长账龄(>1年)应收占比 = {long_ratio:.1%}（长账龄={long_term_ar:.0f}，总应收={total_ar:.0f}）",
            threshold=f"长账龄占比 > {th.ar_aging_high_ratio:.0%}",
            conclusion="长账龄应收占比过高，回收风险大，可能包含大量坏账",
            raw_value=long_ratio,
            threshold_value=th.ar_aging_high_ratio,
        )
    return None
