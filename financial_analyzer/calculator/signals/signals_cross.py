"""
勾稽验证审计信号
=====================
包含原有3个信号 + 新增2个信号，共5个勾稽检测。
"""
from ..audit_engine import (
    Signal, SignalLevel, SignalCategory, SignalRegistry,
    AuditThresholds, DEFAULT_THRESHOLDS,
)
from ...logging_config import get_logger

logger = get_logger(__name__)


def _v(row, keys, default=None):
    if row is None:
        return default
    for k in keys:
        if k in row and row[k] is not None:
            try:
                import pandas as pd
                v = float(row[k])
                if not pd.isna(v):
                    return v
            except (ValueError, TypeError):
                pass
    return default


# ============================================================================
# 1. 收入-资产增长不匹配
# ============================================================================
@SignalRegistry.register("cross_rev_asset", SignalCategory.CROSS_VALIDATION,
                         "收入-资产增长不匹配", "营收高增长但资产未同步增长")
def check_rev_asset(current, previous, ctx):
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    if not previous:
        return None

    revenue = _v(current, ["revenue", "total_revenue"])
    revenue_prev = _v(previous, ["revenue", "total_revenue"])
    total_assets = _v(current, ["total_assets"])
    ta_prev = _v(previous, ["total_assets"])

    if not all([revenue, revenue_prev, revenue_prev > 0, total_assets, ta_prev, ta_prev > 0]):
        return None

    rev_growth = (revenue - revenue_prev) / revenue_prev
    ta_growth = (total_assets - ta_prev) / ta_prev

    if rev_growth > th.rev_growth_threshold and ta_growth < th.asset_growth_low:
        level = SignalLevel.HIGH if rev_growth > 0.5 else SignalLevel.MEDIUM
        return Signal(
            id="cross_rev_asset",
            name="收入-资产增长不匹配",
            category=SignalCategory.CROSS_VALIDATION,
            level=level,
            value=f"营收增速 {rev_growth:.1%}，资产增速 {ta_growth:.1%}",
            threshold=f"营收增速>{th.rev_growth_threshold:.0%} 且 资产增速>{th.asset_growth_low:.0%}",
            conclusion="营收高增长但资产未同步增长，需验证收入真实性",
            raw_value=rev_growth,
            threshold_value=th.rev_growth_threshold,
        )
    return None


# ============================================================================
# 2. 税负不匹配
# ============================================================================
@SignalRegistry.register("cross_tax_burden", SignalCategory.CROSS_VALIDATION,
                         "税负不匹配", "收入增长但税负率异常偏低")
def check_tax_burden(current, previous, ctx):
    """
    参考文档：收入大幅增长，但所缴纳的增值税或所得税增长不明显。
    计算"支付的各项税费/营业收入"比率。
    """
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    revenue = _v(current, ["revenue", "total_revenue"])
    net_profit = _v(current, ["net_profit", "n_income", "n_income_attr_p"])
    tax_paid = _v(current, ["income_tax", "taxes_and_surcharges"])

    if not (revenue and revenue > 0 and net_profit and net_profit > 0):
        return None

    if tax_paid is not None:
        # 有效税率 = 所得税 / (净利润 + 所得税)
        denominator = net_profit + tax_paid
        if denominator > 0:
            tax_rate = tax_paid / denominator
            if tax_rate < th.tax_rate_low:
                return Signal(
                    id="cross_tax_burden",
                    name="所得税税负异常偏低",
                    category=SignalCategory.CROSS_VALIDATION,
                    level=SignalLevel.MEDIUM,
                    value=f"有效税率 = {tax_rate:.1%}",
                    threshold=f"有效税率 > {th.tax_rate_low:.0%}",
                    conclusion="收入增长但税负不成比例，财务造假通常不配合真金白银纳税",
                    raw_value=tax_rate,
                    threshold_value=th.tax_rate_low,
                )
    return None


# ============================================================================
# 3. 资产负债表平衡性校验
# ============================================================================
@SignalRegistry.register("cross_balance_check", SignalCategory.CROSS_VALIDATION,
                         "资产负债表失衡", "资产 ≠ 负债 + 所有者权益")
def check_balance(current, previous, ctx):
    total_assets = _v(current, ["total_assets"])
    total_liab = _v(current, ["total_liab"])
    equity = _v(current, ["total_hldr_eqy_exc_min_int", "total_equity"])

    if not (total_assets and total_liab and equity):
        return None

    diff = abs(total_assets - total_liab - equity)
    if diff > total_assets * 0.01:
        return Signal(
            id="cross_balance_check",
            name="资产负债表失衡",
            category=SignalCategory.CROSS_VALIDATION,
            level=SignalLevel.HIGH,
            value=f"资产-负债-权益差异 = {diff:.0f}",
            threshold="差异 < 总资产的1%",
            conclusion="财务报表数据存在勾稽错误，数据质量存疑",
            raw_value=diff / total_assets,
            threshold_value=0.01,
        )
    return None


# ============================================================================
# 4. [新增] 增值税税负验证
# ============================================================================
@SignalRegistry.register("cross_vat_burden", SignalCategory.CROSS_VALIDATION,
                         "增值税税负异常", "增值税税负率远低于行业水平")
def check_vat_burden(current, previous, ctx):
    """
    参考文档：计算"支付的各项税费/营业收入"比率，并与行业水平和历史数据对比。
    """
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    revenue = _v(current, ["revenue", "total_revenue"])
    # "支付的各项税费" 在现金流量表中
    taxes_paid = _v(current, [
        "taxes_and_surcharges", "total_tax", "pay_all_tax",
    ])

    if not (revenue and revenue > 0 and taxes_paid and taxes_paid > 0):
        return None

    vat_burden = taxes_paid / revenue

    # 与历史对比
    if previous:
        rev_prev = _v(previous, ["revenue", "total_revenue"])
        tax_prev = _v(previous, ["taxes_and_surcharges", "total_tax", "pay_all_tax"])
        if rev_prev and rev_prev > 0 and tax_prev and tax_prev > 0:
            prev_burden = tax_prev / rev_prev
            # 税负率大幅下降
            if vat_burden < prev_burden * 0.7 and vat_burden < th.vat_burden_low:
                return Signal(
                    id="cross_vat_burden",
                    name="增值税税负率大幅下降",
                    category=SignalCategory.CROSS_VALIDATION,
                    level=SignalLevel.MEDIUM,
                    value=f"综合税负率: {prev_burden:.2%} → {vat_burden:.2%}",
                    threshold=f"税负率 > {th.vat_burden_low:.0%} 且 无大幅下降",
                    conclusion="税负率大幅下降且低于行业水平，收入增长的真实性存疑",
                    raw_value=vat_burden,
                    threshold_value=th.vat_burden_low,
                )

    # 绝对值检测
    if vat_burden < th.vat_burden_low:
        return Signal(
            id="cross_vat_burden",
            name="增值税税负率异常偏低",
            category=SignalCategory.CROSS_VALIDATION,
            level=SignalLevel.LOW,
            value=f"综合税负率 = {vat_burden:.2%}",
            threshold=f"税负率 > {th.vat_burden_low:.0%}",
            conclusion="税负率偏低，需与同行业对比确认是否异常",
            raw_value=vat_burden,
            threshold_value=th.vat_burden_low,
        )
    return None


# ============================================================================
# 5. [新增] 收入-现金流勾稽验证
# ============================================================================
@SignalRegistry.register("cross_rev_cash", SignalCategory.CROSS_VALIDATION,
                         "收入-现金流勾稽异常", "营收×(1+税率) ≠ 销售回款+应收增加")
def check_rev_cash_cross(current, previous, ctx):
    """
    参考文档：用公式"营业收入×(1+税率) ≈ 销售商品收到现金+应收账款增加"进行勾稽验证。
    """
    revenue = _v(current, ["revenue", "total_revenue"])
    cash_receipts = _v(current, [
        "c_fr_sale_sg", "cash_received_from_sales", "c_fr_sg"
    ])

    if not previous:
        return None

    ar = _v(current, ["accounts_receivable", "accounts_receiv", "acc_receivable"])
    ar_prev = _v(previous, ["accounts_receivable", "accounts_receiv", "acc_receivable"])

    if not (revenue and revenue > 0 and cash_receipts and ar is not None and ar_prev is not None):
        return None

    ar_increase = ar - ar_prev
    # 估算：营收×1.13（含增值税） ≈ 销售回款 + 应收增加
    expected_receipts = revenue * 1.13
    actual_receipts = cash_receipts + ar_increase

    # 单位处理
    if expected_receipts > 0 and actual_receipts > 0:
        ratio = actual_receipts / expected_receipts
        if ratio > 100:  # 单位不一致
            expected_receipts = revenue * 10000 * 1.13
            ratio = actual_receipts / expected_receipts

        # 偏差超过30%
        if ratio > 0 and abs(1 - ratio) > 0.3:
            level = SignalLevel.HIGH if abs(1 - ratio) > 0.5 else SignalLevel.MEDIUM
            direction = "高于" if ratio > 1 else "低于"
            return Signal(
                id="cross_rev_cash",
                name="收入-现金流勾稽异常",
                category=SignalCategory.CROSS_VALIDATION,
                level=level,
                value=f"实际回款/理论回款 = {ratio:.2f}（{direction}预期）",
                threshold="实际回款/理论回款 在 0.7-1.3 之间",
                conclusion="营收与现金流勾稽关系异常，收入确认的真实性需核查",
                raw_value=ratio,
                threshold_value=0.7,
            )
    return None
