"""
现金流审计信号
=====================
包含原有3个信号 + 新增1个信号，共4个现金流检测。
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
# 1. 持续负经营现金流
# ============================================================================
@SignalRegistry.register("cf_negative_ocf", SignalCategory.CASHFLOW,
                         "持续负经营现金流", "经营活动现金流连续多年为负")
def check_negative_ocf(current, previous, ctx):
    multi_year = ctx.get("multi_year_data")
    if multi_year and len(multi_year) >= 3:
        ocfs = []
        for period in multi_year[:5]:
            ocf = _v(period, ["op_cashflow", "n_cashflow_act"])
            if ocf is not None:
                ocfs.append(ocf)
        if len(ocfs) >= 3 and all(o < 0 for o in ocfs[:3]):
            return Signal(
                id="cf_negative_ocf",
                name="持续负经营现金流",
                category=SignalCategory.CASHFLOW,
                level=SignalLevel.HIGH,
                value=f"近3年经营现金流均为负: {[f'{o:.0f}' for o in ocfs[:3]]}",
                threshold="经营现金流 > 0",
                conclusion="经营活动持续失血，自身造血能力严重不足",
            )

    # 单期检测
    ocf = _v(current, ["op_cashflow", "n_cashflow_act"])
    if ocf is not None and ocf < 0:
        return Signal(
            id="cf_negative_ocf",
            name="经营现金流为负",
            category=SignalCategory.CASHFLOW,
            level=SignalLevel.LOW,
            value=f"经营现金流 = {ocf:.0f}",
            threshold="经营现金流 > 0",
            conclusion="当期经营现金流为负，需关注持续性",
        )
    return None


# ============================================================================
# 2. 融资依赖
# ============================================================================
@SignalRegistry.register("cf_financing_dep", SignalCategory.CASHFLOW,
                         "外部融资依赖", "靠外部输血维持运营")
def check_financing_dependency(current, previous, ctx):
    multi_year = ctx.get("multi_year_data")
    if not multi_year or len(multi_year) < 3:
        return None

    ocf_list = []
    fcf_list = []
    for period in multi_year[:5]:
        ocf = _v(period, ["op_cashflow", "n_cashflow_act"])
        fcf = _v(period, ["fin_cf", "n_cash_flows_fnc_act", "n_cash_finance_act"])
        if ocf is not None:
            ocf_list.append(ocf)
        if fcf is not None:
            fcf_list.append(fcf)

    if len(fcf_list) >= 3 and len(ocf_list) >= 3:
        # 连续融资净流入但经营现金流差
        if all(f > 0 for f in fcf_list[:3]) and sum(ocf_list[:3]) < 0:
            return Signal(
                id="cf_financing_dep",
                name="外部融资依赖",
                category=SignalCategory.CASHFLOW,
                level=SignalLevel.HIGH,
                value="连续多年筹资活动净流入，但经营活动现金流为负",
                threshold="经营现金流 > 0 或 筹资活动净流出",
                conclusion="企业靠外部输血维持运转，自身造血能力差，资金链断裂风险高",
            )
    return None


# ============================================================================
# 3. 收入-回款不匹配
# ============================================================================
@SignalRegistry.register("cf_revenue_cash", SignalCategory.CASHFLOW,
                         "收入-回款不匹配", "营收大幅增长但销售回款乏力")
def check_revenue_cash(current, previous, ctx):
    """
    参考文档：收入大幅增加，但"销售商品、提供劳务收到的现金"增长乏力。
    用公式：营业收入×(1+税率) ≈ 销售商品收到现金+应收账款增加 进行勾稽验证。
    """
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    revenue = _v(current, ["revenue", "total_revenue"])
    cash_receipts = _v(current, [
        "c_fr_sale_sg", "cash_received_from_sales",
        "c_fr_sg", "sales_cash"
    ])

    if not (revenue and revenue > 0 and cash_receipts):
        return None

    # 注意：tushare的revenue单位是万元，cashflow是元
    # 需要根据数据源判断是否需要乘10000
    receipt_ratio = cash_receipts / revenue if revenue != 0 else 0
    # 如果比值极大，说明单位不一致（revenue是万元，cash是元）
    if receipt_ratio > 100:
        receipt_ratio = cash_receipts / (revenue * 10000) if revenue != 0 else 0

    if 0 < receipt_ratio < th.revenue_cash_receipt:
        level = SignalLevel.HIGH if receipt_ratio < 0.5 else SignalLevel.MEDIUM
        return Signal(
            id="cf_revenue_cash",
            name="收入-回款不匹配",
            category=SignalCategory.CASHFLOW,
            level=level,
            value=f"销售回款/营收 = {receipt_ratio:.1%}",
            threshold=f"销售回款/营收 > {th.revenue_cash_receipt:.0%}",
            conclusion="虚增的收入没有形成真实的现金流入，回款质量差",
            raw_value=receipt_ratio,
            threshold_value=th.revenue_cash_receipt,
        )
    return None


# ============================================================================
# 4. [新增] 连续5年现金流结构模式分析
# ============================================================================
@SignalRegistry.register("cf_structure", SignalCategory.CASHFLOW,
                         "现金流结构异常", "连续多年现金流结构不健康")
def check_cf_structure(current, previous, ctx):
    """
    参考文档：观察连续5年以上的现金流量表结构，判断公司的现金流模式是否健康。

    健康模式：经营净流入 + 投资净流出 + 筹资净流出（成熟期）
    危险模式：经营净流出 + 投资净流入 + 筹资净流入（持续输血）
    """
    multi_year = ctx.get("multi_year_data")
    if not multi_year or len(multi_year) < 3:
        return None

    patterns = []
    for period in multi_year[:5]:
        ocf = _v(period, ["op_cashflow", "n_cashflow_act"]) or 0
        icf = _v(period, ["inv_cf", "n_cashflow_inv_act"]) or 0
        fcf = _v(period, ["fin_cf", "n_cash_flows_fnc_act", "n_cash_finance_act"]) or 0
        pattern = ("+" if ocf >= 0 else "-") + ("+" if icf >= 0 else "-") + ("+" if fcf >= 0 else "-")
        patterns.append(pattern)

    # 危险模式：经营-投资+筹资+ (持续依赖外部)
    # 或 经营-投资+筹资- (最危险)
    danger_patterns = ["-++", "-+-"]
    danger_count = sum(1 for p in patterns if p in danger_patterns)

    if danger_count >= 3:
        return Signal(
            id="cf_structure",
            name="现金流结构持续异常",
            category=SignalCategory.CASHFLOW,
            level=SignalLevel.HIGH,
            value=f"近{len(patterns)}年现金流模式: {patterns}",
            threshold="经营现金流为正（成熟期模式）",
            conclusion=f"近{len(patterns)}年中{danger_count}年为危险模式（经营失血+外部输血），资金链风险高",
        )
    elif danger_count >= 2:
        return Signal(
            id="cf_structure",
            name="现金流结构异常",
            category=SignalCategory.CASHFLOW,
            level=SignalLevel.MEDIUM,
            value=f"近{len(patterns)}年现金流模式: {patterns}",
            threshold="经营现金流为正（成熟期模式）",
            conclusion="现金流结构不稳定，部分年份依赖外部融资",
        )
    return None
