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

    def test_message_count(self):
        cm = ConversationManager()
        cm.add_message(Message(role="user", content="q1", msg_type="text"))
        cm.add_message(Message(role="assistant", content="a1", msg_type="text"))
        assert cm.message_count == 2

    def test_get_last_assistant_message(self):
        cm = ConversationManager()
        cm.add_message(Message(role="user", content="q1", msg_type="text"))
        cm.add_message(Message(role="assistant", content="a1", msg_type="text"))
        cm.add_message(Message(role="user", content="q2", msg_type="text"))

        last = cm.get_last_assistant_message()
        assert last is not None
        assert last.content == "a1"

    def test_get_all_assistant_content(self):
        cm = ConversationManager()
        cm.add_message(Message(role="assistant", content="分析1", msg_type="text"))
        cm.add_message(Message(role="user", content="追问", msg_type="text"))
        cm.add_message(Message(role="assistant", content="分析2", msg_type="text"))

        all_content = cm.get_all_assistant_content()
        assert "分析1" in all_content
        assert "分析2" in all_content
