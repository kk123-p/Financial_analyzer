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


class TestAnalysisOrchestratorIntent:
    def test_identify_quick_intent(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        assert orchestrator._identify_intent("贵州茅台的PE是多少？") == "quick"

    def test_identify_deep_intent_via_command(self):
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
            "综合分析财务数据",
            "全面分析",
        ]
        for phrase in deep_phrases:
            assert orchestrator._identify_intent(phrase) == "deep", f"Failed: {phrase}"

    def test_followup_with_context(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        conv = ConversationManager()
        conv.add_message(Message(role="assistant", content="盈利能力分析完成，ROE=30%...", msg_type="structured"))
        intent = orchestrator._identify_intent("为什么ROE这么高？", conversation=conv)
        assert intent == "followup"

    def test_followup_without_context_is_quick(self):
        """无历史上下文的短问题应识别为 quick"""
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        conv = ConversationManager()
        intent = orchestrator._identify_intent("PE是多少？", conversation=conv)
        assert intent == "quick"

    def test_debate_keyword_triggers(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        assert orchestrator._identify_intent("来个三方辩论") == "debate"


class TestAnalysisOrchestratorBuildPrompt:
    def test_build_system_context_quick_mode(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        data = {"company_snapshot": {"name": "测试"}}
        context = orchestrator._build_system_context("quick", data, None, [])
        assert "测试" in context
        # 用户问题不应出现在系统上下文中
        assert "测试问题" not in context

    def test_build_system_context_deep_mode_includes_frameworks(self):
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
        context = orchestrator._build_system_context("deep", data, None, signals)
        assert "哈佛分析框架" in context
        assert "三表联动验证" in context
        assert "生命周期" in context
        assert "利润质量恶化预警" in context
        assert "纸面富贵预警" in context
        assert "数据依据" in context
        # 用户问题不应出现在系统上下文中 (不会有"## 用户问题"标题)
        assert "## 用户问题" not in context


class TestAnalysisOrchestratorAnalyze:
    def test_analyze_quick_streams_response(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        conversation = ConversationManager()
        data = {"company_snapshot": {"name": "测试"}}

        events = []
        def callback(event_type, content, meta):
            events.append((event_type, content, meta))

        orchestrator.analyze(
            user_message="PE是多少？",
            conversation=conversation,
            data=data,
            stock_code="000001.SZ",
            company_name="测试公司",
            callback=callback,
        )

        # Should have received chunk events
        assert any(e[0] == "chunk" for e in events)
        # Should have received done event
        assert events[-1][0] == "done"

    def test_analyze_adds_user_message_to_conversation(self):
        orchestrator = AnalysisOrchestrator(llm_client=FakeLLMClient())
        conversation = ConversationManager()
        data = {"company_snapshot": {"name": "测试"}}

        orchestrator.analyze(
            user_message="PE是多少？",
            conversation=conversation,
            data=data,
            stock_code="000001.SZ",
            callback=lambda *a: None,
        )

        ctx = conversation.get_context()
        assert len(ctx) >= 1
        assert ctx[0].role == "user"
        assert ctx[0].content == "PE是多少？"

    def test_analyze_error_handling(self):
        """LLM 返回失败时不应崩溃"""
        class FailingClient(FakeLLMClient):
            def generate_deep_analysis_stream(self, prompt, system_prompt=None, callback=None):
                from financial_analyzer.deepseek.client import AnalysisReport
                report = AnalysisReport()
                report.success = False
                report.error = "模拟错误"
                return report

        orchestrator = AnalysisOrchestrator(llm_client=FailingClient())
        conversation = ConversationManager()
        data = {"company_snapshot": {"name": "测试"}}

        events = []
        def callback(event_type, content, meta):
            events.append((event_type, content))

        orchestrator.analyze(
            user_message="PE是多少？",
            conversation=conversation,
            data=data,
            stock_code="000001.SZ",
            callback=callback,
        )

        assert any(e[0] == "error" for e in events)
