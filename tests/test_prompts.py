import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_analyzer.deepseek.prompts import (
    ANALYST_ROLES,
    build_debate_round1,
    build_debate_round2,
    build_debate_round3,
    get_analyst_roles,
)


# ============================================================================
# Task 1: 增强后的分析师 system_prompt 测试
# ============================================================================

class TestAnalystRoleEnhancement:
    """验证三位分析师的 system_prompt 包含增强内容"""

    @pytest.mark.parametrize("role_key", ["value", "growth", "risk"])
    def test_system_prompt_contains_thinking_framework(self, role_key):
        """每位分析师的 system_prompt 包含思维框架"""
        role = ANALYST_ROLES[role_key]
        prompt = role["system_prompt"]
        assert "思维框架" in prompt, f"{role_key} analyst missing thinking framework"

    @pytest.mark.parametrize("role_key", ["value", "growth", "risk"])
    def test_system_prompt_contains_citation_standard(self, role_key):
        """每位分析师的 system_prompt 包含引用规范"""
        role = ANALYST_ROLES[role_key]
        prompt = role["system_prompt"]
        assert "引用规范" in prompt, f"{role_key} analyst missing citation standard"

    @pytest.mark.parametrize("role_key", ["value", "growth", "risk"])
    def test_system_prompt_contains_self_questioning(self, role_key):
        """每位分析师的 system_prompt 包含自我质疑清单"""
        role = ANALYST_ROLES[role_key]
        prompt = role["system_prompt"]
        assert "自我质疑" in prompt, f"{role_key} analyst missing self-questioning"

    @pytest.mark.parametrize("role_key", ["value", "growth", "risk"])
    def test_system_prompt_contains_tool_guidance(self, role_key):
        """每位分析师的 system_prompt 包含工具使用指引"""
        role = ANALYST_ROLES[role_key]
        prompt = role["system_prompt"]
        assert "get_financial_metric" in prompt, f"{role_key} analyst missing tool guidance"
        assert "get_historical_trend" in prompt, f"{role_key} analyst missing tool guidance"

    @pytest.mark.parametrize("role_key", ["value", "growth", "risk"])
    def test_system_prompt_preserves_original_traits(self, role_key):
        """增强后的 system_prompt 保留了原有角色特质"""
        role = ANALYST_ROLES[role_key]
        prompt = role["system_prompt"]
        if role_key == "value":
            assert "格雷厄姆" in prompt
            assert "安全边际" in prompt
        elif role_key == "growth":
            assert "费雪" in prompt
            assert "成长" in prompt
        elif role_key == "risk":
            assert "塔勒布" in prompt
            assert "尾部风险" in prompt

    @pytest.mark.parametrize("role_key", ["value", "growth", "risk"])
    def test_system_prompt_contains_example_citation(self, role_key):
        """每位分析师的 system_prompt 包含引用示例"""
        role = ANALYST_ROLES[role_key]
        prompt = role["system_prompt"]
        assert "（" in prompt and "）" in prompt, f"{role_key} analyst missing citation example"


# ============================================================================
# Task 2: 辩论第一轮提示词测试
# ============================================================================

class TestDebateRound1:
    """验证增强后的辩论第一轮提示词"""

    def test_round1_with_role_key_contains_tool_guidance(self):
        """build_debate_round1 输出包含工具使用指引"""
        result = build_debate_round1(
            structured_prompt="测试数据",
            role_key="value",
        )
        assert "get_financial_metric" in result
        assert "get_historical_trend" in result

    def test_round1_with_role_key_contains_output_structure(self):
        """build_debate_round1 输出包含要求的结构"""
        result = build_debate_round1(
            structured_prompt="测试数据",
            role_key="growth",
        )
        assert "核心判断" in result
        assert "关键数据点" in result
        assert "风险点" in result
        assert "估值区间" in result

    def test_round1_with_role_key_contains_fact_inference_tags(self):
        """build_debate_round1 输出要求标注事实和推断"""
        result = build_debate_round1(
            structured_prompt="测试数据",
            role_key="risk",
        )
        assert "[事实]" in result or "[推断]" in result

    def test_round1_without_role_key_contains_tool_guidance(self):
        """通用版本也包含工具使用指引"""
        result = build_debate_round1(structured_prompt="测试数据")
        assert "get_financial_metric" in result
        assert "get_historical_trend" in result

    def test_round1_includes_system_prompt(self):
        """build_debate_round1 将 system_prompt 嵌入输出"""
        result = build_debate_round1(
            structured_prompt="测试数据",
            role_key="value",
        )
        assert "格雷厄姆" in result

    def test_round1_includes_tasks(self):
        """build_debate_round1 将专属任务嵌入输出"""
        result = build_debate_round1(
            structured_prompt="测试数据",
            role_key="value",
        )
        assert "清算价值" in result


# ============================================================================
# Task 3: 辩论第二轮提示词测试
# ============================================================================

class TestDebateRound2:
    """验证增强后的辩论第二轮提示词"""

    def test_round2_requires_specific_data_citation(self):
        """build_debate_round2 输出要求引用对方具体数据点"""
        result = build_debate_round2(round1_statements="测试陈述")
        assert "引用" in result or "具体数据" in result

    def test_round2_prohibits_vague_rebuttals(self):
        """build_debate_round2 输出禁止泛泛而谈"""
        result = build_debate_round2(round1_statements="测试陈述")
        assert "不允许泛泛而谈" in result or "不允许空泛" in result

    def test_round2_requires_acknowledgment(self):
        """build_debate_round2 输出要求承认合理点"""
        result = build_debate_round2(round1_statements="测试陈述")
        assert "承认" in result

    def test_round2_requires_overlooked_risks(self):
        """build_debate_round2 输出要求指出被忽略的风险"""
        result = build_debate_round2(round1_statements="测试陈述")
        assert "忽略" in result

    def test_round2_with_dict_input(self):
        """build_debate_round2 支持 dict 输入"""
        statements = {
            "value": "价值分析师观点",
            "growth": "成长分析师观点",
            "risk": "风控师观点",
        }
        result = build_debate_round2(round1_statements=statements)
        assert "价值分析师" in result or "格雷厄姆" in result
        assert "成长分析师" in result or "费雪" in result

    def test_round2_output_structure(self):
        """build_debate_round2 输出包含三部分结构"""
        result = build_debate_round2(round1_statements="测试陈述")
        assert "具体质疑" in result
        assert "合理点" in result
        assert "忽略的风险" in result


# ============================================================================
# Task 4: 辩论第三轮提示词测试
# ============================================================================

class TestDebateRound3:
    """验证增强后的辩论第三轮提示词"""

    def test_round3_contains_consensus_confidence_table(self):
        """build_debate_round3 输出包含共识置信度表"""
        result = build_debate_round3(debate_history="测试历史")
        assert "一致性" in result
        assert "高" in result
        assert "中" in result
        assert "低" in result

    def test_round3_preserves_scenario_matrix(self):
        """build_debate_round3 保留情景概率矩阵"""
        result = build_debate_round3(debate_history="测试历史")
        assert "情景概率矩阵" in result
        assert "乐观" in result
        assert "中性" in result
        assert "悲观" in result

    def test_round3_contains_key_data_summary(self):
        """build_debate_round3 包含关键数据引用汇总"""
        result = build_debate_round3(debate_history="测试历史")
        assert "关键数据引用汇总" in result
        assert "引用来源" in result or "引用者" in result

    def test_round3_preserves_final_summary(self):
        """build_debate_round3 保留最终摘要"""
        result = build_debate_round3(debate_history="测试历史")
        assert "最终摘要" in result

    def test_round3_preserves_risk_alert(self):
        """build_debate_round3 保留关键风险提示"""
        result = build_debate_round3(debate_history="测试历史")
        assert "关键风险提示" in result
        assert "永久性损失" in result

    def test_round3_preserves_consensus_and_divergence(self):
        """build_debate_round3 保留共识区域和分歧区域"""
        result = build_debate_round3(debate_history="测试历史")
        assert "共识区域" in result
        assert "分歧区域" in result
