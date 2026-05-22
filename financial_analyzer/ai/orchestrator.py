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
from .output_parser import OutputParser

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
        cancel_event=None,
    ):
        """统一分析入口 — 所有模式行为一致，LLM 纯问答"""
        conversation.add_message(Message(role="user", content=user_message, msg_type="text"))

        intent = self._identify_intent(user_message, conversation)

        if callback:
            callback("meta", f"intent:{intent}", None)

        if intent == "debate" and self._debate_factory:
            self._stream_debate(data, stock_code, company_name, conversation, callback)
        elif intent == "template":
            template = getattr(conversation, '_active_template', None)
            if template:
                self._stream_template(template, data, stock_code, company_name,
                                     conversation, callback, cancel_event=cancel_event)
            else:
                if callback:
                    callback("error", "未选择分析模板", None)
                    callback("done", "", None)
        else:
            self._stream_chat(user_message, conversation, callback, data, stock_code, company_name, cancel_event=cancel_event)

    def _identify_intent(self, message: str, conversation: ConversationManager | None = None) -> str:
        """识别用户分析意图"""
        msg_lower = message.strip().lower()

        # Template intent: conversation has active_template set by WebSocket handler
        if conversation and getattr(conversation, '_active_template', None):
            return "template"

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

    def _stream_chat(self, message, conversation, callback, data=None, stock_code="", company_name="", cancel_event=None):
        """纯问答模式 — 仅在问题涉及当前股票数据时注入摘要"""
        system_prompt = ""
        user_prompt = message

        if data and self._is_data_question(message, stock_code, company_name):
            from .templates import build_lightweight_summary
            system_prompt = build_lightweight_summary(data, stock_code)
            if len(message.strip()) < 10:
                user_prompt = f"请针对以上数据，用专业简洁的中文回答以下问题：{message}"
        elif data:
            # 通用问题：不注入数据，只给一个简短角色提示
            system_prompt = "你是一个专业的财务分析助手。请用简洁、专业的中文回答用户问题。"
            user_prompt = message

    @staticmethod
    def _is_data_question(message: str, stock_code: str, company_name: str) -> bool:
        """判断用户问题是否需要引用当前股票数据"""
        msg = message.strip()
        # 股票引用词：问题明确指向当前分析的股票
        stock_refs = [stock_code, company_name, "这只", "这个股票", "该公司", "这家", "当前",
                      "它的", "他的", "它", "他"]
        if any(r in msg for r in stock_refs if r):
            return True
        # 财务指标词：问题涉及具体财务数据
        finance_terms = [
            "毛利率", "净利率", "ROE", "ROA", "PE", "PB", "市盈率", "市净率",
            "营收", "净利润", "利润", "负债", "资产", "现金流", "分红", "股息",
            "增长率", "同比", "环比", "趋势", "报表", "财报", "财务",
            "主力", "资金", "融资", "融券", "北向", "股东", "估值",
            "杜邦", "周转", "杠杆", "偿债", "营运", "盈利", "成本",
        ]
        if any(t in msg for t in finance_terms):
            return True
        return False

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

        result = self._llm.generate_deep_analysis_stream(
            user_prompt, system_prompt=system_prompt, callback=on_chunk,
            cancel_event=cancel_event,
        )
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

    def _stream_template(self, template: dict, data: dict, stock_code: str,
                         company_name: str, conversation, callback,
                         extra_question: str = "", cancel_event=None):
        """模板驱动分析 — 按 section 流式输出"""
        from .templates import get_template_data_summary

        if callback:
            sections = template.get("analysis_sections", [])
            callback("meta", "template_start", {
                "template": template["name"],
                "sections": len(sections),
            })

        # 1. 提取并格式化数据
        data_text = get_template_data_summary(data, stock_code, template)

        # 2. 组装 sections 指引
        sections_text = "\n".join([
            f"## {s['title']}\n{s['guidance']}"
            for s in template.get("analysis_sections", [])
        ])

        # 3. 组装 prompt
        system_prompt = template.get("system_role", "")
        user_prompt = f"""## 分析任务
对 {company_name} ({stock_code}) 执行「{template["name"]}」分析。

## 分析框架（严格按每个 ## 标题输出）
{sections_text}

## 当前数据
{data_text}"""

        if extra_question:
            user_prompt += f"\n\n## 用户补充问题\n{extra_question}"

        user_prompt += "\n\n请逐段分析，每个 ## 标题作为一个独立的分析段落。"

        # 4. 流式输出并检测 section 边界
        accumulated = ""
        current_section_idx = -1

        def on_chunk(chunk: str, done: bool):
            nonlocal accumulated, current_section_idx

            if chunk:
                accumulated += chunk

            # 检测 section 边界（## 开头的行）
            lines = accumulated.split("\n")
            section_count = sum(1 for l in lines if l.strip().startswith("## "))

            if section_count > current_section_idx + 1:
                current_section_idx += 1
                section_content = self._extract_section(accumulated, current_section_idx)
                if section_content and callback:
                    sections_list = template.get("analysis_sections", [])
                    section_title = sections_list[current_section_idx]["title"] \
                        if current_section_idx < len(sections_list) else ""
                    callback("template_section", section_content.strip(), {
                        "section_index": current_section_idx,
                        "section_title": section_title,
                    })

            if done:
                # 发送剩余未检测到的 section
                total_sections = len(template.get("analysis_sections", []))
                if current_section_idx < total_sections - 1:
                    for idx in range(current_section_idx + 1, total_sections):
                        remaining = self._extract_section(accumulated, idx)
                        if remaining and remaining.strip():
                            sections_list = template.get("analysis_sections", [])
                            section_title = sections_list[idx]["title"] if idx < len(sections_list) else ""
                            if callback:
                                callback("template_section", remaining.strip(), {
                                    "section_index": idx,
                                    "section_title": section_title,
                                })

                if callback:
                    callback("template_done", accumulated, None)
                    callback("done", "", None)

                conversation.add_message(Message(
                    role="assistant",
                    content=accumulated,
                    msg_type="template",
                    metadata={"template": template.get("name"), "stock_code": stock_code},
                ))

        result = self._llm.generate_deep_analysis_stream(
            user_prompt,
            system_prompt=system_prompt,
            callback=on_chunk,
            cancel_event=cancel_event,
        )

        if not result.success:
            if callback:
                callback("error", result.error or "分析失败", None)
                callback("done", "", None)

    @staticmethod
    def _extract_section(text: str, section_idx: int) -> str:
        """从累加文本中提取指定索引的 section 内容"""
        lines = text.split("\n")
        sections = []
        current = []
        for line in lines:
            if line.strip().startswith("## ") and current:
                sections.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            sections.append("\n".join(current))

        if section_idx < len(sections):
            return sections[section_idx]
        return ""
