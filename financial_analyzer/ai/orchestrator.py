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
        """统一分析入口"""
        conversation.add_message(Message(role="user", content=user_message, msg_type="text"))

        intent = self._identify_intent(user_message, conversation)

        # Always build report for data context (all modes need it)
        report = None
        signals = []
        try:
            report = ReportBuilder.build(data, stock_code)
            if intent in ("deep", "debate"):
                signals = SignalDetector.detect(report)
        except Exception as e:
            logger.warning(f"Report building failed: {e}")

        if callback:
            callback("meta", f"intent:{intent}", None)

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

        if msg_lower.startswith("/debate"):
            return "debate"
        if msg_lower.startswith("/deep"):
            return "deep"

        for kw in DEBATE_KEYWORDS:
            if kw in message:
                return "debate"

        for kw in DEEP_KEYWORDS:
            if kw in message:
                return "deep"

        if conversation and conversation.message_count >= 1:
            last_assistant = conversation.get_last_assistant_message()
            if last_assistant and len(message) < 50:
                return "followup"

        return "quick"

    def _build_prompt(self, intent: str, message: str, data: dict | None,
                      report: dict | None, signals: list | None) -> str:
        """构建提示词"""
        builder = PromptBuilder()
        company_name = report.get("company_snapshot", {}).get("name", "") if report else ""

        if intent == "quick":
            builder.with_mode("quick")
            builder.with_question(message)
            if report:
                builder.with_data(report)
            elif data:
                builder.with_data(data)
        elif intent == "deep":
            builder.with_mode("deep")
            builder.with_question(message)
            if report:
                builder.with_data(report)
            elif data:
                builder.with_data(data)
            builder.with_framework("harvard")
            builder.with_framework("crosscheck")
            builder.with_framework("lifecycle")
            builder.with_framework("warnings")
            builder.with_output_format("structured")
            if signals:
                builder.with_signals(signals)
        elif intent == "followup":
            builder.with_mode("followup")
            builder.with_question(message)
            if report:
                builder.with_data(report)
            elif data:
                builder.with_data(data)
        elif intent == "debate":
            builder.with_mode("debate")
            builder.with_question(message)
            if report:
                builder.with_data(report)
            elif data:
                builder.with_data(data)

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
                    callback("chunk", result.raw_text, None)
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
                callback("done", "", None)

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
                    callback("chunk", result.raw_text, None)
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
                callback("done", "", None)

    def _stream_followup(self, data, report, signals, message, conversation, callback):
        """追问模式：注入历史上下文"""
        context = conversation.get_all_assistant_content()
        prompt = self._build_prompt("followup", message, data, report, signals)

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
                callback("done", "", None)

    def _stream_debate(self, data, stock_code, company_name, conversation, callback):
        """辩论模式：委托 DebateEngine"""
        if not self._debate_factory:
            if callback:
                callback("error", "辩论引擎不可用", None)
                callback("done", "", None)
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
                callback("done", "", None)
