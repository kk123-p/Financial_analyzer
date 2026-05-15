"""
三维分析师简报生成器 - 为价值/成长/风控三个角色各生成专属数据包
"""
from ..deepseek.prompts import ANALYST_ROLES
from ..logging_config import get_logger

logger = get_logger(__name__)


class BriefingGenerator:
    """三维分析师简报生成器"""

    @staticmethod
    def generate_all(report: dict) -> dict:
        """
        为三个分析师生成专属简报

        Args:
            report: ReportBuilder.build() 输出的结构化报告

        Returns:
            {"value": str, "growth": str, "risk": str}
        """
        return {
            "value": BriefingGenerator.generate_value_briefing(report),
            "growth": BriefingGenerator.generate_growth_briefing(report),
            "risk": BriefingGenerator.generate_risk_briefing(report),
        }

    @staticmethod
    def generate_value_briefing(report: dict) -> str:
        """格雷厄姆式价值分析师专属简报"""
        lines = []
        role = ANALYST_ROLES["value"]
        lines.append(f"{'='*40}")
        lines.append(f"  {role['emoji']} {role['name']} 专属数据简报")
        lines.append(f"{'='*40}")
        lines.append(f"核心问题: {role['core_question']}")
        lines.append("")

        snap = report.get("company_snapshot", {})
        val = report.get("valuation", {})
        health = report.get("financial_health", {})
        raw = health.get("_raw", {})
        dupont = report.get("dupont_analysis", {})
        risk = report.get("risk_models", {})

        # 估值数据
        lines.append("--- 估值与安全边际 ---")
        lines.append(f"  当前价格: {snap.get('price', 'N/A')}")
        lines.append(f"  PE: {snap.get('pe', 'N/A')} | PB: {snap.get('pb', 'N/A')}")
        if val.get("pe_percentile"):
            pct = val["pe_percentile"]
            lines.append(f"  PE 5年历史分位: {pct.get('percentile', 'N/A'):.1f}% (均值 {pct.get('avg', 'N/A'):.1f})")
        if val.get("pb_percentile"):
            pct = val["pb_percentile"]
            lines.append(f"  PB 5年历史分位: {pct.get('percentile', 'N/A'):.1f}%")
        lines.append("")

        # 资产质量
        lines.append("--- 资产质量 ---")
        equity = raw.get("equity")
        ta = raw.get("total_assets")
        goodwill = raw.get("goodwill")
        ar = raw.get("accounts_receivable")
        inv = raw.get("inventory")
        cash = raw.get("cash")
        tl = raw.get("total_liab")

        if equity:
            lines.append(f"  净资产: {equity/1e8:.2f}亿")
        if goodwill and equity and equity > 0:
            lines.append(f"  商誉/净资产: {goodwill/equity*100:.1f}%")
        if ar and raw.get("revenue"):
            lines.append(f"  应收/营收: {ar/raw['revenue']*100:.1f}%")
        if inv and raw.get("op_cost"):
            lines.append(f"  存货/营业成本: {inv/raw['op_cost']*100:.1f}%")
        if cash and ta:
            lines.append(f"  货币资金/总资产: {cash/ta*100:.1f}%")
        lines.append("")

        # 清算价值估算
        lines.append("--- 清算价值估算 ---")
        if equity and goodwill:
            tangible_equity = equity - goodwill
            lines.append(f"  有形净资产 = 净资产 - 商誉 = {tangible_equity/1e8:.2f}亿")
            if snap.get("market_cap_yi"):
                lines.append(f"  当前市值: {snap['market_cap_yi']}亿")
                if tangible_equity > 0:
                    pb_tangible = snap["market_cap_yi"] / (tangible_equity / 1e8)
                    lines.append(f"  有形市净率: {pb_tangible:.2f}")
        lines.append("")

        # 股息率
        profitability = health.get("盈利能力", {})
        roe = profitability.get("ROE")
        if roe:
            lines.append(f"  ROE: {roe:.2f}%")

        # 财务稳健性
        solvency = health.get("偿债能力", {})
        dar = solvency.get("资产负债率")
        if dar:
            lines.append(f"  资产负债率: {dar:.2f}%")

        # Z-score
        if risk.get("zscore"):
            z = risk["zscore"]
            lines.append(f"  Z-score: {z.get('z_score', 'N/A'):.2f} [{z.get('zone_cn', '')}]")

        return "\n".join(lines)

    @staticmethod
    def generate_growth_briefing(report: dict) -> str:
        """费雪式成长分析师专属简报"""
        lines = []
        role = ANALYST_ROLES["growth"]
        lines.append(f"{'='*40}")
        lines.append(f"  {role['emoji']} {role['name']} 专属数据简报")
        lines.append(f"{'='*40}")
        lines.append(f"核心问题: {role['core_question']}")
        lines.append("")

        health = report.get("financial_health", {})
        raw = health.get("_raw", {})
        raw_prev = health.get("_raw_prev", {})
        dupont = report.get("dupont_analysis", {})

        # 增长数据
        lines.append("--- 增长动能 ---")
        growth = health.get("发展能力", {})
        for k, v in growth.items():
            if v is not None:
                lines.append(f"  {k}: {v:.2f}%")
        lines.append("")

        # 营收/利润 CAGR
        rev_cur = raw.get("revenue")
        np_cur = raw.get("net_profit")
        rev_prev = raw_prev.get("revenue")
        np_prev = raw_prev.get("net_profit")

        if rev_cur and rev_prev and rev_prev > 0:
            rev_growth = (rev_cur - rev_prev) / abs(rev_prev) * 100
            lines.append(f"  营收增速: {rev_growth:.1f}%")
        if np_cur and np_prev and np_prev > 0:
            np_growth = (np_cur - np_prev) / abs(np_prev) * 100
            lines.append(f"  净利润增速: {np_growth:.1f}%")
        lines.append("")

        # 盈利能力
        lines.append("--- 盈利能力 ---")
        profitability = health.get("盈利能力", {})
        for k, v in profitability.items():
            if v is not None:
                unit = "%" if "率" in k or "RO" in k else ""
                lines.append(f"  {k}: {v:.2f}{unit}")
        lines.append("")

        # 运营效率趋势
        lines.append("--- 运营效率 ---")
        efficiency = health.get("营运能力", {})
        for k, v in efficiency.items():
            if v is not None:
                lines.append(f"  {k}: {v:.2f}")
        lines.append("")

        # ROE 杜邦分解（判断增长质量）
        if dupont.get("three_factor"):
            lines.append("--- ROE 驱动因素 ---")
            for dp in dupont["three_factor"][:3]:
                ed = dp.get("end_date", "N/A")
                roe = dp.get("roe")
                nm = dp.get("net_margin")
                at = dp.get("asset_turnover")
                em = dp.get("equity_multiplier")
                if roe:
                    lines.append(f"  {ed}: ROE={roe:.2f}% = 净利率{nm:.2f}% x 周转{at:.3f} x 杠杆{em:.2f}")
            lines.append("")

        # 现金流质量
        cf = report.get("cashflow_analysis", {})
        if cf.get("quadrant"):
            lines.append("--- 现金流象限 ---")
            for q in cf["quadrant"][:2]:
                lines.append(f"  {q.get('end_date', 'N/A')}: {q.get('quadrant_type', 'N/A')}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_risk_briefing(report: dict) -> str:
        """塔勒布式风控师专属简报"""
        lines = []
        role = ANALYST_ROLES["risk"]
        lines.append(f"{'='*40}")
        lines.append(f"  {role['emoji']} {role['name']} 专属数据简报")
        lines.append(f"{'='*40}")
        lines.append(f"核心问题: {role['core_question']}")
        lines.append("")

        health = report.get("financial_health", {})
        raw = health.get("_raw", {})
        risk = report.get("risk_models", {})
        signals = report.get("anomaly_signals", [])
        dupont = report.get("dupont_analysis", {})

        # Z-score
        lines.append("--- 破产风险模型 ---")
        if risk.get("zscore"):
            z = risk["zscore"]
            lines.append(f"  Z-score: {z.get('z_score', 'N/A'):.2f}")
            lines.append(f"  风险区域: {z.get('zone_cn', '未知')}")
            if z.get("components"):
                for k, v in z["components"].items():
                    lines.append(f"    {k}: {v:.4f}")
        lines.append("")

        # F-score
        if risk.get("fscore"):
            f = risk["fscore"]
            lines.append(f"  F-score: {f.get('score', 'N/A')}/9")
            lines.append(f"  诊断: {f.get('diagnosis', '')}")
            if f.get("details"):
                for d in f["details"][:5]:
                    lines.append(f"    {d}")
        lines.append("")

        # M-score
        if risk.get("mscore"):
            m = risk["mscore"]
            lines.append(f"  M-score: {m.get('m_score', 'N/A'):.2f}")
            manip = "是 ⚠️" if m.get("manipulator") else "否"
            lines.append(f"  盈余操纵嫌疑: {manip}")
        lines.append("")

        # 偿债能力
        lines.append("--- 偿债压力 ---")
        solvency = health.get("偿债能力", {})
        for k, v in solvency.items():
            if v is not None:
                unit = "%" if "率" in k else ""
                lines.append(f"  {k}: {v:.2f}{unit}")
        lines.append("")

        # 杠杆风险
        if dupont.get("improved"):
            imp = dupont["improved"][0]
            rnoa = imp.get("rnoa")
            nbc = imp.get("nbc")
            flev = imp.get("flev")
            spread = imp.get("spread")
            if rnoa and nbc:
                lines.append(f"--- 杠杆风险 (改良杜邦) ---")
                lines.append(f"  RNOA: {rnoa:.2f}%")
                lines.append(f"  NBC: {nbc:.2f}%")
                lines.append(f"  经营差异率: {spread or 0:+.2f}%")
                lines.append(f"  FLEV: {flev or 0:.3f}")
                if spread and spread < 0:
                    lines.append(f"  ⚠️ 经营差异率为负，杠杆正在侵蚀股东回报！")
                lines.append("")

        # 异常信号全量清单
        if signals:
            lines.append("--- 异常信号全量清单 ---")
            for sig in signals:
                level_icon = {"high": "🔴", "medium": "🟡"}.get(sig.get("level"), "⚪")
                lines.append(f"  {level_icon} {sig['name']}: {sig['value']}")
            lines.append("")

        return "\n".join(lines)
