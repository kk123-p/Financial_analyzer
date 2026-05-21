import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_analyzer.ai.prompt_framework import PromptBuilder


class TestPromptBuilderQuickMode:
    def test_build_quick_mode_minimal(self):
        """快速模式：仅数据 + 问题，不注入框架"""
        report = {"company_snapshot": {"name": "测试公司"}, "financial_health": {}}
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_mode("quick")
        prompt = builder.build()

        assert "测试公司" in prompt
        assert "快速分析" in prompt


class TestPromptBuilderDeepMode:
    def test_build_deep_mode_with_harvard_framework(self):
        """深度模式：注入哈佛分析框架"""
        report = {
            "company_snapshot": {"name": "贵州茅台", "price": 1800},
            "financial_health": {
                "盈利能力": {"ROE": 30.5, "毛利率": 92.0},
                "偿债能力": {"资产负债率": 21.5},
            },
            "risk_models": {"zscore": {"z_score": 8.5}},
        }
        builder = PromptBuilder("贵州茅台")
        builder.with_data(report)
        builder.with_framework("harvard")
        builder.with_mode("deep")
        prompt = builder.build()

        assert "贵州茅台" in prompt
        assert "哈佛分析框架" in prompt
        assert "战略分析" in prompt
        assert "会计分析" in prompt
        assert "财务分析" in prompt
        assert "前景分析" in prompt
        assert "ROE" in prompt

    def test_build_deep_mode_with_crosscheck(self):
        """深度模式：注入三表联动验证"""
        report = {
            "company_snapshot": {"name": "测试公司"},
            "financial_health": {"_raw": {"net_profit": 100, "op_cashflow": 120}},
            "dupont_analysis": {"improved": [{"rnoa": 15.0, "flev": 0.5}]},
        }
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_framework("crosscheck")
        builder.with_mode("deep")
        prompt = builder.build()

        assert "三表联动验证" in prompt
        assert "经营性资产" in prompt
        assert "经营现金流" in prompt

    def test_build_deep_mode_with_lifecycle(self):
        """深度模式：注入生命周期定位框架"""
        report = {
            "company_snapshot": {"name": "测试公司"},
            "cashflow_analysis": {"quadrant": [{"quadrant_type": "成熟期"}]},
        }
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_framework("lifecycle")
        builder.with_mode("deep")
        prompt = builder.build()

        assert "生命周期" in prompt

    def test_build_deep_mode_with_warnings(self):
        """深度模式：注入13条利润质量预警"""
        report = {
            "company_snapshot": {"name": "测试公司"},
            "anomaly_signals": [
                {"name": "盈利质量预警", "level": "high", "trigger_data": "CF/NP = 0.3"}
            ],
        }
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_framework("warnings")
        builder.with_mode("deep")
        prompt = builder.build()

        assert "利润质量恶化预警" in prompt
        assert "盈利质量预警" in prompt

    def test_build_deep_mode_all_frameworks(self):
        """深度模式：组合全部4个框架"""
        report = {
            "company_snapshot": {"name": "测试公司"},
            "financial_health": {
                "盈利能力": {"ROE": 20.0},
                "偿债能力": {"资产负债率": 50.0},
                "营运能力": {"总资产周转率": 0.8},
                "发展能力": {"营收增长率": 15.0},
            },
            "risk_models": {"zscore": {"z_score": 3.0}, "mscore": {"m_score": -2.0}},
            "anomaly_signals": [],
            "cashflow_analysis": {"quadrant": [{"quadrant_type": "成长期"}]},
        }
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_framework("harvard")
        builder.with_framework("crosscheck")
        builder.with_framework("lifecycle")
        builder.with_framework("warnings")
        builder.with_output_format("structured")
        builder.with_mode("deep")
        prompt = builder.build()

        assert "哈佛分析框架" in prompt
        assert "三表联动验证" in prompt
        assert "生命周期" in prompt
        assert "利润质量恶化预警" in prompt
        assert "数据依据" in prompt
        assert "推理过程" in prompt
        assert "综合结论" in prompt

    def test_build_with_signals_injection(self):
        """注入矛盾信号到提示词"""
        report = {"company_snapshot": {"name": "测试公司"}, "financial_health": {}}
        signals = [
            {"name": "盈利质量预警", "trigger_data": "CF/NP = 0.3", "task": "请解释利润缺乏现金支撑的原因"},
            {"name": "增长透支预警", "trigger_data": "AR增速/Rev增速 = 2.1", "task": "分析是否放宽信用政策"},
        ]
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_signals(signals)
        builder.with_mode("deep")
        prompt = builder.build()

        assert "盈利质量预警" in prompt
        assert "增长透支预警" in prompt
        assert "CF/NP = 0.3" in prompt
        assert "请解释利润缺乏现金支撑的原因" in prompt


class TestPromptBuilderDebateMode:
    def test_build_debate_mode_includes_roles(self):
        """辩论模式：包含三视角角色提示词"""
        report = {"company_snapshot": {"name": "测试公司"}, "financial_health": {}}
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_mode("debate")
        prompt = builder.build()

        assert "格雷厄姆" in prompt or "价值" in prompt
        assert "费雪" in prompt or "成长" in prompt
        assert "塔勒布" in prompt or "风控" in prompt


class TestPromptBuilderFollowupMode:
    def test_followup_with_context(self):
        """追问模式：注入历史上下文"""
        report = {"company_snapshot": {"name": "测试公司"}, "financial_health": {}}
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_context("之前的分析结论: ROE=30%, 盈利质量优秀")
        builder.with_mode("followup")
        prompt = builder.build()

        assert "测试公司" in prompt
        assert "之前的分析" in prompt
        assert "ROE=30%" in prompt
        assert "追问" in prompt

    def test_followup_without_context_still_builds(self):
        """追问模式无上下文时仍能正常构建"""
        report = {"company_snapshot": {"name": "测试公司"}, "financial_health": {}}
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_mode("followup")
        prompt = builder.build()

        assert "测试公司" in prompt
        assert len(prompt) > 50


class TestPromptBuilderEdgeCases:
    def test_quick_mode_does_not_inject_frameworks(self):
        """快速模式下不注入任何分析框架"""
        report = {"company_snapshot": {"name": "测试公司"}, "financial_health": {}}
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_framework("harvard")
        builder.with_mode("quick")
        prompt = builder.build()

        assert "哈佛分析框架" not in prompt

    def test_explicit_output_format_overrides_deep_default(self):
        """显式设置 output_format 覆盖深度模式的默认结构化"""
        report = {"company_snapshot": {"name": "测试公司"}, "financial_health": {}}
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_mode("deep")
        builder.with_output_format("structured")
        prompt = builder.build()

        assert "数据依据" in prompt
        assert "推理过程" in prompt

    def test_unknown_framework_key_silently_ignored(self):
        """未知框架键不报错，静默忽略"""
        report = {"company_snapshot": {"name": "测试公司"}, "financial_health": {}}
        builder = PromptBuilder("测试公司")
        builder.with_data(report)
        builder.with_framework("nonexistent_framework")
        builder.with_mode("deep")
        prompt = builder.build()

        assert "测试公司" in prompt
