import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_analyzer.deepseek.prompts import (
    ANALYST_ROLES,
    CROSS_EXAM_DIRECTIONS,
    DEBATE_SYSTEM_PROMPT,
    build_debate_round1,
    build_debate_round2,
    build_debate_round3,
    build_citation_verification_prompt,
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


# ============================================================================
# Task 5: 辩论第二轮 role_key 模板化测试
# ============================================================================

class TestDebateRound2RoleKey:
    """验证 build_debate_round2 支持 role_key 参数"""

    @pytest.mark.parametrize("role_key", ["value", "growth", "risk"])
    def test_round2_with_role_key_contains_role_name(self, role_key):
        """role_key 模式输出包含对应角色名"""
        statements = {"value": "陈述1", "growth": "陈述2", "risk": "陈述3"}
        result = build_debate_round2(statements, role_key=role_key)
        role = ANALYST_ROLES[role_key]
        assert role["name"] in result

    @pytest.mark.parametrize("role_key", ["value", "growth", "risk"])
    def test_round2_with_role_key_contains_system_prompt(self, role_key):
        """role_key 模式输出包含角色 system_prompt"""
        statements = {"value": "陈述1", "growth": "陈述2", "risk": "陈述3"}
        result = build_debate_round2(statements, role_key=role_key)
        role = ANALYST_ROLES[role_key]
        assert role["system_prompt"][:20] in result

    @pytest.mark.parametrize("role_key", ["value", "growth", "risk"])
    def test_round2_with_role_key_contains_cross_exam_direction(self, role_key):
        """role_key 模式输出包含该角色的质询方向"""
        statements = {"value": "陈述1", "growth": "陈述2", "risk": "陈述3"}
        result = build_debate_round2(statements, role_key=role_key)
        direction = CROSS_EXAM_DIRECTIONS[role_key]
        assert direction[:20] in result

    @pytest.mark.parametrize("role_key", ["value", "growth", "risk"])
    def test_round2_with_role_key_contains_all_analyses(self, role_key):
        """role_key 模式输出包含所有分析师的陈述"""
        statements = {"value": "价值观点A", "growth": "成长观点B", "risk": "风控观点C"}
        result = build_debate_round2(statements, role_key=role_key)
        assert "价值观点A" in result
        assert "成长观点B" in result
        assert "风控观点C" in result

    def test_round2_without_role_key_still_works(self):
        """无 role_key 时向后兼容"""
        result = build_debate_round2(round1_statements="测试陈述")
        assert "交叉质询" in result
        assert "具体质疑" in result


class TestCrossExamDirections:
    """验证 CROSS_EXAM_DIRECTIONS 定义完整"""

    def test_all_roles_have_directions(self):
        """所有分析师角色都有对应的质询方向"""
        for role_key in ["value", "growth", "risk"]:
            assert role_key in CROSS_EXAM_DIRECTIONS

    @pytest.mark.parametrize("role_key", ["value", "growth", "risk"])
    def test_direction_is_nonempty_string(self, role_key):
        """每个质询方向是非空字符串"""
        assert isinstance(CROSS_EXAM_DIRECTIONS[role_key], str)
        assert len(CROSS_EXAM_DIRECTIONS[role_key]) > 10


# ============================================================================
# Task 6: 引用验证提示词测试
# ============================================================================

class TestCitationVerification:
    """验证 build_citation_verification_prompt 输出正确"""

    def test_output_contains_debate_text(self):
        """输出包含传入的辩论文本"""
        text = "ROE = 15.3%（2024年报）"
        result = build_citation_verification_prompt(text)
        assert text in result

    def test_output_requires_verification_format(self):
        """输出要求验证格式"""
        result = build_citation_verification_prompt("测试辩论内容")
        assert "[准确]" in result
        assert "[不准确]" in result
        assert "[无法验证]" in result

    def test_output_requires_summary(self):
        """输出要求总结统计"""
        result = build_citation_verification_prompt("测试辩论内容")
        assert "总引用数" in result
        assert "整体可信度" in result

    def test_output_contains_indicator_fields(self):
        """输出包含验证字段要求"""
        result = build_citation_verification_prompt("测试辩论内容")
        assert "指标名称" in result
        assert "引用数值" in result
        assert "报告期" in result

    def test_output_requires_verification_status(self):
        """输出要求验证状态分类"""
        result = build_citation_verification_prompt("测试辩论内容")
        assert "准确" in result
        assert "不准确" in result
        assert "无法验证" in result


# ============================================================================
# Task 7: 语言一致性测试
# ============================================================================

class TestLanguageConsistency:
    """验证提示词语言一致性"""

    def test_debate_system_prompt_no_english_role_labels(self):
        """DEBATE_SYSTEM_PROMPT 不含英文角色标签"""
        assert "You are" not in DEBATE_SYSTEM_PROMPT
        assert "your task" not in DEBATE_SYSTEM_PROMPT

    def test_debate_system_prompt_chinese_structure(self):
        """DEBATE_SYSTEM_PROMPT 包含中文结构化内容"""
        assert "语言一致性" in DEBATE_SYSTEM_PROMPT
        assert "引用执行" in DEBATE_SYSTEM_PROMPT
        assert "结构化输出" in DEBATE_SYSTEM_PROMPT

    def test_debate_system_prompt_citation_rules(self):
        """DEBATE_SYSTEM_PROMPT 包含引用执行规则"""
        assert "指标名称" in DEBATE_SYSTEM_PROMPT
        assert "报告期" in DEBATE_SYSTEM_PROMPT
        assert "[推断]" in DEBATE_SYSTEM_PROMPT
        assert "[事实]" in DEBATE_SYSTEM_PROMPT

    def test_risk_role_no_english_in_prompt(self):
        """risk 角色 system_prompt 无英文硬编码"""
        prompt = ANALYST_ROLES["risk"]["system_prompt"]
        assert "You are" not in prompt
        assert "you are" not in prompt

    def test_risk_role_contains_five_dimensions(self):
        """risk 角色 system_prompt 包含 5 个风控维度"""
        prompt = ANALYST_ROLES["risk"]["system_prompt"]
        assert "杠杆与偿债能力" in prompt
        assert "现金流脆弱性" in prompt
        assert "反身性风险" in prompt
        assert "治理与透明度" in prompt
        assert "尾部风险暴露" in prompt

    def test_risk_role_tool_guidance_uses_anomaly_signals(self):
        """risk 角色工具指引包含 get_anomaly_signals"""
        prompt = ANALYST_ROLES["risk"]["system_prompt"]
        assert "get_anomaly_signals" in prompt
