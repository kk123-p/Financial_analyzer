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
        events1 = parser.feed("第一段")
        events2 = parser.feed("续接文本")
        events3 = parser.feed("最后一段")

        # 每次 feed 只返回本次新增事件
        assert len(events1) == 1
        assert events1[0]["content"] == "第一段"
        assert len(events2) == 1
        assert events2[0]["content"] == "续接文本"
        assert len(events3) == 1
        assert events3[0]["content"] == "最后一段"


class TestOutputParserStructured:
    def test_detect_data_section(self):
        """检测到 📊 数据依据 标记时推送 chunk"""
        parser = OutputParser()
        chunk = "📊 数据依据\n- ROE: 20% [2024年报]\n- 毛利率: 92%"
        events = parser.feed(chunk)

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
        """不完整标记不产出 structured 事件"""
        parser = OutputParser()
        events = parser.feed("这是一个📊字符，可能不是标记")
        types = [e["type"] for e in events]
        assert "structured" not in types

    def test_finalize_resets_state(self):
        parser = OutputParser()
        parser.feed("📊 数据\n置信度: 高")
        parser.finalize()
        parser.feed("新的对话")
        result = parser.finalize()
        assert result.raw_text == "新的对话"
