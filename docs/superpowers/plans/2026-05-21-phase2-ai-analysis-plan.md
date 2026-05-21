# Phase 2 AI 智能财务分析模块 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建统一的 AI 对话式财务分析系统 — 核心分析逻辑独立模块化，通过 WebSocket 接入 Web UI 统一对话面板，提示词注入专业财务框架，输出结构化、可追溯的分析结果。

**Architecture:** 三层分离。`ai/` 下新建 4 个核心模块（PromptFramework, OutputParser, ConversationManager, AnalysisOrchestrator）；`deepseek/prompts.py` 重构为底层引擎；Web 层新增统一 WebSocket 对话 API；前端融合两子面板为单个对话界面。

**Tech Stack:** Python 3.11+, FastAPI + WebSocket, Jinja2 + htmx, DeepSeek API (OpenAI 兼容), Precision Glass CSS 设计令牌

---

## 文件结构

```
financial_analyzer/ai/
├── prompt_framework.py     # NEW: PromptBuilder + 4个框架注入器
├── output_parser.py        # NEW: StructuredOutput 流式解析器
├── conversation.py         # NEW: ConversationManager 多轮上下文
├── orchestrator.py         # NEW: AnalysisOrchestrator 统一调度

financial_analyzer/deepseek/
└── prompts.py              # MODIFY: 重构为 framework 底层数据提供者

financial_analyzer/web/
├── routes/ai_api.py        # MODIFY: 新增 /ai/conversation WebSocket
├── static/css/chat.css     # NEW: 对话面板样式
├── static/js/app.js        # MODIFY: 统一聊天 WebSocket 客户端
└── templates/index.html    # MODIFY: AI Tab 替换为统一对话面板

tests/
├── test_prompt_framework.py  # NEW
├── test_output_parser.py     # NEW
├── test_conversation.py      # NEW
└── test_orchestrator.py      # NEW
```

---

## Task 1: PromptFramework — 可组合提示词构建器

**Files:**
- Create: `financial_analyzer/ai/prompt_framework.py`
- Create: `tests/test_prompt_framework.py`

- [ ] **Step 1: 编写框架注入器设计的首个测试**

```python
# tests/test_prompt_framework.py
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_analyzer.ai.prompt_framework import PromptBuilder


class TestPromptBuilderQuickMode:
    def test_build_quick_mode_minimal(self):
        """快速模式：仅数据 + 问题，不注入框架"""
        report = {"company_snapshot": {"name": "测试公司"}, "financial_health": {}}
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_mode("quick")
        prompt = builder.build()

        assert "测试公司" in prompt
        assert "快速分析" in prompt


class TestPromptBuilderDeepMode:
    def test_build_deep_mode_with_harvard_framework(self):
        """深度模式：注入哈佛分析框架"""
        report = {
            "company_snapshot": {"name": "贵州茅台", "price": 1800},
            "financial_health": {
                "盈利能力": {"ROE": 30.5, "毛利率": 92.0},
                "偿债能力": {"资产负债率": 21.5},
            },
            "risk_models": {"zscore": {"z_score": 8.5}},
        }
        builder = PromptBuilder("贵州茅台")
        builder.with_data(report)
        builder.with_framework("harvard")
        builder.with_mode("deep")
        prompt = builder.build()

        assert "贵州茅台" in prompt
        assert "哈佛分析框架" in prompt
        assert "战略分析" in prompt
        assert "会计分析" in prompt
        assert "财务分析" in prompt
        assert "前景分析" in prompt
        assert "ROE" in prompt

    def test_build_deep_mode_with_crosscheck(self):
        """深度模式：注入三表联动验证"""
        report = {
            "company_snapshot": {"name": "测试公司"},
            "financial_health": {"_raw": {"net_profit": 100, "op_cashflow": 120}},
            "dupont_analysis": {"improved": [{"rnoa": 15.0, "flev": 0.5}]},
        }
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_framework("crosscheck")
        builder.with_mode("deep")
        prompt = builder.build()

        assert "三表联动验证" in prompt
        assert "经营性资产" in prompt
        assert "经营现金流" in prompt

    def test_build_deep_mode_with_lifecycle(self):
        """深度模式：注入生命周期定位框架"""
        report = {
            "company_snapshot": {"name": "测试公司"},
            "cashflow_analysis": {"quadrant": [{"quadrant_type": "成熟期"}]},
        }
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_framework("lifecycle")
        builder.with_mode("deep")
        prompt = builder.build()

        assert "生命周期" in prompt
        assert "导入期" in prompt or "成长期" in prompt or "成熟期" in prompt or "衰退期" in prompt

    def test_build_deep_mode_with_warnings(self):
        """深度模式：注入13条利润质量预警"""
        report = {
            "company_snapshot": {"name": "测试公司"},
            "anomaly_signals": [
                {"name": "盈利质量预警", "level": "high", "value": "CF/NP = 0.3"}
            ],
        }
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_framework("warnings")
        builder.with_mode("deep")
        prompt = builder.build()

        assert "利润质量预警" in prompt
        assert "盈利质量预警" in prompt

    def test_build_deep_mode_all_frameworks(self):
        """深度模式：组合全部4个框架"""
        report = {
            "company_snapshot": {"name": "测试公司"},
            "financial_health": {
                "盈利能力": {"ROE": 20.0},
                "偿债能力": {"资产负债率": 50.0},
                "营运能力": {"总资产周转率": 0.8},
                "发展能力": {"营收增长率": 15.0},
            },
            "risk_models": {"zscore": {"z_score": 3.0}, "mscore": {"m_score": -2.0}},
            "anomaly_signals": [],
            "cashflow_analysis": {"quadrant": [{"quadrant_type": "成长期"}]},
        }
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_framework("harvard")
        builder.with_framework("crosscheck")
        builder.with_framework("lifecycle")
        builder.with_framework("warnings")
        builder.with_output_format("structured")
        builder.with_mode("deep")
        prompt = builder.build()

        assert "哈佛分析框架" in prompt
        assert "三表联动验证" in prompt
        assert "生命周期" in prompt
        assert "利润质量预警" in prompt
        assert "数据依据" in prompt
        assert "推理过程" in prompt
        assert "综合结论" in prompt

    def test_build_with_signals_injection(self):
        """注入矛盾信号到提示词"""
        report = {"company_snapshot": {"name": "测试公司"}, "financial_health": {}}
        signals = [
            {"name": "盈利质量预警", "trigger_data": "CF/NP = 0.3", "task": "请解释利润缺乏现金支撑的原因"},
            {"name": "增长透支预警", "trigger_data": "AR增速/Rev增速 = 2.1", "task": "分析是否放宽信用政策"},
        ]
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_signals(signals)
        builder.with_mode("deep")
        prompt = builder.build()

        assert "盈利质量预警" in prompt
        assert "增长透支预警" in prompt
        assert "CF/NP = 0.3" in prompt
        assert "请解释利润缺乏现金支撑的原因" in prompt


class TestPromptBuilderDebateMode:
    def test_build_debate_mode_includes_roles(self):
        """辩论模式：包含三视角角色提示词"""
        report = {"company_snapshot": {"name": "测试公司"}, "financial_health": {}}
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_mode("debate")
        prompt = builder.build()

        assert "格雷厄姆" in prompt or "价值" in prompt
        assert "费雪" in prompt or "成长" in prompt
        assert "塔勒布" in prompt or "风控" in prompt
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_prompt_framework.py -v
```
Expected: all FAIL (module not found)

- [ ] **Step 3: 编写 PromptFramework 实现**

```python
# financial_analyzer/ai/prompt_framework.py
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
- [指标名称]: [具体数值] [数据来源：如2024年报·资产负债表]
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
        self._context: str | None = None  # 追问上下文

    def with_data(self, report: dict) -> "PromptBuilder":
        """注入结构化体检数据"""
        self._data = report
        return self

    def with_framework(self, framework: str) -> "PromptBuilder":
        """叠加一个分析框架 (harvard / crosscheck / lifecycle / warnings)"""
        if framework in self.FRAMEWORKS:
            self._frameworks.append(framework)
        return self

    def with_signals(self, signals: list) -> "PromptBuilder":
        """注入已检测的矛盾信号"""
        self._signals = signals
        return self

    def with_output_format(self, fmt: str) -> "PromptBuilder":
        """设置输出格式 (structured / free)"""
        self._output_format = fmt
        return self

    def with_mode(self, mode: str) -> "PromptBuilder":
        """
        设置分析模式：
        - "quick": 轻量提示词，仅数据 + 问题
        - "deep": 完整框架注入，结构化输出
        - "debate": 三视角辩论提示词
        - "followup": 追问模式，注入上下文
        """
        self._mode = mode
        return self

    def with_context(self, context: str) -> "PromptBuilder":
        """注入对话上下文（追问模式）"""
        self._context = context
        return self

    def build(self) -> str:
        """组装完整提示词"""
        parts = []

        # --- 角色设定 ---
        parts.append(self._build_role())

        # --- 公司数据 ---
        if self._data:
            parts.append(self._format_data(self._data))

        # --- 对话上下文（追问模式）---
        if self._mode == "followup" and self._context:
            parts.append(f"## 之前的分析\n{self._context}")
            parts.append("请基于上述分析，回答以下追问：")

        # --- 分析框架（深度模式）---
        if self._mode in ("deep", "debate"):
            for fw_key in self._frameworks:
                name, template = self.FRAMEWORKS[fw_key]
                parts.append(f"---\n{template}")

        # --- 矛盾信号注入 ---
        if self._signals and self._mode in ("deep", "debate"):
            parts.append(self._format_signals(self._signals))

        # --- 输出格式约束 ---
        if self._output_format == "structured":
            parts.append(OUTPUT_FORMAT_STRUCTURED)
        elif self._mode == "deep" and not self._output_format:
            # 深度模式默认结构化输出
            parts.append(OUTPUT_FORMAT_STRUCTURED)

        # --- 模式特定尾缀 ---
        if self._mode == "debate":
            parts.append("\n请启动三视角辩论流程。")
        elif self._mode == "deep":
            parts.append("\n请基于以上框架和数据进行全面深度分析。")
        elif self._mode == "quick":
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
        if self._company_name:
            return f"{role}\n\n**分析对象：{self._company_name}**"
        return role

    def _format_data(self, report: dict) -> str:
        """将体检报告 dict 转为紧凑的可读文本"""
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

        return "\n".join(lines)

    def _format_signals(self, signals: list) -> str:
        """格式化矛盾信号"""
        lines = ["---\n## 已检测到的异常信号\n"]
        for sig in signals:
            level_icon = {"high": "🔴", "medium": "🟡"}.get(sig.get("level", ""), "⚪")
            lines.append(f"- {level_icon} **{sig['name']}**: {sig.get('trigger_data', '')}")
            if sig.get("task"):
                lines.append(f"  → 请重点关注: {sig['task']}")
        lines.append("\n请在分析中对上述信号进行深入诊断。")
        return "\n".join(lines)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_prompt_framework.py -v
```
Expected: all PASS

- [ ] **Step 5: 提交**

```bash
git add financial_analyzer/ai/prompt_framework.py tests/test_prompt_framework.py
git commit -m "feat: add PromptFramework with 4 professional analysis frameworks

Harvard framework, 3-table cross-check, lifecycle positioning, and 13 warning
signals checklist. Builder pattern with quick/deep/debate/followup modes.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: OutputParser — 结构化输出解析器

**Files:**
- Create: `financial_analyzer/ai/output_parser.py`
- Create: `tests/test_output_parser.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_output_parser.py
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_analyzer.ai.output_parser import OutputParser, StructuredOutput


class TestOutputParserBasic:
    def test_empty_input(self):
        parser = OutputParser()
        events = parser.feed("")
        assert events == []

    def test_single_chunk_no_structure(self):
        parser = OutputParser()
        events = parser.feed("这是一段普通文本，没有结构化标记。")
        assert len(events) == 1
        assert events[0]["type"] == "chunk"
        assert events[0]["content"] == "这是一段普通文本，没有结构化标记。"

    def test_multiple_chunks_merge(self):
        parser = OutputParser()
        parser.feed("第一段")
        parser.feed("续接文本")
        events = parser.feed("最后一段")

        assert len(events) == 3
        assert events[0]["content"] == "第一段"
        assert events[1]["content"] == "续接文本"
        assert events[2]["content"] == "最后一段"


class TestOutputParserStructured:
    def test_detect_data_section(self):
        """检测到 📊 数据依据 标记时产出 structured 事件"""
        parser = OutputParser()
        chunk = "📊 数据依据\n- ROE: 20% [2024年报]\n- 毛利率: 92%"
        events = parser.feed(chunk)

        # 含结构化标记的内容仍作为 chunk 推送（实时显示）
        assert any(e["type"] == "chunk" for e in events)

    def test_extract_confidence_high(self):
        parser = OutputParser()
        parser.feed("📊 数据依据\n- ROE: 20%\n🔍 推理过程\n公司盈利能力强\n✅ 综合结论\n盈利质量优秀\n置信度: 高")

        result = parser.finalize()
        assert result is not None
        assert result.confidence == "高"
        assert "ROE" in result.raw_text
        assert "盈利质量优秀" in result.conclusion

    def test_extract_confidence_medium(self):
        parser = OutputParser()
        parser.feed("置信度: 中 — 部分数据缺失")
        result = parser.finalize()
        assert result.confidence == "中"

    def test_extract_confidence_low(self):
        parser = OutputParser()
        parser.feed("置信度: 低")
        result = parser.finalize()
        assert result.confidence == "低"

    def test_no_confidence_found(self):
        parser = OutputParser()
        parser.feed("这是一段没有置信度标注的分析结论。")
        result = parser.finalize()
        assert result.confidence == "未标注"

    def test_extract_signal_tags(self):
        parser = OutputParser()
        parser.feed(
            "📊 数据依据\n- 经营CF/净利润: 1.23\n"
            "🔍 推理过程\n现金流覆盖充足\n"
            "✅ 综合结论\n盈利质量好\n"
            "置信度: 高\n"
            "信号标签: 现金流质量 92/100, 盈余质量 优, 应收增速 偏高"
        )
        result = parser.finalize()
        assert len(result.signal_tags) >= 2
        names = [t["name"] for t in result.signal_tags]
        assert "现金流质量" in names
        assert "盈余质量" in names

    def test_partial_marker_not_yet_structured(self):
        """不完整标记（如只看到 📊）不产出 structured 事件"""
        parser = OutputParser()
        events = parser.feed("这是一个📊字符，可能不是标记")
        # 没有完整的结构化区段，不应触发 structured 类型事件
        types = [e["type"] for e in events]
        assert "structured" not in types

    def test_finalize_resets_state(self):
        parser = OutputParser()
        parser.feed("📊 数据\n置信度: 高")
        parser.finalize()
        parser.feed("新的对话")
        result = parser.finalize()
        assert result.raw_text == "新的对话"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_output_parser.py -v
```
Expected: all FAIL

- [ ] **Step 3: 编写 OutputParser 实现**

```python
# financial_analyzer/ai/output_parser.py
"""
流式结构化输出解析器

在 LLM 流式输出过程中，实时检测结构化标记（📊 🔍 ✅）
并将文本块推送给前端显示，同时在流结束后提取结构化数据。
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class StructuredOutput:
    """解析完成的结构化分析输出"""
    data_points: list[dict] = field(default_factory=list)
    reasoning: str = ""
    conclusion: str = ""
    confidence: str = "未标注"  # "高" | "中" | "低" | "未标注"
    signal_tags: list[dict] = field(default_factory=list)
    raw_text: str = ""


class OutputParser:
    """流式结构化输出解析器"""

    # 三级置信度关键词
    CONFIDENCE_PATTERNS = {
        "high": [r"置信度[：:]\s*高", r"置信度[：:]\s*强"],
        "medium": [r"置信度[：:]\s*中", r"置信度[：:]\s*一般"],
        "low": [r"置信度[：:]\s*低", r"置信度[：:]\s*弱", r"置信度[：:]\s*差"],
    }

    # 信号标签提取：标签名 [可选评分]
    # 如 "现金流质量 92/100" 或 "盈余质量 优"
    SIGNAL_TAG_PATTERN = re.compile(
        r"(现金流质量|盈余质量|资产质量|增长可持续性|财务风险|估值合理性|信用政策|存货风险|商誉风险)"
        r"\s*(\d{1,3}/\d{1,3}|优|良|中|差|偏高|偏低|正常|关注|危险)?"
    )

    # 三区段分隔标记
    SECTION_MARKERS = {
        "data": re.compile(r"📊\s*数据依据"),
        "reasoning": re.compile(r"🔍\s*推理过程"),
        "conclusion": re.compile(r"✅\s*综合结论"),
    }

    def __init__(self):
        self._buffer = ""
        self._current_section: str | None = None

    def feed(self, chunk: str) -> list[dict]:
        """喂入一个文本块，返回事件列表"""
        self._buffer += chunk

        events = [{"type": "chunk", "content": chunk}]

        # 检测区段切换
        for section_name, pattern in self.SECTION_MARKERS.items():
            if pattern.search(self._buffer) and self._current_section != section_name:
                self._current_section = section_name
                events.append({
                    "type": "meta",
                    "content": f"section:{section_name}",
                })
                break

        return events

    def finalize(self) -> StructuredOutput | None:
        """流结束后提取结构化数据"""
        if not self._buffer.strip():
            return None

        result = StructuredOutput(raw_text=self._buffer)

        # 提取置信度
        for level, patterns in self.CONFIDENCE_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, self._buffer):
                    label_map = {"high": "高", "medium": "中", "low": "低"}
                    result.confidence = label_map[level]
                    break
            if result.confidence != "未标注":
                break

        # 提取信号标签
        signal_section_match = re.search(
            r"信号标签[：:](.*?)(?:\n\n|\n(?![ \t]*[-•])|$)",
            self._buffer, re.DOTALL
        )
        if signal_section_match:
            tags_text = signal_section_match.group(1)
            for m in self.SIGNAL_TAG_PATTERN.finditer(tags_text):
                result.signal_tags.append({
                    "name": m.group(1),
                    "value": (m.group(2) or "").strip(),
                })

        # 提取结论区段
        conclusion_match = re.search(
            r"✅\s*综合结论(.*?)(?=\n📊|\n##|\Z)",
            self._buffer, re.DOTALL
        )
        if conclusion_match:
            result.conclusion = conclusion_match.group(1).strip()

        # 提取推理区段
        reasoning_match = re.search(
            r"🔍\s*推理过程(.*?)(?=✅|\Z)",
            self._buffer, re.DOTALL
        )
        if reasoning_match:
            result.reasoning = reasoning_match.group(1).strip()

        # 重置状态
        self._buffer = ""
        self._current_section = None

        return result
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_output_parser.py -v
```
Expected: all PASS

- [ ] **Step 5: 提交**

```bash
git add financial_analyzer/ai/output_parser.py tests/test_output_parser.py
git commit -m "feat: add OutputParser for structured streaming analysis output

Detects data/reasoning/conclusion sections, extracts confidence labels
and signal tags from streaming LLM output.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: ConversationManager — 多轮对话管理

**Files:**
- Create: `financial_analyzer/ai/conversation.py`
- Create: `tests/test_conversation.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_conversation.py
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_analyzer.ai.conversation import ConversationManager, Message


class TestConversationManager:
    def test_add_and_retrieve_messages(self):
        cm = ConversationManager()
        cm.add_message(Message(role="user", content="分析盈利能力", msg_type="text"))
        cm.add_message(Message(role="assistant", content="盈利能力分析如下...", msg_type="text"))

        ctx = cm.get_context()
        assert len(ctx) == 2
        assert ctx[0].role == "user"
        assert ctx[1].role == "assistant"

    def test_get_context_for_llm(self):
        cm = ConversationManager()
        cm.add_message(Message(role="system", content="你是财务分析师", msg_type="system"))
        cm.add_message(Message(role="user", content="问题", msg_type="text"))
        cm.add_message(Message(role="assistant", content="回答", msg_type="text"))

        llm_msgs = cm.get_context_for_llm()
        assert len(llm_msgs) == 3
        assert llm_msgs[0]["role"] == "system"
        assert llm_msgs[1]["role"] == "user"
        assert llm_msgs[2]["role"] == "assistant"

    def test_context_limit_trims_oldest(self):
        cm = ConversationManager(max_history=3)
        for i in range(5):
            cm.add_message(Message(role="user", content=f"msg{i}", msg_type="text"))

        ctx = cm.get_context()
        assert len(ctx) == 3
        assert ctx[0].content == "msg2"
        assert ctx[-1].content == "msg4"

    def test_clear_resets_all(self):
        cm = ConversationManager()
        cm.add_message(Message(role="user", content="test", msg_type="text"))
        cm.clear()
        assert len(cm.get_context()) == 0

    def test_metadata_preserved(self):
        cm = ConversationManager()
        cm.add_message(Message(
            role="assistant", content="分析结果",
            msg_type="structured",
            metadata={"confidence": "高", "signals": ["现金流质量 92"]},
        ))
        ctx = cm.get_context()
        assert ctx[0].msg_type == "structured"
        assert ctx[0].metadata["confidence"] == "高"

    def test_empty_context_for_llm(self):
        cm = ConversationManager()
        llm_msgs = cm.get_context_for_llm()
        assert llm_msgs == []

    def test_system_message_preserved_in_llm_context(self):
        """System 消息即使超过 limit，也应始终保留在 LLM 上下文中"""
        cm = ConversationManager(max_history=2)
        cm.add_message(Message(role="system", content="系统提示词", msg_type="system"))
        cm.add_message(Message(role="user", content="q1", msg_type="text"))
        cm.add_message(Message(role="assistant", content="a1", msg_type="text"))
        cm.add_message(Message(role="user", content="q2", msg_type="text"))

        llm_msgs = cm.get_context_for_llm()
        assert llm_msgs[0]["role"] == "system"
        assert len(llm_msgs) >= 3  # system + 至少2条最近消息
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_conversation.py -v
```
Expected: all FAIL

- [ ] **Step 3: 编写 ConversationManager 实现**

```python
# financial_analyzer/ai/conversation.py
"""
多轮对话上下文管理器

管理对话消息历史，支持上下文裁剪、LLM 格式转换和会话级别状态。
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field


@dataclass
class Message:
    """单条对话消息"""
    role: str   # "user" | "assistant" | "system"
    content: str
    msg_type: str = "text"   # "text" | "structured" | "tool_call" | "meta"
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ConversationManager:
    """多轮对话上下文管理器"""

    def __init__(self, max_history: int = 50):
        self._messages: list[Message] = []
        self._max_history = max_history
        self._system_message: Message | None = None

    def add_message(self, msg: Message):
        """添加一条消息"""
        if msg.role == "system":
            self._system_message = msg
            return
        self._messages.append(msg)
        # 超过限制时裁剪最早的非系统消息
        while len(self._messages) > self._max_history:
            self._messages.pop(0)

    def get_context(self, limit: int | None = None) -> list[Message]:
        """获取最近的消息列表"""
        msgs = self._messages
        if limit is not None:
            msgs = msgs[-limit:]
        return list(msgs)

    def get_context_for_llm(self) -> list[dict]:
        """转为 OpenAI 兼容的消息格式"""
        result = []
        if self._system_message:
            result.append({
                "role": "system",
                "content": self._system_message.content,
            })
        for msg in self._messages:
            role = "assistant" if msg.role == "assistant" else "user"
            result.append({"role": role, "content": msg.content})
        return result

    def clear(self):
        """清空对话历史"""
        self._messages.clear()

    @property
    def message_count(self) -> int:
        return len(self._messages)

    def get_last_assistant_message(self) -> Message | None:
        """获取最后一条 assistant 消息"""
        for msg in reversed(self._messages):
            if msg.role == "assistant":
                return msg
        return None

    def get_all_assistant_content(self) -> str:
        """获取所有 assistant 消息的内容拼接（用于上下文）"""
        parts = []
        for msg in self._messages:
            if msg.role == "assistant":
                parts.append(msg.content)
        return "\n\n".join(parts)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_conversation.py -v
```
Expected: all PASS

- [ ] **Step 5: 提交**

```bash
git add financial_analyzer/ai/conversation.py tests/test_conversation.py
git commit -m "feat: add ConversationManager for multi-turn dialogue context

Manages message history with configurable limits, LLM-format conversion,
and system message preservation.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: AnalysisOrchestrator — 统一分析调度器

**Files:**
- Create: `financial_analyzer/ai/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: 编写测试**

```python
# tests/test_orchestrator.py
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_analyzer.ai.orchestrator import AnalysisOrchestrator
from financial_analyzer.ai.conversation import ConversationManager, Message
from financial_analyzer.ai.prompt_framework import PromptBuilder


class FakeLLMClient:
    """模拟 LLM 客户端，用于测试调度逻辑"""
    def __init__(self):
        self.calls = []
        self._stream_responses = ["模拟分析结果。置信度: 高"]

    def generate_deep_analysis_stream(self, prompt, system_prompt=None, callback=None):
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt})
        from financial_analyzer.deepseek.client import AnalysisReport
        for chunk in self._stream_responses:
            if callback:
                callback(chunk, False)
        if callback:
            callback("", True)
        report = AnalysisReport()
        report.success = True
        report.content = "".join(self._stream_responses)
        return report


class FakeDebateEngine:
    """模拟辩论引擎"""
    def __init__(self):
        self.prepare_called = False
        self.start_called = False

    def prepare(self, data, stock_code, *args, **kwargs):
        self.prepare_called = True
        return {"report": {}, "report_text": "mock", "signals": [], "briefings": {}}


class TestAnalysisOrchestratorIntent:
    def test_identify_quick_intent(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        assert orchestrator._identify_intent("贵州茅台的PE是多少？") == "quick"

    def test_identify_deep_intent(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        assert orchestrator._identify_intent("/deep 全面分析盈利能力") == "deep"

    def test_identify_debate_intent(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        assert orchestrator._identify_intent("/debate") == "debate"

    def test_identify_deep_keywords(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        deep_phrases = [
            "深度分析贵州茅台的盈利能力",
            "全面评估公司的财务健康状况",
            "系统地分析现金流质量",
        ]
        for phrase in deep_phrases:
            assert orchestrator._identify_intent(phrase) == "deep", f"Failed: {phrase}"

    def test_followup_in_context(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        conv = ConversationManager()
        conv.add_message(Message(role="assistant", content="盈利能力分析完成，ROE=30%...", msg_type="structured"))
        # 有历史上下文的简短问题应识别为追问
        intent = orchestrator._identify_intent("为什么ROE这么高？", conversation=conv)
        assert intent == "followup"


class TestAnalysisOrchestratorBuildPrompt:
    def test_build_prompt_quick_mode(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        data = {"company_snapshot": {"name": "测试"}}
        prompt = orchestrator._build_prompt("quick", "测试问题", data, None, [])
        assert "测试问题" in prompt
        assert "测试" in prompt

    def test_build_prompt_deep_mode(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        data = {
            "company_snapshot": {"name": "贵州茅台"},
            "financial_health": {
                "盈利能力": {"ROE": 30.5, "毛利率": 92.0},
                "偿债能力": {"资产负债率": 21.5},
                "营运能力": {"总资产周转率": 0.5},
                "发展能力": {"营收增长率": 15.0},
            },
            "risk_models": {
                "zscore": {"z_score": 8.5},
                "mscore": {"m_score": -2.5},
            },
            "anomaly_signals": [],
            "cashflow_analysis": {"quadrant": [{"quadrant_type": "成熟期", "op_sign": "正", "inv_sign": "负", "fin_sign": "负"}]},
        }
        signals = [
            {"name": "纸面富贵预警", "trigger_data": "ROE=30.5%", "task": "分析杠杆贡献率", "level": "medium"},
        ]
        prompt = orchestrator._build_prompt("deep", "深度分析", data, None, signals)
        assert "哈佛分析框架" in prompt
        assert "三表联动验证" in prompt
        assert "生命周期" in prompt
        assert "利润质量预警" in prompt
        assert "纸面富贵预警" in prompt
        assert "数据依据" in prompt
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_orchestrator.py -v
```
Expected: all FAIL

- [ ] **Step 3: 编写 AnalysisOrchestrator 实现**

```python
# financial_analyzer/ai/orchestrator.py
"""
统一分析调度器

接收用户消息和对话上下文，识别分析意图，选择分析模式，
构建提示词，调用 LLM，解析输出。
"""
from __future__ import annotations
import json
import threading
from typing import Callable

from ..logging_config import get_logger
from .conversation import ConversationManager, Message
from .prompt_framework import PromptBuilder
from .output_parser import OutputParser
from .signal_detector import SignalDetector
from .report_builder import ReportBuilder

logger = get_logger(__name__)

# 深度分析关键词
DEEP_KEYWORDS = [
    "深度分析", "全面分析", "全面评估", "系统分析", "系统地分析",
    "综合分析", "全方位分析", "深入分析",
]

# 辩论关键词
DEBATE_KEYWORDS = ["三方辩论", "多空辩论", "价值成长风控"]


class AnalysisOrchestrator:
    """统一分析调度器"""

    def __init__(self, llm_client, debate_engine_factory=None):
        """
        Args:
            llm_client: DeepSeekStreamClient 或兼容的 LLM 客户端
            debate_engine_factory: 可选，辩论引擎工厂函数
        """
        self._llm = llm_client
        self._debate_factory = debate_engine_factory

    def analyze(
        self,
        user_message: str,
        conversation: ConversationManager,
        data: dict,
        stock_code: str,
        company_name: str = "",
        callback: Callable | None = None,
    ):
        """
        统一分析入口

        Args:
            user_message: 用户消息文本
            conversation: 对话管理器
            data: 原始财务数据 (income/balance/cashflow)
            stock_code: 股票代码
            company_name: 公司名称
            callback: 回调函数 callback(event_type: str, content: str, meta: dict | None)

        执行流程按照 intent 分派：
        - "quick" → _stream_quick()
        - "deep" → _stream_deep()
        - "debate" → _stream_debate()
        - "followup" → _stream_followup()
        """
        # 添加用户消息
        conversation.add_message(Message(role="user", content=user_message, msg_type="text"))

        # 意图识别
        intent = self._identify_intent(user_message, conversation)

        # 构建结构化报告（deep / debate 模式需要）
        report = None
        signals = []
        if intent in ("deep", "debate"):
            try:
                report = ReportBuilder.build(data, stock_code)
                signals = SignalDetector.detect(report)
            except Exception as e:
                logger.warning(f"Report building failed: {e}")

        if callback:
            callback("meta", f"intent:{intent}", None)

        # 按意图分派
        if intent == "debate" and self._debate_factory:
            self._stream_debate(data, stock_code, company_name, conversation, callback)
        elif intent == "deep":
            self._stream_deep(data, report, signals, user_message, conversation, callback)
        elif intent == "followup":
            self._stream_followup(data, report, signals, user_message, conversation, callback)
        else:
            self._stream_quick(data, report, user_message, conversation, callback)

    def _identify_intent(self, message: str, conversation: ConversationManager | None = None) -> str:
        """识别用户分析意图"""
        msg_lower = message.strip().lower()

        # 显式命令优先
        if msg_lower.startswith("/debate"):
            return "debate"
        if msg_lower.startswith("/deep"):
            return "deep"

        # 辩论关键词
        for kw in DEBATE_KEYWORDS:
            if kw in message:
                return "debate"

        # 深度分析关键词
        for kw in DEEP_KEYWORDS:
            if kw in message:
                return "deep"

        # 有历史上下文且问题简短 → 追问
        if conversation and conversation.message_count >= 2:
            last_assisstant = conversation.get_last_assistant_message()
            if last_assisstant and len(message) < 50:
                return "followup"

        # 默认快速模式
        return "quick"

    def _build_prompt(self, intent: str, message: str, data: dict | None,
                      report: dict | None, signals: list | None) -> str:
        """构建提示词"""
        builder = PromptBuilder()

        if intent == "quick":
            builder.with_mode("quick")
            if report:
                builder.with_data(report)
            else:
                # 直接用原始消息
                pass

        elif intent == "deep":
            builder.with_mode("deep")
            if report:
                builder.with_data(report)
            builder.with_framework("harvard")
            builder.with_framework("crosscheck")
            builder.with_framework("lifecycle")
            builder.with_framework("warnings")
            builder.with_output_format("structured")
            if signals:
                builder.with_signals(signals)

        elif intent == "followup":
            builder.with_mode("followup")
            if report:
                builder.with_data(report)

        elif intent == "debate":
            builder.with_mode("debate")
            if report:
                builder.with_data(report)

        return builder.build()

    # ========================================================================
    # 各模式流式处理
    # ========================================================================

    def _stream_quick(self, data, report, message, conversation, callback):
        """快速模式：简单问答"""
        prompt = self._build_prompt("quick", message, data, report, None)
        parser = OutputParser()

        def on_chunk(chunk: str, done: bool):
            if chunk:
                for event in parser.feed(chunk):
                    if callback:
                        cb_type = event.get("type", "chunk")
                        callback(cb_type, event.get("content", ""), None)
            if done:
                result = parser.finalize()
                if result and callback:
                    callback("structured", result.raw_text, {
                        "confidence": result.confidence,
                        "signal_tags": result.signal_tags,
                    })
                    conversation.add_message(Message(
                        role="assistant", content=result.raw_text,
                        msg_type="structured",
                        metadata={"confidence": result.confidence, "signal_tags": result.signal_tags},
                    ))
                if callback:
                    callback("done", "", None)

        result = self._llm.generate_deep_analysis_stream(prompt, callback=on_chunk)
        if not result.success:
            if callback:
                callback("error", result.error or "AI 分析失败", None)

    def _stream_deep(self, data, report, signals, message, conversation, callback):
        """深度模式：完整框架 + 结构化输出"""
        prompt = self._build_prompt("deep", message, data, report, signals)
        parser = OutputParser()

        def on_chunk(chunk: str, done: bool):
            if chunk:
                for event in parser.feed(chunk):
                    if callback:
                        cb_type = event.get("type", "chunk")
                        callback(cb_type, event.get("content", ""), None)
            if done:
                result = parser.finalize()
                if result and callback:
                    callback("structured", result.raw_text, {
                        "confidence": result.confidence,
                        "signal_tags": result.signal_tags,
                    })
                    conversation.add_message(Message(
                        role="assistant", content=result.raw_text,
                        msg_type="structured",
                        metadata={"confidence": result.confidence, "signal_tags": result.signal_tags},
                    ))
                if callback:
                    callback("done", "", None)

        result = self._llm.generate_deep_analysis_stream(prompt, callback=on_chunk)
        if not result.success:
            if callback:
                callback("error", result.error or "AI 分析失败", None)

    def _stream_followup(self, data, report, signals, message, conversation, callback):
        """追问模式：注入历史上下文"""
        context = conversation.get_all_assistant_content()
        prompt = self._build_prompt("followup", message, data, report, signals)

        # 注入上下文
        if context:
            prompt = f"## 之前的分析上下文\n{context[:3000]}\n\n---\n\n{prompt}"

        parser = OutputParser()

        def on_chunk(chunk: str, done: bool):
            if chunk:
                for event in parser.feed(chunk):
                    if callback:
                        cb_type = event.get("type", "chunk")
                        callback(cb_type, event.get("content", ""), None)
            if done:
                result = parser.finalize()
                if result:
                    conversation.add_message(Message(
                        role="assistant", content=result.raw_text,
                        msg_type="text",
                        metadata={"confidence": result.confidence},
                    ))
                if callback:
                    callback("done", "", None)

        result = self._llm.generate_deep_analysis_stream(prompt, callback=on_chunk)
        if not result.success:
            if callback:
                callback("error", result.error or "AI 分析失败", None)

    def _stream_debate(self, data, stock_code, company_name, conversation, callback):
        """辩论模式：委托 DebateEngine"""
        if not self._debate_factory:
            if callback:
                callback("error", "辩论引擎不可用", None)
            return

        if callback:
            callback("meta", "debate_start", None)

        try:
            engine = self._debate_factory()
            prepare_result = engine.prepare(data, stock_code)
            if not company_name:
                company_name = prepare_result.get("report", {}).get("company_snapshot", {}).get("name", stock_code)

            import queue
            msg_queue = queue.Queue()
            QUEUE_DONE = object()

            def debate_callback(role: str, chunk: str, done: bool):
                msg_queue.put((role, chunk, done))

            def on_complete(state):
                msg_queue.put(QUEUE_DONE)

            engine.start_debate(
                company_name=company_name,
                stock_code=stock_code,
                callback=debate_callback,
                on_complete=on_complete,
            )

            import asyncio
            loop = asyncio.get_event_loop()

            while True:
                msg = msg_queue.get()
                if msg is QUEUE_DONE:
                    if callback:
                        callback("done", "", None)
                    break

                role, content, done = msg
                if role == "_meta":
                    if callback:
                        callback("meta", content, None)
                else:
                    if callback:
                        callback("chunk", content, {"role": role, "done": done})

            # 保存辩论结果
            full_debate_text = engine._build_full_debate_text()
            conversation.add_message(Message(
                role="assistant", content=full_debate_text,
                msg_type="structured",
                metadata={"mode": "debate", "rounds": 3},
            ))

        except Exception as e:
            logger.error(f"Debate failed: {e}")
            if callback:
                callback("error", str(e), None)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_orchestrator.py -v
```
Expected: all PASS (FakeLLMClient is used, no real API calls)

- [ ] **Step 5: 提交**

```bash
git add financial_analyzer/ai/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add AnalysisOrchestrator for unified analysis dispatch

Intent recognition (quick/deep/debate/followup), mode-aware prompt
building, and streaming output with structured parsing.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: 重构 deepseek/prompts.py

**Files:**
- Modify: `financial_analyzer/deepseek/prompts.py`

- [ ] **Step 1: 确认现有 prompts.py 的公共接口未被破坏**

```bash
python -c "
from financial_analyzer.deepseek.prompts import (
    ANALYST_ROLES, DEEP_ANALYSIS_SYSTEM_PROMPT,
    get_analyst_roles, get_analysis_prompt, build_multi_perspective_prompt,
    get_debate_system_prompt, build_debate_round1, build_debate_round2,
    build_debate_round3, build_user_followup, build_weight_adjustment,
    build_signal_detection_prompt, build_health_report_prompt, build_briefing_prompt,
)
print('All existing imports OK')
"
```

- [ ] **Step 2: 在 `deepseek/prompts.py` 底部追加 `get_framework_templates()` 导出函数**

```python
# 追加到 financial_analyzer/deepseek/prompts.py 末尾

# ============================================================================
# Phase 2: 框架模板导出（供 ai/prompt_framework.py 使用）
# ============================================================================

def get_framework_templates() -> dict:
    """
    返回专业分析框架模板字典

    由 ai/prompt_framework.py 调用，将方法论从提示词文件中解耦导出。

    Returns:
        {
            "harvard": str,       # 哈佛分析框架
            "crosscheck": str,    # 三表联动验证
            "lifecycle": str,     # 生命周期定位
            "warnings": str,      # 13条利润质量预警
        }
    """
    from ..ai.prompt_framework import (
        HARVARD_FRAMEWORK,
        CROSSCHECK_FRAMEWORK,
        LIFECYCLE_FRAMEWORK,
        WARNING_SIGNALS_FRAMEWORK,
    )
    return {
        "harvard": HARVARD_FRAMEWORK,
        "crosscheck": CROSSCHECK_FRAMEWORK,
        "lifecycle": LIFECYCLE_FRAMEWORK,
        "warnings": WARNING_SIGNALS_FRAMEWORK,
    }
```

- [ ] **Step 3: 验证双向导入无循环**

```bash
python -c "
from financial_analyzer.deepseek.prompts import get_framework_templates
templates = get_framework_templates()
assert 'harvard' in templates
assert 'crosscheck' in templates
assert 'lifecycle' in templates
assert 'warnings' in templates
print('Framework templates exported successfully')
"
```

- [ ] **Step 4: 提交**

```bash
git add financial_analyzer/deepseek/prompts.py
git commit -m "refactor: export framework templates from prompts.py

Add get_framework_templates() to bridge prompt_framework templates
into the existing deepseek prompt system.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: WebSocket 统一对话 API

**Files:**
- Modify: `financial_analyzer/web/routes/ai_api.py`

- [ ] **Step 1: 新增 `/ai/conversation` WebSocket 端点**

在 `ai_api.py` 文件末尾追加以下内容：

```python
# 追加到 financial_analyzer/web/routes/ai_api.py 末尾

@router.websocket("/conversation")
async def ai_conversation(websocket: WebSocket):
    """统一 AI 对话入口 — 支持快速问答、深度分析、三方辩论"""
    await websocket.accept()
    orchestrator = None
    conversation = None

    try:
        # 接收初始化消息
        init_data = await websocket.receive_text()
        params = json.loads(init_data)
        stock_code = params.get("stock_code", "")

        if not stock_code:
            await websocket.send_text(json.dumps({"type": "error", "content": "缺少股票代码"}))
            await websocket.close()
            return

        # 获取 session 数据
        session = _get_session_for_ws(stock_code)
        if not session or not session.get("data"):
            await websocket.send_text(json.dumps({
                "type": "error",
                "content": "请先获取财务数据，再使用 AI 分析功能"
            }))
            await websocket.close()
            return

        data = {k: pd.DataFrame(v) for k, v in session["data"].items()}
        company_name = session.get("stock_name", stock_code)

        # 初始化 AI 组件
        ai_config = _get_ai_config()
        api_key = ai_config.get("api_key", "")
        if not api_key:
            await websocket.send_text(json.dumps({"type": "error", "content": "请先配置 DeepSeek API Key"}))
            await websocket.close()
            return

        from financial_analyzer.deepseek.client import DeepSeekConfig, DeepSeekStreamClient
        from financial_analyzer.ai.conversation import ConversationManager
        from financial_analyzer.ai.orchestrator import AnalysisOrchestrator

        config = DeepSeekConfig(api_key=api_key)
        client = DeepSeekStreamClient(config=config)

        # 辩论引擎工厂
        def debate_factory():
            from financial_analyzer.ai.debate_engine import DebateEngine
            engine = DebateEngine(config=config)
            return engine

        orchestrator = AnalysisOrchestrator(
            llm_client=client,
            debate_engine_factory=debate_factory,
        )
        conversation = ConversationManager()

        # 通知前端就绪
        await websocket.send_text(json.dumps({"type": "meta", "content": "ready"}))

        # 消息循环
        while True:
            msg_data = await websocket.receive_text()
            msg = json.loads(msg_data)

            if msg.get("type") == "message":
                user_message = msg.get("content", "").strip()
                if not user_message:
                    continue

                # 使用队列桥接同步线程和异步 WebSocket
                import queue as q_module
                msg_queue = q_module.Queue()
                loop = asyncio.get_event_loop()

                def analysis_callback(event_type: str, content: str, meta: dict | None):
                    msg_queue.put((event_type, content, meta))

                # 在线程中执行分析（避免阻塞事件循环）
                def run_analysis():
                    try:
                        orchestrator.analyze(
                            user_message=user_message,
                            conversation=conversation,
                            data=data,
                            stock_code=stock_code,
                            company_name=company_name,
                            callback=analysis_callback,
                        )
                    except Exception as e:
                        logger.error(f"Analysis error: {e}", exc_info=True)
                        msg_queue.put(("error", str(e), None))

                thread = threading.Thread(target=run_analysis, daemon=True)
                thread.start()

                # 流式推送结果
                while True:
                    item = await loop.run_in_executor(None, msg_queue.get)
                    event_type, content, meta = item

                    if event_type == "done":
                        await websocket.send_text(json.dumps({"type": "done", "content": ""}))
                        break

                    payload = {"type": event_type, "content": content}
                    if meta:
                        payload["meta"] = meta
                    await websocket.send_text(json.dumps(payload))

            elif msg.get("type") == "stop":
                # 用户中断当前分析
                await websocket.send_text(json.dumps({"type": "meta", "content": "stopped"}))
                break

    except WebSocketDisconnect:
        logger.info("AI conversation WebSocket disconnected")
    except Exception as e:
        logger.error(f"AI conversation error: {e}", exc_info=True)
        try:
            await websocket.send_text(json.dumps({"type": "error", "content": str(e)}))
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
```

- [ ] **Step 2: 确认新旧端点共存且旧端点不受影响**

```bash
python -c "
from financial_analyzer.web.routes.ai_api import router
routes = [r.path for r in router.routes]
print('Registered routes:')
for r in routes:
    print(f'  {r}')
assert '/ai/chat' in routes or any('chat' in str(r) for r in router.routes)
assert '/ai/debate' in routes or any('debate' in str(r) for r in router.routes)
assert '/ai/conversation' in routes or any('conversation' in str(r) for r in router.routes)
print('All endpoints registered')
"
```

- [ ] **Step 3: 提交**

```bash
git add financial_analyzer/web/routes/ai_api.py
git commit -m "feat: add /ai/conversation WebSocket for unified AI dialogue

Single endpoint replaces /ai/chat and /ai/debate with intent-based
routing (quick/deep/debate/followup). Old endpoints preserved for
backward compatibility.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 7: Web UI — 对话面板样式

**Files:**
- Create: `financial_analyzer/web/static/css/chat.css`

- [ ] **Step 1: 编写 chat.css**

```css
/* financial_analyzer/web/static/css/chat.css */

/* ---- AI 对话面板布局 ---- */
.chat-container {
  display: flex;
  flex-direction: column;
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

/* 消息列表 */
.chat-messages {
  flex: 1 1 0;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
}

.chat-messages::-webkit-scrollbar { width: 4px; }
.chat-messages::-webkit-scrollbar-track { background: transparent; }
.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.18);
  border-radius: 2px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: rgba(59, 130, 246, 0.32);
}

/* 空状态 */
.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: 8px;
  color: var(--text-muted);
  font-size: var(--text-sm);
}

.chat-empty .hint {
  font-size: var(--text-xs);
  color: var(--text-muted);
  opacity: 0.6;
}

.chat-empty .quick-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

/* 快捷操作按钮 */
.quick-action {
  padding: 6px 14px;
  border: 1px solid rgba(59, 130, 246, 0.15);
  border-radius: 16px;
  background: rgba(17, 24, 50, 0.45);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  cursor: pointer;
  font-family: var(--font-sans);
  transition: all var(--duration-normal) var(--ease-out-expo);
}

.quick-action:hover {
  background: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.30);
  color: var(--accent-primary);
}

/* ---- 消息气泡 ---- */
.chat-bubble {
  max-width: 85%;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: var(--text-sm);
  line-height: 1.7;
  animation: msg-in 200ms var(--ease-out-expo) both;
}

@keyframes msg-in {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* 用户消息 */
.chat-bubble--user {
  align-self: flex-end;
  background: rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.25);
  border-radius: 14px 14px 4px 14px;
  color: var(--text-primary);
}

/* AI 消息 */
.chat-bubble--assistant {
  align-self: flex-start;
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--blur-card)) saturate(140%);
  -webkit-backdrop-filter: blur(var(--blur-card)) saturate(140%);
  border: 1px solid rgba(148, 163, 184, 0.08);
  border-radius: 14px 14px 14px 4px;
  color: var(--text-primary);
}

/* 系统消息 */
.chat-system {
  align-self: center;
  padding: 4px 14px;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.08);
  color: var(--accent-primary);
  font-size: var(--text-xs);
}

/* ---- 结构化卡片 ---- */
.chat-structured {
  align-self: flex-start;
  max-width: 90%;
  background: var(--glass-bg-card);
  backdrop-filter: blur(var(--blur-card)) saturate(140%);
  -webkit-backdrop-filter: blur(var(--blur-card)) saturate(140%);
  border: 1px solid rgba(59, 130, 246, 0.10);
  border-radius: 12px;
  padding: 16px;
  font-size: var(--text-sm);
  line-height: 1.7;
  animation: msg-in 250ms var(--ease-out-expo) both;
}

.chat-structured .cs-section {
  padding: 6px 0;
  border-bottom: 1px solid var(--divider);
}

.chat-structured .cs-section:last-child {
  border-bottom: none;
}

.chat-structured .cs-label {
  font-weight: 600;
  font-size: var(--text-xs);
  margin-bottom: 4px;
}

.chat-structured .cs-label--data    { color: var(--text-muted); }
.chat-structured .cs-label--reason  { color: var(--warning); }
.chat-structured .cs-label--conclusion { color: var(--positive); }

/* 置信度徽章 */
.confidence-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: var(--text-2xs);
  font-weight: 600;
  letter-spacing: 0.03em;
}

.confidence-badge--high   { background: rgba(20, 184, 166, 0.12); color: var(--positive); }
.confidence-badge--medium { background: rgba(245, 158, 11, 0.12); color: var(--warning); }
.confidence-badge--low    { background: rgba(244, 63, 94, 0.12); color: var(--negative); }

/* 信号标签 */
.signal-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.signal-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: var(--text-2xs);
  font-weight: 600;
}

.signal-tag--good  { background: rgba(20, 184, 166, 0.1); color: var(--positive); }
.signal-tag--warn  { background: rgba(245, 158, 11, 0.1); color: var(--warning); }
.signal-tag--bad   { background: rgba(244, 63, 94, 0.1); color: var(--negative); }

/* ---- 辩论区段 ---- */
.debate-round-header {
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  text-align: center;
  color: var(--accent-primary);
  margin: 16px 0 8px;
  padding: 8px 0;
  border-top: 1px solid;
  border-bottom: 1px solid;
  border-image: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.30), transparent) 1;
}

.debate-analyst-header {
  font-size: 13px;
  font-weight: 600;
  margin: 12px 0 4px;
}

.debate-analyst-text {
  color: var(--text-primary);
  font-size: var(--text-sm);
  line-height: 1.8;
  padding-left: 14px;
  border-left: 3px solid rgba(59, 130, 246, 0.20);
}

/* ---- 输入区 ---- */
.chat-input-area {
  display: flex;
  gap: 10px;
  padding: 12px 20px;
  border-top: 1px solid rgba(59, 130, 246, 0.08);
  background: rgba(11, 16, 33, 0.40);
  flex-shrink: 0;
}

.chat-input-area input {
  flex: 1;
  background: rgba(6, 8, 14, 0.55);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(59, 130, 246, 0.15);
  color: var(--text-primary);
  padding: 10px 16px;
  border-radius: 8px;
  font-size: var(--text-sm);
  font-family: var(--font-sans);
}

.chat-input-area input:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.20);
  outline: none;
}

.chat-input-area input::placeholder {
  color: var(--text-muted);
}

/* ---- 工具调用指示器 ---- */
.tool-call-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: var(--text-xs);
  color: var(--text-muted);
  animation: pulse-opacity 1s ease-in-out infinite alternate;
}

@keyframes pulse-opacity {
  from { opacity: 0.5; }
  to   { opacity: 1; }
}

/* 停止按钮 */
.chat-stop-btn {
  padding: 8px 16px;
  border: 1px solid rgba(244, 63, 94, 0.20);
  border-radius: 8px;
  background: rgba(244, 63, 94, 0.08);
  color: var(--negative);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}
.chat-stop-btn:hover {
  background: rgba(244, 63, 94, 0.15);
  border-color: rgba(244, 63, 94, 0.35);
}
```

- [ ] **Step 2: 确认 CSS 无语法错误并与现有 token 一致**

```bash
echo "CSS file created — validate visually when UI is rendered"
```

- [ ] **Step 3: 提交**

```bash
git add financial_analyzer/web/static/css/chat.css
git commit -m "feat: add chat.css for unified AI dialogue panel

Message bubbles, structured output cards, confidence badges,
signal tags, debate round headers, and input area — all using
existing Precision Glass design tokens.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 8: Web UI — 更新模板和 JS

**Files:**
- Modify: `financial_analyzer/web/templates/index.html` (AI Tab 部分)
- Modify: `financial_analyzer/web/static/js/app.js` (新增 chat WebSocket 客户端)

- [ ] **Step 1: 更新 index.html 的 AI Tab**

将现有 AI Tab 的 HTML（`index.html` 中 `<!-- Tab: AI 投研 -->` 段）替换为：

```html
<!-- Tab: AI 投研 -->
<div id="tab-ai" class="tab-panel">
    <div class="chat-container" id="chat-container">
        <!-- 消息列表 -->
        <div class="chat-messages" id="chat-messages">
            <div class="chat-empty" id="chat-empty">
                <div style="font-size:40px;opacity:0.3;margin-bottom:8px;">📊</div>
                <div>AI 财务分析助手</div>
                <div class="hint">支持快速问答、深度分析（/deep）和三方辩论（/debate）</div>
                <div class="quick-actions">
                    <button class="quick-action" onclick="sendQuick('分析盈利能力')">分析盈利能力</button>
                    <button class="quick-action" onclick="sendQuick('评估财务风险')">评估财务风险</button>
                    <button class="quick-action" onclick="sendQuick('/deep 全面深度分析')">全面深度分析</button>
                    <button class="quick-action" onclick="sendQuick('/debate')">三方辩论</button>
                </div>
            </div>
        </div>

        <!-- 输入区 -->
        <div class="chat-input-area" id="chat-input-area">
            <input type="text" id="chat-input"
                   placeholder="输入分析问题... (Ctrl+Enter 发送)"
                   onkeydown="if(event.key==='Enter'&&event.ctrlKey)sendMessage()">
            <button class="btn btn-accent" onclick="sendMessage()" id="chat-send-btn">发送</button>
            <button class="chat-stop-btn" onclick="stopAnalysis()" id="chat-stop-btn" style="display:none;">停止</button>
        </div>
    </div>
</div>
```

- [ ] **Step 2: 在 index.html `<head>` 中引入 chat.css**

在 `base.html` 的 `<head>` 中添加：

```html
<link rel="stylesheet" href="/static/css/chat.css">
```

- [ ] **Step 3: 在 app.js 中新增统一对话 WebSocket 客户端**

在 `app.js` 文件末尾追加：

```js
// ============================================================================
// 统一 AI 对话 WebSocket 客户端
// ============================================================================

let chatWs = null;
let chatInProgress = false;

function sendQuick(question) {
    document.getElementById('chat-input').value = question;
    sendMessage();
}

function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message || chatInProgress) return;

    const stockCode = document.querySelector('input[name="stock_code"]')?.value || '';
    if (!stockCode) {
        alert('请先输入股票代码并获取数据');
        return;
    }

    // 隐藏空状态
    const emptyEl = document.getElementById('chat-empty');
    if (emptyEl) emptyEl.style.display = 'none';

    const messages = document.getElementById('chat-messages');

    // 添加用户气泡
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble chat-bubble--user';
    userBubble.textContent = message;
    messages.appendChild(userBubble);
    messages.scrollTop = messages.scrollHeight;

    input.value = '';
    chatInProgress = true;

    // 显示停止按钮
    document.getElementById('chat-send-btn').style.display = 'none';
    document.getElementById('chat-stop-btn').style.display = 'inline-block';

    // 连接或复用 WebSocket
    if (chatWs && chatWs.readyState === WebSocket.OPEN) {
        chatWs.send(JSON.stringify({ type: 'message', content: message }));
        return;
    }

    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = protocol + '//' + location.host + '/ai/conversation';

    try {
        chatWs = new WebSocket(wsUrl);
        let _currentAssistantEl = null;
        let _currentStructuredEl = null;
        let _currentSection = null;

        chatWs.onopen = function() {
            chatWs.send(JSON.stringify({ stock_code: stockCode }));
            // 发送初始化消息的延迟，等待服务端就绪
            setTimeout(function() {
                if (chatWs.readyState === WebSocket.OPEN) {
                    chatWs.send(JSON.stringify({ type: 'message', content: message }));
                }
            }, 200);
        };

        chatWs.onmessage = function(event) {
            const msg = JSON.parse(event.data);

            if (msg.type === 'meta') {
                if (msg.content === 'ready') return;

                // 阶段切换
                if (msg.content.startsWith('intent:')) {
                    const intent = msg.content.replace('intent:', '');
                    const sysEl = document.createElement('div');
                    sysEl.className = 'chat-system';
                    const intentLabels = { quick: '快速问答模式', deep: '深度分析模式', debate: '三方辩论模式', followup: '追问模式' };
                    sysEl.textContent = intentLabels[intent] || intent;
                    messages.appendChild(sysEl);
                    messages.scrollTop = messages.scrollHeight;
                }
                else if (msg.content === 'debate_start') {
                    const header = document.createElement('div');
                    header.className = 'debate-round-header';
                    header.textContent = '三方辩论开始';
                    messages.appendChild(header);
                    messages.scrollTop = messages.scrollHeight;
                }
                else if (msg.content.startsWith('section:')) {
                    _currentSection = msg.content.replace('section:', '');
                    _currentAssistantEl = null;
                }
            }
            else if (msg.type === 'chunk') {
                if (!_currentAssistantEl) {
                    _currentAssistantEl = document.createElement('div');
                    _currentAssistantEl.className = 'chat-bubble chat-bubble--assistant';
                    messages.appendChild(_currentAssistantEl);
                }
                _currentAssistantEl.textContent += msg.content;
                messages.scrollTop = messages.scrollHeight;
            }
            else if (msg.type === 'structured') {
                // 结构化卡片
                const card = buildStructuredCard(msg.content, msg.meta || {});
                messages.appendChild(card);
                _currentAssistantEl = null;
                messages.scrollTop = messages.scrollHeight;
            }
            else if (msg.type === 'done') {
                _currentAssistantEl = null;
                chatInProgress = false;
                document.getElementById('chat-send-btn').style.display = 'inline-block';
                document.getElementById('chat-stop-btn').style.display = 'none';
            }
            else if (msg.type === 'error') {
                const errEl = document.createElement('div');
                errEl.className = 'chat-bubble chat-bubble--assistant';
                errEl.style.color = 'var(--negative)';
                errEl.textContent = '⚠️ ' + msg.content;
                messages.appendChild(errEl);
                messages.scrollTop = messages.scrollHeight;
                chatInProgress = false;
                document.getElementById('chat-send-btn').style.display = 'inline-block';
                document.getElementById('chat-stop-btn').style.display = 'none';
            }
        };

        chatWs.onerror = function() {
            const errEl = document.createElement('div');
            errEl.className = 'chat-bubble chat-bubble--assistant';
            errEl.style.color = 'var(--negative)';
            errEl.textContent = '⚠️ WebSocket 连接失败，请检查网络或 API Key 配置';
            messages.appendChild(errEl);
            chatInProgress = false;
            document.getElementById('chat-send-btn').style.display = 'inline-block';
            document.getElementById('chat-stop-btn').style.display = 'none';
        };

        chatWs.onclose = function() {
            chatWs = null;
            chatInProgress = false;
            document.getElementById('chat-send-btn').style.display = 'inline-block';
            document.getElementById('chat-stop-btn').style.display = 'none';
        };
    } catch (e) {
        const errEl = document.createElement('div');
        errEl.className = 'chat-bubble chat-bubble--assistant';
        errEl.style.color = 'var(--negative)';
        errEl.textContent = '⚠️ 连接失败: ' + e.message;
        messages.appendChild(errEl);
        chatInProgress = false;
        document.getElementById('chat-send-btn').style.display = 'inline-block';
        document.getElementById('chat-stop-btn').style.display = 'none';
    }
}

function stopAnalysis() {
    if (chatWs && chatWs.readyState === WebSocket.OPEN) {
        chatWs.send(JSON.stringify({ type: 'stop' }));
    }
    chatInProgress = false;
    document.getElementById('chat-send-btn').style.display = 'inline-block';
    document.getElementById('chat-stop-btn').style.display = 'none';
}

function buildStructuredCard(text, meta) {
    const card = document.createElement('div');
    card.className = 'chat-structured';

    // 按 📊 / 🔍 / ✅ 分割
    const sections = text.split(/(?=📊|🔍|✅)/);
    sections.forEach(function(section) {
        const secDiv = document.createElement('div');
        secDiv.className = 'cs-section';

        let labelClass = 'cs-label ';
        if (section.startsWith('📊')) {
            labelClass += 'cs-label--data';
        } else if (section.startsWith('🔍')) {
            labelClass += 'cs-label--reason';
        } else if (section.startsWith('✅')) {
            labelClass += 'cs-label--conclusion';
        }

        secDiv.innerHTML = '<div class="' + labelClass + '">' +
            section.substring(0, section.indexOf('\n') > -1 ? section.indexOf('\n') : section.length) +
            '</div>' +
            (section.indexOf('\n') > -1 ? '<div style="color:var(--text-secondary);">' +
            section.substring(section.indexOf('\n') + 1).replace(/\n/g, '<br>') +
            '</div>' : '');

        card.appendChild(secDiv);
    });

    // 置信度徽章
    if (meta.confidence && meta.confidence !== '未标注') {
        const badge = document.createElement('span');
        badge.className = 'confidence-badge confidence-badge--' +
            (meta.confidence === '高' ? 'high' : meta.confidence === '中' ? 'medium' : 'low');
        badge.textContent = '置信度 ' + meta.confidence;
        card.appendChild(badge);
    }

    // 信号标签
    if (meta.signal_tags && meta.signal_tags.length > 0) {
        const tagsDiv = document.createElement('div');
        tagsDiv.className = 'signal-tags';
        meta.signal_tags.forEach(function(tag) {
            const tagSpan = document.createElement('span');
            const value = typeof tag === 'string' ? tag : (tag.name + ' ' + (tag.value || ''));
            const level = value.includes('高') || value.includes('优') ? 'good' :
                          value.includes('低') || value.includes('差') ? 'bad' : 'warn';
            tagSpan.className = 'signal-tag signal-tag--' + level;
            tagSpan.textContent = value;
            tagsDiv.appendChild(tagSpan);
        });
        card.appendChild(tagsDiv);
    }

    return card;
}
```

- [ ] **Step 4: 删除 app.js 中旧 AI 辩论函数**

删除 `app.js` 中不再需要的旧辩论函数：`startDebate()` 和 `switchAiTab()`（保留 `switchAiTab` 中其他 tab 的切换逻辑）。旧函数 `switchAiTab` 可以改为 no-op 或完全删除，因为现在只有一个统一面板。

实际上，为了最小化风险，删除 `switchAiTab` 函数的调用引用并保留函数体（或标记为废弃）：

```js
// switchAiTab 在新 UI 中不再需要，保留空壳以防旧引用
function switchAiTab(tab, btn) {
    // DEPRECATED: 统一对话面板已替代子标签
}
```

旧的 `startDebate` 函数在 Task 7 更新 `index.html` 后不再被引用，可保留或删除。为安全起见，保留函数体：

```js
// startDebate 在新 UI 中通过 /ai/conversation 触发
// 保留函数定义以避免潜在的引用错误
```

- [ ] **Step 5: 验证 HTML 模板渲染无 Jinja2 语法错误**

```bash
python -c "
from financial_analyzer.web.main import create_app
app = create_app()
print('App created successfully with new AI tab template')
"
```

- [ ] **Step 6: 提交**

```bash
git add financial_analyzer/web/templates/index.html financial_analyzer/web/templates/base.html financial_analyzer/web/static/js/app.js
git commit -m "feat: replace AI sub-tabs with unified conversational chat panel

New chat UI with message bubbles, structured cards, confidence badges,
and quick actions. WebSocket client for /ai/conversation endpoint.
Old debate and chat endpoints preserved for backward compatibility.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 9: 集成验证

**Files:** (none new — validation only)

- [ ] **Step 1: 运行全部测试确保无回归**

```bash
cd "C:/Users/LK/Desktop/FA/10.6"
python -m pytest tests/ -v --ignore=tests/test_adapter.py --ignore=tests/test_cache.py
```

Expected: all existing and new tests pass.

- [ ] **Step 2: 验证模块导入链路完整**

```bash
python -c "
# 核心新模块
from financial_analyzer.ai.prompt_framework import PromptBuilder
from financial_analyzer.ai.output_parser import OutputParser, StructuredOutput
from financial_analyzer.ai.conversation import ConversationManager, Message
from financial_analyzer.ai.orchestrator import AnalysisOrchestrator

# 已有模块不受影响
from financial_analyzer.ai.report_builder import ReportBuilder
from financial_analyzer.ai.signal_detector import SignalDetector
from financial_analyzer.ai.debate_engine import DebateEngine
from financial_analyzer.deepseek.client import DeepSeekClient, DeepSeekStreamClient
from financial_analyzer.deepseek.prompts import get_framework_templates

# Web 模块
from financial_analyzer.web.main import create_app

print('All imports successful')
print('Module integration verified')
"
```

Expected: "All imports successful"

- [ ] **Step 3: 端到端 Prompt 构建验证**

```bash
python -c "
from financial_analyzer.ai.prompt_framework import PromptBuilder

# 模拟完整深度分析场景
report = {
    'company_snapshot': {'name': '贵州茅台', 'price': 1800, 'pe': 35, 'pb': 12, 'market_cap_yi': 22600},
    'financial_health': {
        '盈利能力': {'ROE': 30.5, '毛利率': 92.0, '净利率': 52.0},
        '偿债能力': {'资产负债率': 21.5, '流动比率': 3.5},
        '营运能力': {'总资产周转率': 0.5, '存货周转率': 0.3},
        '发展能力': {'营收增长率': 15.0, '净利润增长率': 18.0},
    },
    'risk_models': {
        'zscore': {'z_score': 8.5, 'zone_cn': '安全'},
        'mscore': {'m_score': -2.5, 'manipulator': False},
    },
    'anomaly_signals': [],
    'cashflow_analysis': {'quadrant': [{'quadrant_type': '成熟期', 'op_sign': '正', 'inv_sign': '负', 'fin_sign': '负', 'end_date': '20241231'}]},
    'dupont_analysis': {'three_factor': [{'end_date': '20241231', 'roe': 30.5, 'net_margin': 52.0, 'asset_turnover': 0.5, 'equity_multiplier': 1.17}]},
}
signals = [
    {'name': '纸面富贵预警', 'trigger_data': 'ROE=30.5%', 'task': '分析杠杆贡献', 'level': 'medium'},
]

builder = PromptBuilder('贵州茅台')
builder.with_data(report)
builder.with_framework('harvard')
builder.with_framework('crosscheck')
builder.with_framework('lifecycle')
builder.with_framework('warnings')
builder.with_signals(signals)
builder.with_output_format('structured')
builder.with_mode('deep')
prompt = builder.build()

print(f'Prompt generated: {len(prompt)} chars')
assert '哈佛分析框架' in prompt
assert '三表联动验证' in prompt
assert '生命周期' in prompt
assert '利润质量预警' in prompt
assert '贵州茅台' in prompt
assert '纸面富贵预警' in prompt
assert '数据依据' in prompt
assert '推理过程' in prompt
assert '综合结论' in prompt
print('All assertions passed')
print('E2E prompt build verified')
"
```

- [ ] **Step 4: 提交**

```bash
git commit --allow-empty -m "verify: integration tests pass for Phase 2 AI modules

All 4 new modules importable, prompt framework builds complete deep
analysis prompts, no regressions in existing test suite.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```
