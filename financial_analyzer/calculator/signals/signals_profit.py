"""
利润端审计信号
=====================
包含原有3个信号 + 新增1个信号，共4个利润端检测。
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
# 1. 利润-现金流长期背离
# ============================================================================
@SignalRegistry.register("profit_cf_divergence", SignalCategory.PROFIT,
                         "利润-现金流背离", "连续多年盈利但经营现金流远低于净利润")
def check_profit_cf_divergence(current, previous, ctx):
    """
    参考文档：公司持续盈利，但经营性现金流净额连续多年远低于净利润。
    利润是"应计"出来的，没有真金白银流入。
    """
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)

    # 从context获取多年数据（由上层预处理）
    multi_year = ctx.get("multi_year_data")
    if multi_year and len(multi_year) >= 3:
        profits = []
        ocfs = []
        for period in multi_year[:5]:
            np_ = _v(period, ["net_profit", "n_income", "n_income_attr_p"])
            ocf = _v(period, ["op_cashflow", "n_cashflow_act"])
            if np_ is not None:
                profits.append(np_)
            if ocf is not None:
                ocfs.append(ocf)

        if len(profits) >= 3 and len(ocfs) >= 3:
            # 连续盈利且经营CF均远低于净利润
            if all(p > 0 for p in profits[:3]) and all(o < p * th.profit_cf_ratio for p, o in zip(profits[:3], ocfs[:3])):
                avg_ratio = sum(o / p for p, o in zip(profits[:3], ocfs[:3])) / 3
                return Signal(
                    id="profit_cf_divergence",
                    name="利润-现金流长期背离",
                    category=SignalCategory.PROFIT,
                    level=SignalLevel.HIGH,
                    value=f"近3年经营CF/净利润均值 = {avg_ratio:.2f}",
                    threshold=f"经营CF/净利润 > {th.profit_cf_ratio}",
                    conclusion="连续多年盈利但缺乏现金流支撑，利润可能是应计出来的，没有真金白银流入",
                    raw_value=avg_ratio,
                    threshold_value=th.profit_cf_ratio,
                )

    # 单期简化检测
    np_cur = _v(current, ["net_profit", "n_income", "n_income_attr_p"])
    ocf_cur = _v(current, ["op_cashflow", "n_cashflow_act"])
    if np_cur and np_cur > 0 and ocf_cur is not None:
        ratio = ocf_cur / np_cur
        if ratio < th.profit_cf_ratio:
            return Signal(
                id="profit_cf_divergence",
                name="利润-现金流背离",
                category=SignalCategory.PROFIT,
                level=SignalLevel.MEDIUM,
                value=f"经营现金流/净利润 = {ratio:.2f}",
                threshold=f"经营CF/净利润 > {th.profit_cf_ratio}",
                conclusion="盈利但经营现金流不足，利润质量存疑",
                raw_value=ratio,
                threshold_value=th.profit_cf_ratio,
            )
    return None


# ============================================================================
# 2. 异常毛利率
# ============================================================================
@SignalRegistry.register("profit_gross_margin", SignalCategory.PROFIT,
                         "异常高毛利率", "毛利率远超行业常规")
def check_gross_margin(current, previous, ctx):
    """
    参考文档：毛利率远超同行，或变动趋势与行业规律相反。
    虚增收入或压低成本，导致毛利率虚高。
    """
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    revenue = _v(current, ["revenue", "total_revenue"])
    cost = _v(current, ["oper_cost", "operating_cost"])

    if not (revenue and revenue > 0 and cost is not None):
        return None

    gross_margin = (revenue - cost) / revenue
    if gross_margin > th.gross_margin_high:
        level = SignalLevel.HIGH if gross_margin > 0.8 else SignalLevel.MEDIUM
        return Signal(
            id="profit_gross_margin",
            name="异常高毛利率",
            category=SignalCategory.PROFIT,
            level=level,
            value=f"毛利率 = {gross_margin:.1%}",
            threshold=f"毛利率 > {th.gross_margin_high:.0%}",
            conclusion="毛利率异常偏高，需与同行业对比，可能存在虚增收入或压低成本",
            raw_value=gross_margin,
            threshold_value=th.gross_margin_high,
        )
    return None


# ============================================================================
# 3. 非经常性损益依赖
# ============================================================================
@SignalRegistry.register("profit_non_recurring", SignalCategory.PROFIT,
                         "非经常性损益依赖", "扣非净利润与净利润差异巨大")
def check_non_recurring(current, previous, ctx):
    """
    参考文档：扣非后净利润持续亏损，靠变卖资产、政府补贴等方式实现账面盈利。
    """
    th: AuditThresholds = ctx.get("thresholds", DEFAULT_THRESHOLDS)
    net_profit = _v(current, ["net_profit", "n_income", "n_income_attr_p"])
    total_profit = _v(current, ["total_profit"])
    operate_profit = _v(current, ["operate_profit", "operate_profit_deducted"])

    if not (net_profit and net_profit > 0 and total_profit and operate_profit is not None):
        return None

    non_recurring = total_profit - operate_profit
    ratio = abs(non_recurring) / net_profit

    if ratio > th.non_recurring_profit_ratio:
        level = SignalLevel.HIGH if ratio > 1.0 else SignalLevel.MEDIUM
        return Signal(
            id="profit_non_recurring",
            name="非经常性损益依赖",
            category=SignalCategory.PROFIT,
            level=level,
            value=f"非经常性损益/净利润 = {ratio:.1%}（非经常性={non_recurring:.0f}，净利润={net_profit:.0f}）",
            threshold=f"非经常性损益/净利润 > {th.non_recurring_profit_ratio:.0%}",
            conclusion="主业盈利能力差，依赖一次性收益维持账面盈利",
            raw_value=ratio,
            threshold_value=th.non_recurring_profit_ratio,
        )
    return None


# ============================================================================
# 4. [新增] 会计估计变更检测
# ============================================================================
@SignalRegistry.register("profit_accounting_change", SignalCategory.PROFIT,
                         "会计估计异常变更", "坏账计提/折旧年限等发生突变")
def check_accounting_change(current, previous, ctx):
    """
    参考文档：突然大幅变更坏账准备计提比例、固定资产折旧年限等。
    通过调整会计估计来"调节"利润。

    检测方式：对比本期与上期的坏账准备/应收比率变化，
    或从context获取会计变更标记。
    """
    # 从context获取会计变更信息（如有上层预处理）
    acct_changes = ctx.get("accounting_changes")
    if acct_changes and acct_changes.get("has_significant_change"):
        changes_desc = acct_changes.get("description", "检测到重大会计估计变更")
        return Signal(
            id="profit_accounting_change",
            name="会计估计异常变更",
            category=SignalCategory.PROFIT,
            level=SignalLevel.MEDIUM,
            value=changes_desc,
            threshold="无重大变更",
            conclusion="通过调整会计估计调节利润，需关注变更的合理性",
        )

    # 简化检测：坏账准备/应收比率变化
    if not previous:
        return None
    bad_debt = _v(current, ["bad_debt_provision", "provision_for_bad_debts"])
    ar = _v(current, ["accounts_receivable", "accounts_receiv"])
    bad_debt_prev = _v(previous, ["bad_debt_provision", "provision_for_bad_debts"])
    ar_prev = _v(previous, ["accounts_receivable", "accounts_receiv"])

    if not (bad_debt is not None and ar and ar > 0 and bad_debt_prev is not None and ar_prev and ar_prev > 0):
        return None

    cur_ratio = bad_debt / ar
    prev_ratio = bad_debt_prev / ar_prev
    change = cur_ratio - prev_ratio

    # 坏账计提比例大幅下降（超过5个百分点）可能是激进调整
    if change < -0.05:
        return Signal(
            id="profit_accounting_change",
            name="坏账计提比例大幅下调",
            category=SignalCategory.PROFIT,
            level=SignalLevel.MEDIUM,
            value=f"坏账/应收比率: {prev_ratio:.1%} → {cur_ratio:.1%}（下降 {abs(change):.1%}）",
            threshold="坏账计提比例无大幅变动",
            conclusion="坏账计提比例大幅下调，可能通过调整会计估计美化利润",
            raw_value=change,
            threshold_value=-0.05,
        )
    return None
