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
    msg_type: str = "text"
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class ConversationManager:
    """多轮对话上下文管理器"""

    def __init__(self, max_history: int = 50):
        self._messages: list[Message] = []
        self._max_history = max_history
        self._active_template: dict | None = None
        self._system_message: Message | None = None

    def add_message(self, msg: Message):
        """添加一条消息"""
        if msg.role == "system":
            self._system_message = msg
            return
        self._messages.append(msg)
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
