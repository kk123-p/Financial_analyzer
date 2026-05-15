"""
治理与披露审计信号（全新）
=============================
参考文档维度二、四：公司治理信号 + 监管与信息披露信号。
部分信号需要外部数据（公告、新闻等），通过context传入。
"""
from ..audit_engine import (
    Signal, SignalLevel, SignalCategory, SignalRegistry,
    AuditThresholds, DEFAULT_THRESHOLDS,
)
from ...logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# 1. [新增] 审计意见异常
# ============================================================================
@SignalRegistry.register("gov_audit_opinion", SignalCategory.GOVERNANCE,
                         "审计意见异常", "非标准审计意见")
def check_audit_opinion(current, previous, ctx):
    """
    参考文档：年报被出具带强调事项段、保留意见、无法表示意见的审计报告。
    表明审计师对财务数据的真实性或公司的持续经营能力存在重大疑疑。

    数据来源：context["audit_opinion"] 由上层从公告数据获取
    """
    opinion = ctx.get("audit_opinion")
    if not opinion:
        return None

    opinion_type = opinion.get("type", "")  # standard / emphasis / qualified / disclaimer / adverse
    opinion_text = opinion.get("text", "")

    if opinion_type in ("disclaimer", "adverse"):
        return Signal(
            id="gov_audit_opinion",
            name="严重审计意见异常",
            category=SignalCategory.GOVERNANCE,
            level=SignalLevel.HIGH,
            value=f"审计意见: {opinion_text}",
            threshold="标准无保留意见",
            conclusion="被出具否定意见或无法表示意见，财务数据可信度严重存疑",
        )
    elif opinion_type in ("qualified", "emphasis"):
        return Signal(
            id="gov_audit_opinion",
            name="非标准审计意见",
            category=SignalCategory.GOVERNANCE,
            level=SignalLevel.MEDIUM,
            value=f"审计意见: {opinion_text}",
            threshold="标准无保留意见",
            conclusion="被出具保留意见或带强调事项段，需关注具体强调事项",
        )
    return None


# ============================================================================
# 2. [新增] 关联交易异常
# ============================================================================
@SignalRegistry.register("gov_related_party", SignalCategory.GOVERNANCE,
                         "关联交易异常", "关联交易规模或占比异常")
def check_related_party(current, previous, ctx):
    """
    参考文档：主要客户或供应商与公司高管、实际控制人存在隐秘的关联关系。
    极有可能是"自买自卖"的虚构交易或利益输送。

    数据来源：context["related_party"] 由上层预处理
    """
    rp = ctx.get("related_party")
    if not rp:
        return None

    # 关联交易金额/营收占比
    revenue = None
    for k in ["revenue", "total_revenue"]:
        if k in current and current[k] is not None:
            try:
                revenue = float(current[k])
                break
            except (ValueError, TypeError):
                pass

    rp_amount = rp.get("total_amount", 0)
    rp_revenue = rp.get("revenue_amount", 0)

    if revenue and revenue > 0 and rp_amount > 0:
        rp_ratio = rp_amount / revenue
        if rp_ratio > 0.3:
            level = SignalLevel.HIGH if rp_ratio > 0.5 else SignalLevel.MEDIUM
            return Signal(
                id="gov_related_party",
                name="关联交易规模异常",
                category=SignalCategory.GOVERNANCE,
                level=level,
                value=f"关联交易/营收 = {rp_ratio:.1%}（关联交易={rp_amount:.0f}，营收={revenue:.0f}）",
                threshold="关联交易/营收 < 30%",
                conclusion="关联交易占比过高，可能存在利益输送或虚构交易",
                raw_value=rp_ratio,
                threshold_value=0.3,
            )

    # 关联交易毛利率异常
    if rp.get("gross_margin") and revenue:
        rp_margin = rp["gross_margin"]
        if rp_margin > 0.6:
            return Signal(
                id="gov_related_party",
                name="关联交易毛利率异常",
                category=SignalCategory.GOVERNANCE,
                level=SignalLevel.MEDIUM,
                value=f"关联交易毛利率 = {rp_margin:.1%}",
                threshold="关联交易毛利率 < 60%",
                conclusion="关联交易毛利率异常偏高，可能存在利益输送",
                raw_value=rp_margin,
                threshold_value=0.6,
            )
    return None


# ============================================================================
# 3. [新增] 大股东资金占用
# ============================================================================
@SignalRegistry.register("gov_fund_occupation", SignalCategory.GOVERNANCE,
                         "大股东资金占用", "大股东或实控人非经营性占用资金")
def check_fund_occupation(current, previous, ctx):
    """
    参考文档：年度报告显示，大股东或实际控制人非经营性占用上市公司资金。
    表明公司治理结构失效，上市公司成为大股东的"提款机"。

    数据来源：context["fund_occupation"]
    """
    fo = ctx.get("fund_occupation")
    if not fo:
        return None

    amount = fo.get("amount", 0)
    if amount and amount > 0:
        return Signal(
            id="gov_fund_occupation",
            name="大股东资金占用",
            category=SignalCategory.GOVERNANCE,
            level=SignalLevel.HIGH,
            value=f"占用金额 = {amount:.0f}",
            threshold="无资金占用",
            conclusion="大股东或实控人非经营性占用上市公司资金，治理结构失效",
        )
    return None


# ============================================================================
# 4. [新增] 关键高管变动
# ============================================================================
@SignalRegistry.register("gov_executive_change", SignalCategory.GOVERNANCE,
                         "关键高管频繁变动", "财务总监/董秘/独董等密集离职")
def check_executive_change(current, previous, ctx):
    """
    参考文档：财务总监、董秘、独立董事等关键岗位人员在短时间内密集离职。
    可能是内部人士为避免自身风险而"用脚投票"。

    数据来源：context["executive_changes"]
    """
    ec = ctx.get("executive_changes")
    if not ec:
        return None

    departures = ec.get("departures", [])
    if len(departures) >= 3:
        names = ", ".join(d.get("name", "未知") for d in departures[:5])
        return Signal(
            id="gov_executive_change",
            name="关键高管频繁变动",
            category=SignalCategory.GOVERNANCE,
            level=SignalLevel.HIGH,
            value=f"近期离职高管: {names}（共{len(departures)}人）",
            threshold="关键岗位无密集变动",
            conclusion="关键岗位人员密集离职，可能反映公司财务或内控存在重大问题",
        )
    elif len(departures) >= 2:
        return Signal(
            id="gov_executive_change",
            name="高管变动频繁",
            category=SignalCategory.GOVERNANCE,
            level=SignalLevel.MEDIUM,
            value=f"近期离职高管{len(departures)}人",
            threshold="关键岗位无密集变动",
            conclusion="高管变动较频繁，需关注公司内部治理状况",
        )
    return None


# ============================================================================
# 5. [新增] 频繁变更审计机构
# ============================================================================
@SignalRegistry.register("gov_auditor_change", SignalCategory.GOVERNANCE,
                         "频繁变更审计机构", "年报审计前更换会计师事务所")
def check_auditor_change(current, previous, ctx):
    """
    参考文档：尤其在年报审计前，上市公司"炒掉"出具过非标意见或提出质疑的会计师事务所。
    大概率是为"购买"满意的审计意见。

    数据来源：context["auditor_change"]
    """
    ac = ctx.get("auditor_change")
    if not ac:
        return None

    if ac.get("changed_before_annual"):
        return Signal(
            id="gov_auditor_change",
            name="审计前更换审计机构",
            category=SignalCategory.GOVERNANCE,
            level=SignalLevel.HIGH,
            value=f"变更详情: {ac.get('description', '年报审计前更换会计师事务所')}",
            threshold="审计机构稳定",
            conclusion="在年报审计前更换审计机构，可能是为购买满意的审计意见",
        )
    elif ac.get("frequent_changes"):
        return Signal(
            id="gov_auditor_change",
            name="频繁变更审计机构",
            category=SignalCategory.GOVERNANCE,
            level=SignalLevel.MEDIUM,
            value=f"近3年变更{ac.get('change_count', '?')}次",
            threshold="审计机构稳定",
            conclusion="频繁变更审计机构，是掩盖舞弊行为的典型信号",
        )
    return None
