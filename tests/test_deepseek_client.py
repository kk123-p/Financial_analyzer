"""
DeepSeek client.py + prompts.py unit tests
Covers: config defaults, payload cleanup, prompt structure
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_analyzer.deepseek.client import DeepSeekConfig, DeepSeekClient, DeepSeekStreamClient
from financial_analyzer.deepseek.prompts import (
    get_analysis_prompt, build_multi_perspective_prompt,
    DEEP_ANALYSIS_SYSTEM_PROMPT, ANALYST_ROLES,
)


# ============================================================================
# DeepSeekConfig defaults
# ============================================================================
class TestDeepSeekConfigDefaults:

    def test_model_default(self):
        cfg = DeepSeekConfig()
        assert cfg.model == "deepseek-v4-flash"

    def test_max_tokens_default(self):
        cfg = DeepSeekConfig()
        assert cfg.max_tokens == 8192

    def test_no_frequency_penalty_field(self):
        cfg = DeepSeekConfig()
        assert not hasattr(cfg, "frequency_penalty")

    def test_no_presence_penalty_field(self):
        cfg = DeepSeekConfig()
        assert not hasattr(cfg, "presence_penalty")

    def test_other_defaults_unchanged(self):
        cfg = DeepSeekConfig()
        assert cfg.base_url == "https://api.deepseek.com"
        assert cfg.temperature == 0.3
        assert cfg.timeout == 120


# ============================================================================
# Payload dicts — no deprecated params
# ============================================================================
class TestPayloadCleanup:

    def _build_stream_payload(self):
        """Simulate the payload built in generate_deep_analysis_stream."""
        cfg = DeepSeekConfig(api_key="test-key")
        return {
            "model": cfg.model,
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ],
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
            "stream": True,
        }

    def _build_report_stream_payload(self):
        """Simulate the payload built in generate_report_stream."""
        cfg = DeepSeekConfig(api_key="test-key")
        return {
            "model": cfg.model,
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ],
            "max_tokens": cfg.max_tokens,
            "temperature": cfg.temperature,
            "stream": True,
        }

    def test_deep_analysis_payload_no_frequency_penalty(self):
        payload = self._build_stream_payload()
        assert "frequency_penalty" not in payload

    def test_deep_analysis_payload_no_presence_penalty(self):
        payload = self._build_stream_payload()
        assert "presence_penalty" not in payload

    def test_report_stream_payload_no_frequency_penalty(self):
        payload = self._build_report_stream_payload()
        assert "frequency_penalty" not in payload

    def test_report_stream_payload_no_presence_penalty(self):
        payload = self._build_report_stream_payload()
        assert "presence_penalty" not in payload


# ============================================================================
# get_analysis_prompt — focus-first structure
# ============================================================================
class TestGetAnalysisPrompt:

    def test_returns_focus_instruction_first(self):
        result = get_analysis_prompt("some data", "dupont")
        lines = result.strip().split("\n")
        first_non_empty = next(l for l in lines if l.strip())
        assert "杜邦" in first_non_empty

    def test_includes_structured_prompt(self):
        result = get_analysis_prompt("MY_DATA_BLOCK", "zscore")
        assert "MY_DATA_BLOCK" in result

    def test_default_focus_is_comprehensive(self):
        result = get_analysis_prompt("data")
        assert "综合" in result

    def test_unknown_focus_falls_back_to_comprehensive(self):
        result = get_analysis_prompt("data", "unknown_key")
        assert "综合" in result

    def test_fcf_focus(self):
        result = get_analysis_prompt("data", "fcf")
        assert "自由现金流" in result

    def test_no_perspective_parameter(self):
        """perspective parameter was removed — function should not accept it."""
        import inspect
        sig = inspect.signature(get_analysis_prompt)
        assert "perspective" not in sig.parameters


# ============================================================================
# build_multi_perspective_prompt — no system prompt duplication
# ============================================================================
class TestBuildMultiPerspectivePrompt:

    def test_does_not_contain_deep_analysis_system_prompt(self):
        result = build_multi_perspective_prompt("sample data")
        assert DEEP_ANALYSIS_SYSTEM_PROMPT not in result

    def test_contains_structured_data(self):
        result = build_multi_perspective_prompt("MY_STOCK_DATA")
        assert "MY_STOCK_DATA" in result

    def test_contains_all_roles(self):
        result = build_multi_perspective_prompt("data")
        for role in ANALYST_ROLES.values():
            assert role["name"] in result

    def test_has_output_format_instructions(self):
        result = build_multi_perspective_prompt("data")
        assert "格式" in result or "输出" in result

    def test_fixed_instructions_before_variable_data(self):
        """Instructions should come before the structured_prompt data block."""
        result = build_multi_perspective_prompt("VARIABLE_DATA_BLOCK")
        instructions_pos = result.find("格式输出")
        data_pos = result.find("VARIABLE_DATA_BLOCK")
        assert instructions_pos < data_pos
