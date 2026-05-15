"""
深度投研报告模板 - 情景矩阵、风险摘要、结构化报告格式化
将辩论结果整合为可导出的最终报告
"""
from ..deepseek.prompts import ANALYST_ROLES
from ..logging_config import get_logger

logger = get_logger(__name__)


class ReportTemplate:
    """深度投研报告模板"""

    @staticmethod
    def build_final_report(debate_state, report: dict, signals: list,
                           weights: dict = None) -> str:
        """
        构建最终深度投研报告

        Args:
            debate_state: DebateState 对象
            report: 体检报告 dict
            signals: 矛盾信号列表
            weights: 视角权重 {"value": int, "growth": int, "risk": int}

        Returns:
            完整报告文本（Markdown 格式）
        """
        sections = []

        # 封面
        sections.append(ReportTemplate._build_cover(report))

        # 矛盾信号
        if signals:
            sections.append(ReportTemplate._build_signals_section(signals))

        # 第一轮：独立陈述
        if debate_state.round1_statements:
            sections.append(ReportTemplate._build_round1_section(debate_state.round1_statements))

        # 第二轮：交叉质询
        if debate_state.round2_statements:
            sections.append(ReportTemplate._build_round2_section(debate_state.round2_statements))

        # 第三轮：共识地图
        if debate_state.round3_result:
            sections.append(ReportTemplate._build_consensus_section(
                debate_state.round3_result, weights))

        # 数据附录
        sections.append(ReportTemplate._build_appendix(report))

        # 风险声明
        sections.append(ReportTemplate._build_disclaimer())

        return "\n\n".join(sections)

    @staticmethod
    def build_export_text(debate_state, report: dict, signals: list,
                          weights: dict = None) -> str:
        """构建纯文本导出格式"""
        return ReportTemplate.build_final_report(debate_state, report, signals, weights)

    @staticmethod
    def build_html_report(debate_state, report: dict, signals: list,
                          weights: dict = None) -> str:
        """构建 HTML 导出格式"""
        md_text = ReportTemplate.build_final_report(debate_state, report, signals, weights)

        snap = report.get("company_snapshot", {})
        title = f"{snap.get('name', '')} ({snap.get('stock_code', '')}) 深度投研报告"

        # 简单 Markdown → HTML 转换
        html_body = ReportTemplate._md_to_html(md_text)

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
body {{ font-family: "Microsoft YaHei", sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; background: #0f172a; color: #e2e8f0; line-height: 1.8; }}
h1 {{ color: #f59e0b; border-bottom: 2px solid #334155; padding-bottom: 10px; }}
h2 {{ color: #3b82f6; margin-top: 30px; }}
h3 {{ color: #94a3b8; }}
table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
th, td {{ border: 1px solid #334155; padding: 8px 12px; text-align: left; }}
th {{ background: #1e293b; color: #f59e0b; }}
tr:nth-child(even) {{ background: #1e293b; }}
.signal {{ background: #7f1d1d; border-left: 4px solid #ef4444; padding: 10px; margin: 10px 0; border-radius: 4px; }}
.disclaimer {{ background: #1e293b; border: 1px solid #475569; padding: 15px; border-radius: 8px; font-size: 0.9em; color: #94a3b8; }}
blockquote {{ border-left: 3px solid #3b82f6; padding-left: 15px; color: #94a3b8; }}
code {{ background: #1e293b; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    # ========================================================================
    # 各章节构建
    # ========================================================================

    @staticmethod
    def _build_cover(report: dict) -> str:
        """封面"""
        snap = report.get("company_snapshot", {})
        val = report.get("valuation", {})
        risk = report.get("risk_models", {})

        lines = []
        lines.append("=" * 50)
        lines.append(f"  {snap.get('name', 'N/A')} ({snap.get('stock_code', '')})")
        lines.append(f"  AI 深度投研报告")
        lines.append("=" * 50)
        lines.append("")
        lines.append(f"行业: {snap.get('industry', 'N/A')}")
        if snap.get("price"):
            lines.append(f"当前价格: {snap['price']}")
        if snap.get("pe"):
            lines.append(f"PE: {snap['pe']:.2f}  |  PB: {snap.get('pb', 'N/A')}")
        if snap.get("market_cap_yi"):
            lines.append(f"总市值: {snap['market_cap_yi']}亿元")

        # 关键模型得分
        lines.append("")
        lines.append("--- 关键模型得分 ---")
        if risk.get("zscore"):
            z = risk["zscore"]
            lines.append(f"  Z-score: {z.get('z_score', 'N/A'):.2f} [{z.get('zone_cn', '')}]")
        if risk.get("fscore"):
            f = risk["fscore"]
            lines.append(f"  F-score: {f.get('score', 'N/A')}/9")
        if risk.get("mscore"):
            m = risk["mscore"]
            lines.append(f"  M-score: {m.get('m_score', 'N/A'):.2f}")

        return "\n".join(lines)

    @staticmethod
    def _build_signals_section(signals: list) -> str:
        """矛盾信号章节"""
        lines = []
        lines.append("## ⚠️ 矛盾信号预警")
        lines.append("")
        for sig in signals:
            level_icon = {"high": "🔴 高风险", "medium": "🟡 中风险"}.get(sig.get("level"), "⚪")
            lines.append(f"### {level_icon}: {sig['name']}")
            lines.append(f"- 触发条件: {sig.get('trigger_desc', '')}")
            lines.append(f"- 触发数据: {sig.get('trigger_data', '')}")
            lines.append(f"- 诊断任务: {sig.get('task', '')}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _build_round1_section(statements: dict) -> str:
        """第一轮独立陈述"""
        lines = []
        lines.append("## 第一轮：独立视角陈述")
        lines.append("")
        for aid in ["value", "growth", "risk"]:
            stmt = statements.get(aid, "")
            role = ANALYST_ROLES.get(aid, {})
            lines.append(f"### {role.get('emoji', '')} {role.get('name', aid)}")
            lines.append("")
            lines.append(stmt)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _build_round2_section(statements: dict) -> str:
        """第二轮交叉质询"""
        lines = []
        lines.append("## 第二轮：交叉质询")
        lines.append("")
        for aid in ["value", "growth", "risk"]:
            stmt = statements.get(aid, "")
            role = ANALYST_ROLES.get(aid, {})
            lines.append(f"### {role.get('emoji', '')} {role.get('name', aid)} 的质询")
            lines.append("")
            lines.append(stmt)
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _build_consensus_section(consensus: str, weights: dict = None) -> str:
        """第三轮共识地图"""
        lines = []
        lines.append("## 第三轮：共识地图")
        if weights:
            lines.append(f"")
            lines.append(f"视角权重: 价值 {weights.get('value', 33)}% | "
                        f"成长 {weights.get('growth', 33)}% | "
                        f"风控 {weights.get('risk', 33)}%")
        lines.append("")
        lines.append(consensus)
        return "\n".join(lines)

    @staticmethod
    def _build_appendix(report: dict) -> str:
        """数据附录"""
        lines = []
        lines.append("## 附录：核心数据")

        health = report.get("financial_health", {})
        if not health.get("error"):
            for cat in ["偿债能力", "营运能力", "盈利能力", "发展能力", "市场价值"]:
                cat_data = health.get(cat, {})
                if cat_data:
                    items = [f"{k}={v}" for k, v in cat_data.items() if v is not None]
                    if items:
                        lines.append(f"  {cat}: {' | '.join(items[:6])}")

        return "\n".join(lines)

    @staticmethod
    def _build_disclaimer() -> str:
        """风险声明"""
        return """## ⚠️ 风险提示

本报告由 AI 深度投研系统自动生成，基于公开财务数据和量化模型分析。

**重要声明：**
1. 本报告仅供参考，不构成任何投资建议
2. AI 分析可能存在偏差，请结合自身判断
3. 过往业绩不代表未来表现
4. 投资有风险，入市需谨慎

---
报告生成时间: {timestamp}
""".format(timestamp=__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @staticmethod
    def _md_to_html(text: str) -> str:
        """简单 Markdown → HTML 转换"""
        import re

        lines = text.split("\n")
        html_lines = []
        in_table = False

        for line in lines:
            stripped = line.strip()

            # 标题
            if stripped.startswith("### "):
                html_lines.append(f"<h3>{stripped[4:]}</h3>")
            elif stripped.startswith("## "):
                html_lines.append(f"<h2>{stripped[3:]}</h2>")
            elif stripped.startswith("# "):
                html_lines.append(f"<h1>{stripped[2:]}</h1>")
            # 分隔线
            elif stripped == "---" or (stripped.startswith("=") and len(stripped) > 5):
                html_lines.append("<hr>")
            # 表格
            elif "|" in stripped and stripped.startswith("|"):
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                if all(set(c) <= set("- :") for c in cells):
                    continue  # 跳过表格分隔行
                if not in_table:
                    html_lines.append("<table>")
                    tag = "th"
                    in_table = True
                else:
                    tag = "td"
                row = "".join(f"<{tag}>{c}</{tag}>" for c in cells)
                html_lines.append(f"<tr>{row}</tr>")
            else:
                if in_table:
                    html_lines.append("</table>")
                    in_table = False
                # 粗体
                stripped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
                # 列表
                if stripped.startswith("- "):
                    html_lines.append(f"<li>{stripped[2:]}</li>")
                elif stripped:
                    html_lines.append(f"<p>{stripped}</p>")

        if in_table:
            html_lines.append("</table>")

        return "\n".join(html_lines)
