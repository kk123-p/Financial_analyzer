"""
矛盾信号检测器 - 4个核心矛盾信号的自动触发
将第一阶段指标间的隐性矛盾，固化为带标签的诊断任务
"""
from ..logging_config import get_logger

logger = get_logger(__name__)


class SignalDetector:
    """矛盾信号检测器"""

    # 矛盾信号定义
    SIGNALS = [
        {
            "id": "profit_quality",
            "name": "盈利质量预警",
            "description": "利润增长缺乏现金流支撑",
            "trigger_desc": "(归母净利润增速 > 20%) & (经营现金流/净利润 < 0.5)",
            "task": "请解释利润增长缺乏现金支撑的具体原因，识别主要拖累科目（应收账款增加？存货积压？一次性收益？）。",
        },
        {
            "id": "growth_overdraft",
            "name": "增长透支预警",
            "description": "高增长依赖放宽信用政策",
            "trigger_desc": "(营收增速 > 30%) & (应收账款增速/营收增速 > 1.5)",
            "task": "分析高增长是否依赖放宽信用政策。测算如果应收账款坏账计提增加1个百分点，对净利润的冲击有多大。",
        },
        {
            "id": "paper_wealth",
            "name": "纸面富贵预警",
            "description": "高ROE完全由杠杆驱动",
            "trigger_desc": "ROE > 20% & 杠杆贡献率 > 60%（改良杜邦）",
            "task": "拆解ROE中杠杆带来的收益占比。估算如果利率上升100个基点，利息覆盖倍数会恶化到什么程度。",
        },
        {
            "id": "financial_dress",
            "name": "财务粉饰预警",
            "description": "同时存在盈余操纵可能和破产风险",
            "trigger_desc": "M-score > -1.78 且 Z-score < 1.8",
            "task": "该公司同时存在盈余操纵可能和破产风险。请交叉验证收入确认政策与现金流的背离，识别最可能的粉饰手法。",
        },
    ]

    @staticmethod
    def detect(report: dict) -> list:
        """
        基于体检报告检测矛盾信号

        Args:
            report: ReportBuilder.build() 输出的结构化报告

        Returns:
            list of triggered signals: [{
                "id", "name", "description", "trigger_desc",
                "task", "triggered": True,
                "trigger_data": str  # 触发时的具体数据
            }]
        """
        triggered = []

        # 1. 盈利质量预警
        signal = SignalDetector._check_profit_quality(report)
        if signal:
            triggered.append(signal)

        # 2. 增长透支预警
        signal = SignalDetector._check_growth_overdraft(report)
        if signal:
            triggered.append(signal)

        # 3. 纸面富贵预警
        signal = SignalDetector._check_paper_wealth(report)
        if signal:
            triggered.append(signal)

        # 4. 财务粉饰预警
        signal = SignalDetector._check_financial_dress(report)
        if signal:
            triggered.append(signal)

        return triggered

    @staticmethod
    def _check_profit_quality(report: dict) -> dict | None:
        """盈利质量预警: (净利润增速 > 20%) & (经营CF/净利润 < 0.5)"""
        raw = report.get("financial_health", {}).get("_raw", {})
        raw_prev = report.get("financial_health", {}).get("_raw_prev", {})

        np_cur = raw.get("net_profit")
        np_prev = raw_prev.get("net_profit")
        op_cf = raw.get("op_cashflow")

        if np_cur is None or np_prev is None or op_cf is None:
            return None

        # 净利润增速
        if np_prev == 0:
            return None
        np_growth = (np_cur - np_prev) / abs(np_prev) * 100

        # 经营现金流/净利润
        if np_cur == 0:
            return None
        cf_ratio = op_cf / np_cur

        if np_growth > 20 and cf_ratio < 0.5:
            sig = dict(SignalDetector.SIGNALS[0])
            sig["triggered"] = True
            sig["trigger_data"] = (
                f"净利润增速 = {np_growth:.1f}%，"
                f"经营现金流/净利润 = {cf_ratio:.2f}（阈值: 增速>20% 且 CF/NP < 0.5）"
            )
            return sig

        return None

    @staticmethod
    def _check_growth_overdraft(report: dict) -> dict | None:
        """增长透支预警: (营收增速 > 30%) & (应收增速/营收增速 > 1.5)"""
        raw = report.get("financial_health", {}).get("_raw", {})
        raw_prev = report.get("financial_health", {}).get("_raw_prev", {})

        rev_cur = raw.get("revenue")
        rev_prev = raw_prev.get("revenue")
        ar_cur = raw.get("accounts_receivable")
        ar_prev = raw_prev.get("accounts_receivable")

        if not all([rev_cur, rev_prev, ar_cur, ar_prev]):
            return None
        if rev_prev == 0 or ar_prev == 0:
            return None

        rev_growth = (rev_cur - rev_prev) / abs(rev_prev) * 100
        ar_growth = (ar_cur - ar_prev) / abs(ar_prev) * 100

        if rev_growth > 0:
            ar_rev_ratio = ar_growth / rev_growth
        else:
            return None

        if rev_growth > 30 and ar_rev_ratio > 1.5:
            sig = dict(SignalDetector.SIGNALS[1])
            sig["triggered"] = True
            sig["trigger_data"] = (
                f"营收增速 = {rev_growth:.1f}%，"
                f"应收增速/营收增速 = {ar_rev_ratio:.2f}（阈值: 营收>30% 且 比值>1.5）"
            )
            return sig

        return None

    @staticmethod
    def _check_paper_wealth(report: dict) -> dict | None:
        """纸面富贵预警: ROE > 20% & 杠杆贡献率 > 60%"""
        dupont = report.get("dupont_analysis", {})
        improved = dupont.get("improved", [])

        if not improved:
            return None

        latest = improved[0]
        roe = latest.get("roe")
        lev_contrib = latest.get("leverage_contribution")

        if roe is None or lev_contrib is None:
            return None

        # 杠杆贡献率占比
        if roe == 0:
            return None
        lev_ratio = abs(lev_contrib) / abs(roe) * 100

        if roe > 20 and lev_ratio > 60:
            sig = dict(SignalDetector.SIGNALS[2])
            sig["triggered"] = True
            sig["trigger_data"] = (
                f"ROE = {roe:.2f}%，"
                f"杠杆贡献率占比 = {lev_ratio:.1f}%（阈值: ROE>20% 且 杠杆占比>60%）"
            )
            return sig

        return None

    @staticmethod
    def _check_financial_dress(report: dict) -> dict | None:
        """财务粉饰预警: M-score > -1.78 且 Z-score < 1.8"""
        risk = report.get("risk_models", {})

        mscore_data = risk.get("mscore", {})
        zscore_data = risk.get("zscore", {})

        m_score = mscore_data.get("m_score")
        z_score = zscore_data.get("z_score")

        if m_score is None or z_score is None:
            return None

        if m_score > -1.78 and z_score < 1.8:
            sig = dict(SignalDetector.SIGNALS[3])
            sig["triggered"] = True
            sig["trigger_data"] = (
                f"M-score = {m_score:.2f}（阈值 > -1.78），"
                f"Z-score = {z_score:.2f}（阈值 < 1.8）"
            )
            return sig

        return None
