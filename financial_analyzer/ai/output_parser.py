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
    confidence: str = "未标注"
    signal_tags: list[dict] = field(default_factory=list)
    raw_text: str = ""


class OutputParser:
    """流式结构化输出解析器"""

    CONFIDENCE_PATTERNS = {
        "high": [r"置信度[：:]\s*高", r"置信度[：:]\s*强"],
        "medium": [r"置信度[：:]\s*中", r"置信度[：:]\s*一般"],
        "low": [r"置信度[：:]\s*低", r"置信度[：:]\s*弱", r"置信度[：:]\s*差"],
    }

    SIGNAL_TAG_PATTERN = re.compile(
        r"(现金流质量|盈余质量|资产质量|增长可持续性|财务风险|估值合理性|信用政策|存货风险|商誉风险)"
        r"\s*(\d{1,3}/\d{1,3}|优|良|中|差|偏高|偏低|正常|关注|危险)?"
    )

    SECTION_MARKERS = {
        "data": re.compile(r"📊\s*数据依据"),
        "reasoning": re.compile(r"🔍\s*推理过程"),
        "conclusion": re.compile(r"✅\s*综合结论"),
    }

    def __init__(self):
        self._buffer = ""
        self._current_section: str | None = None
        self._events: list[dict] = []
        self._last_idx = 0

    def feed(self, chunk: str) -> list[dict]:
        """喂入一个文本块，返回事件列表"""
        if not chunk:
            return []

        self._buffer += chunk
        self._events.append({"type": "chunk", "content": chunk})

        # 检测区段切换
        for section_name, pattern in self.SECTION_MARKERS.items():
            if pattern.search(self._buffer) and self._current_section != section_name:
                self._current_section = section_name
                self._events.append({
                    "type": "meta",
                    "content": f"section:{section_name}",
                })
                break

        new_events = self._events[self._last_idx:]
        self._last_idx = len(self._events)
        return new_events

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
        self._events = []
        self._last_idx = 0

        return result
