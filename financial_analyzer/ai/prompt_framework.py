"""
可组合提示词构建器

将专业财务分析框架编码为可复用的提示词组件，按分析模式和用户需求动态组装。
"""

from __future__ import annotations
import json
from typing import Any


# ============================================================================
# 框架模板 — 专业方法论编码
# ============================================================================

HARVARD_FRAMEWORK = """
## 分析框架：哈佛分析框架

请遵循以下四步分析结构：

### 1. 战略分析（前提和导向）
- 识别公司所处的行业生命周期阶段和竞争地位
- 评估公司的竞争战略（成本领先/差异化/集中化）及其与财务数据的匹配性
- 判断资产结构（经营性 vs 投资性）与战略表述的一致性

### 2. 会计分析（基础）
- 评估关键会计政策和会计估计的合理性
- 识别可能存在的会计灵活性和盈余管理迹象
- 关注收入确认政策、存货计价方法、折旧政策等关键选择

### 3. 财务分析（核心）
- 盈利质量：核心营业利润占比、非经常性损益影响、利润含金量
- 资产质量：资产结构与战略的匹配度、减值准备合理性
- 现金流质量：经营造血能力、投融资合理性
- 资本结构质量：杠杆水平、偿债能力

### 4. 前景分析（目的）
- 基于前三步分析的结论，对公司未来发展趋势做出判断
- 指出关键价值驱动因素和主要风险点
"""

CROSSCHECK_FRAMEWORK = """
## 三表联动验证

请对以下勾稽关系进行强制交叉验证，任何不一致处必须明确指出：

### 验证链条1：经营性资产 → 营业利润 → 经营现金流
- 经营性资产规模是否与营业利润水平匹配？（经营性资产报酬率）
- 营业利润是否充分转化为经营现金流？（经营现金流/营业利润比率）
- 若该比率 < 0.7，说明利润可能存在应计项目虚增

### 验证链条2：投资性资产 → 投资收益 → 投资现金流
- 投资性资产规模是否与投资收益匹配？（投资性资产报酬率）
- 投资收益收到现金的比例是否合理？

### 验证链条3：融资现金流 → 资本结构变动
- 筹资活动现金流与负债/权益变动是否一致？
- 是否存在超过实际需求的过度融资？

### 异常判断标准
- 经营性资产报酬率与投资性资产报酬率严重背离 → 战略执行偏差
- 利润增长但经营现金流持续恶化 → 盈利质量红色预警
- 资产和利润同时增长，但经营现金流为负 → 应计利润操纵嫌疑
"""

LIFECYCLE_FRAMEWORK = """
## 生命周期定位

根据经营/投资/筹资三类现金流的正负组合，判断公司所处的生命周期阶段：

| 阶段 | 经营CF | 投资CF | 筹资CF | 特征 |
|------|--------|--------|--------|------|
| 导入期 | 负 | 负 | 正 | 高投入、高风险，依赖外部融资 |
| 成长期 | 正（渐增） | 负 | 正 | 造血能力形成，持续扩张 |
| 成熟期 | 正（充裕） | 正/负 | 负 | 现金流充沛，回馈股东 |
| 衰退期 | 负 | 正 | 负 | 经营萎缩，靠处置资产维持 |

请根据提供的现金流数据判断公司所处阶段，并基于该阶段的典型特征，调整分析重心的权重：

- 导入期：重点关注融资能力、研发投入转化率、现金消耗速度
- 成长期：重点关注营收增速可持续性、市场份额变化、经营杠杆改善
- 成熟期：重点关注分红政策、自由现金流、资本配置效率
- 衰退期：重点关注资产变现能力、债务偿还压力、转型可能性
"""

WARNING_SIGNALS_FRAMEWORK = """
## 利润质量恶化预警清单（逐条核验）

以下13条预警信号，请逐一对照数据核验，标明每条的状态（正常 ⬜ / 关注 ⚠️ / 危险 ❌）：

1. **企业扩张过快** — 营收或资产增速 > 50%？管理层是否有能力驾驭快速扩张？
2. **应收账款规模不正常增加** — 应收增速是否 > 营收增速 × 1.2？账龄是否延长？
3. **企业过度举债** — 资产负债率是否 > 行业均值 × 1.5？利息保障倍数是否 < 2？
4. **会计政策和估计变更** — 近期是否有会计政策变更？变更方向是否增厚利润？
5. **审计异常** — 注册会计师是否频繁变更？审计意见类型是否为非标？
6. **应付账款不正常增加** — 付账期是否异常延长？是否暗示资金链紧张？
7. **存货周转过于缓慢** — 存货周转天数是否同比增加 > 30%？是否存在滞销风险？
8. **无形资产/开发支出异常增加** — 研发资本化比例是否突然上升？
9. **过度依赖非经常性损益** — 扣非净利润/净利润 < 0.7？（非经常性损益占比 > 30%）
10. **销售管理费用走势异常** — 费用率是否与收入变动方向不一致？
11. **反常压缩酌量性支出** — 研发、广告、维修等支出是否异常减少？
12. **有利润但不分红** — 有可分配利润但长期不进行现金分红？留存收益再投资效率如何？
13. **关联交易异常** — 关联交易规模是否大幅增加？定价是否公允？

请对每条给出：状态 + 数据依据 + 一句话判断
"""

OUTPUT_FORMAT_STRUCTURED = """
## 输出格式要求（必须遵守）

你的每个分析结论，必须按以下三段式结构化输出：

```
📊 数据依据
- [指标名称]: [具体数值] [数据来源]
- [指标名称]: [具体数值] [数据来源]

🔍 推理过程
- [基于数据的推理逻辑]
- [指出矛盾信号或不确定性]
- [引用行业对比或历史趋势佐证]

✅ 综合结论
- [一句话核心判断]
- 置信度: [高/中/低] — [置信度判断依据]
- 信号标签: [从以下列表中选择2-4个，附评分0-100]
  (现金流质量 / 盈余质量 / 资产质量 / 增长可持续性 / 财务风险 / 估值合理性 / 信用政策 / 存货风险 / 商誉风险)
```

对于多维度分析，每个维度单独一个三段式。
"""


# ============================================================================
# PromptBuilder
# ============================================================================

class PromptBuilder:
    """可组合的提示词构建器"""

    FRAMEWORKS = {
        "harvard": ("哈佛分析框架", HARVARD_FRAMEWORK),
        "crosscheck": ("三表联动验证", CROSSCHECK_FRAMEWORK),
        "lifecycle": ("生命周期定位", LIFECYCLE_FRAMEWORK),
        "warnings": ("利润质量预警清单", WARNING_SIGNALS_FRAMEWORK),
    }

    def __init__(self, company_name: str = ""):
        self._company_name = company_name
        self._data: dict | None = None
        self._frameworks: list[str] = []
        self._signals: list | None = None
        self._output_format: str | None = None
        self._mode: str = "quick"
        self._context: str | None = None
        self._question: str = ""

    def with_data(self, report: dict) -> "PromptBuilder":
        self._data = report
        return self

    def with_framework(self, framework: str) -> "PromptBuilder":
        if framework in self.FRAMEWORKS:
            if framework not in self._frameworks:
                self._frameworks.append(framework)
        else:
            import logging
            logging.getLogger(__name__).warning(
                "Unknown framework '%s', ignored. Available: %s",
                framework, list(self.FRAMEWORKS.keys()),
            )
        return self

    def with_signals(self, signals: list) -> "PromptBuilder":
        self._signals = signals
        return self

    def with_output_format(self, fmt: str) -> "PromptBuilder":
        self._output_format = fmt
        return self

    def with_mode(self, mode: str) -> "PromptBuilder":
        self._mode = mode
        return self

    def with_context(self, context: str) -> "PromptBuilder":
        self._context = context
        return self

    def with_question(self, question: str) -> "PromptBuilder":
        self._question = question
        return self

    def build(self) -> str:
        parts = []
        parts.append(self._build_role())

        if self._data:
            parts.append(self._format_data(self._data))

        if self._question and self._mode != "quick":
            parts.append(f"## 用户问题\n{self._question}")

        if self._mode == "followup" and self._context:
            parts.append(f"## 之前的分析\n{self._context}")
            parts.append("请基于上述分析，回答以下追问：")

        if self._mode in ("deep", "debate"):
            for fw_key in self._frameworks:
                name, template = self.FRAMEWORKS[fw_key]
                parts.append(f"---\n{template}")

        if self._signals and self._mode in ("deep", "debate"):
            parts.append(self._format_signals(self._signals))

        if self._output_format == "structured" or self._mode in ("quick", "deep", "followup"):
            parts.append(OUTPUT_FORMAT_STRUCTURED)

        if self._mode == "debate":
            parts.append("\n请启动三视角辩论流程。")
        elif self._mode == "deep":
            parts.append("\n请基于以上框架和数据进行全面深度分析。")
        elif self._mode == "quick":
            if self._question:
                parts.append(f"\n## 用户问题\n{self._question}")
            parts.append("\n请基于数据给出简洁、专业的回答。")

        return "\n\n".join(parts)

    def _build_role(self) -> str:
        mode_roles = {
            "quick": "你是一位专业的财务分析师，请基于提供的财务数据，用简洁、专业的中文回答问题。",
            "deep": "你是一位拥有20年经验的高级财务分析师，精通A股、港股和美股市场。你的分析以严谨、深刻和富有洞察力著称。请基于提供的财务数据和分析框架，进行深入、系统的分析。",
            "debate": "你将同时扮演三位不同视角的资深分析师（格雷厄姆式价值分析师、费雪式成长分析师、塔勒布式风控师），对以下公司进行多维度辩论分析。",
            "followup": "你是一位专业的财务分析师，请基于之前的分析上下文和数据，回答用户的追问。",
        }
        role = mode_roles.get(self._mode, mode_roles["quick"])

        # 快速模式要求输出中提到快速分析
        if self._mode == "quick" and self._company_name:
            return f"{role}\n\n**分析对象：{self._company_name}**\n\n请给出快速分析："
        if self._company_name:
            return f"{role}\n\n**分析对象：{self._company_name}**"
        return role

    def _format_data(self, report: dict) -> str:
        lines = ["## 公司数据报告"]

        snap = report.get("company_snapshot", {})
        if snap:
            lines.append("\n### 公司快照")
            name = snap.get("name", "")
            price = snap.get("price", "N/A")
            pe = snap.get("pe", "N/A")
            pb = snap.get("pb", "N/A")
            mcap = snap.get("market_cap_yi", "N/A")
            lines.append(f"  {name} | 股价: {price} | PE: {pe} | PB: {pb} | 市值: {mcap}亿")

        health = report.get("financial_health", {})
        if health:
            lines.append("\n### 财务健康仪表盘")
            for section in ["盈利能力", "偿债能力", "营运能力", "发展能力"]:
                data = health.get(section)
                if data:
                    kv_parts = []
                    for k, v in data.items():
                        if v is not None:
                            kv_parts.append(f"{k}: {v}")
                    if kv_parts:
                        lines.append(f"\n  [{section}]")
                        lines.append("  " + " | ".join(kv_parts))

        dupont = report.get("dupont_analysis", {})
        if dupont.get("three_factor"):
            lines.append("\n### 杜邦分解")
            for dp in dupont["three_factor"][:3]:
                lines.append(
                    f"  {dp.get('end_date','')}: ROE={dp.get('roe','')}% = "
                    f"净利率{dp.get('net_margin','')}% x 周转{dp.get('asset_turnover','')} "
                    f"x 杠杆{dp.get('equity_multiplier','')}"
                )

        risk = report.get("risk_models", {})
        if risk:
            lines.append("\n### 风险模型")
            for key, label in [("zscore", "Z-score"), ("fscore", "F-score"), ("mscore", "M-score")]:
                d = risk.get(key)
                if d:
                    lines.append(f"  {label}: {d}")

        cf = report.get("cashflow_analysis", {})
        if cf.get("quadrant"):
            lines.append("\n### 现金流象限")
            for q in cf["quadrant"][:2]:
                lines.append(
                    f"  {q.get('end_date','')}: {q.get('quadrant_type','')} "
                    f"(经营:{q.get('op_sign','')} 投资:{q.get('inv_sign','')} 筹资:{q.get('fin_sign','')})"
                )

        anomalies = report.get("anomaly_signals")
        if anomalies:
            lines.append("\n### 异常信号")
            for sig in anomalies:
                lines.append(
                    f"  - {sig.get('name', '')}: {sig.get('data') or sig.get('trigger_data', '')} "
                    f"(级别: {sig.get('level', '')})"
                )

        return "\n".join(lines)

    def _format_signals(self, signals: list) -> str:
        lines = ["---\n## 已检测到的异常信号\n"]
        for sig in signals:
            level_icon = {"high": "🔴", "medium": "🟡"}.get(sig.get("level", ""), "⚪")
            lines.append(f"- {level_icon} **{sig.get('name', '未知信号')}**: {sig.get('trigger_data', '')}")
            if sig.get("task"):
                lines.append(f"  → 请重点关注: {sig['task']}")
        lines.append("\n请在分析中对上述信号进行深入诊断。")
        return "\n".join(lines)
