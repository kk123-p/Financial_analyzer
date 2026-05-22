"""AI 模板系统测试"""
import pytest
import pandas as pd
from financial_analyzer.ai.templates import (
    SYSTEM_TEMPLATES, get_template_data_summary, build_lightweight_summary,
    _format_table, _format_trend_summary, _format_top_holders, _format_holder_trend,
    _format_dividend_summary
)


class TestTemplateDefinitions:
    def test_all_six_templates(self):
        assert len(SYSTEM_TEMPLATES) == 6
        names = [t["name"] for t in SYSTEM_TEMPLATES]
        assert "盈利能力深度解读" in names
        assert "财务异常信号排查" in names
        assert "估值合理性判断" in names
        assert "股东结构评估" in names
        assert "资金面多空分析" in names
        assert "成长质量检查" in names

    def test_each_template_has_required_fields(self):
        for t in SYSTEM_TEMPLATES:
            assert "name" in t
            assert "mode" in t
            assert t["mode"] == "template"
            assert "system_role" in t
            assert "data_required" in t
            assert "primary" in t["data_required"]
            assert "analysis_sections" in t
            assert len(t["analysis_sections"]) >= 1
            assert "output_format" in t

    def test_no_scoring(self):
        """确认模板不包含评分字段"""
        for t in SYSTEM_TEMPLATES:
            for s in t.get("analysis_sections", []):
                assert "scoring" not in s
                assert "weight" not in s


class TestDataFormatting:
    @pytest.fixture
    def sample_financial(self):
        return pd.DataFrame([
            {"end_date": "20241231", "roe": 18.2, "grossprofit_margin": 22.3,
             "netprofit_margin": 5.1, "debt_to_assets": 68.4},
            {"end_date": "20231231", "roe": 16.8, "grossprofit_margin": 20.1,
             "netprofit_margin": 4.6, "debt_to_assets": 70.2},
        ])

    @pytest.fixture
    def sample_holders(self):
        return pd.DataFrame([
            {"end_date": "20240630", "holder_name": "测试集团", "hold_ratio": 30.0},
            {"end_date": "20240630", "holder_name": "社保基金", "hold_ratio": 12.0},
        ])

    def test_format_table(self, sample_financial):
        result = _format_table(sample_financial, {"roe", "grossprofit_margin"}, max_rows=3)
        # Should contain the metric values or column names
        assert len(result) > 0

    def test_format_top_holders(self, sample_holders):
        result = _format_top_holders(sample_holders)
        assert "测试集团" in result

    def test_format_holder_trend(self):
        df = pd.DataFrame([
            {"ann_date": "20221231", "holder_num": 500000},
            {"ann_date": "20231231", "holder_num": 420000},
        ])
        result = _format_holder_trend(df)
        assert "50.0万" in result or "42.0万" in result

    def test_format_dividend_summary(self):
        df = pd.DataFrame([
            {"ann_date": "20231231", "cash_div": 1.5},
            {"ann_date": "20221231", "cash_div": 1.2},
        ])
        result = _format_dividend_summary(df)
        assert "1.5" in result
        assert "2.70" in result  # sum of 1.5 + 1.2

    def test_get_template_data_summary(self, sample_financial):
        data = {"financial": sample_financial}
        template = SYSTEM_TEMPLATES[0]  # 盈利能力
        result = get_template_data_summary(data, "000001.SZ", template)
        assert len(result) > 0

    def test_build_lightweight_summary(self, sample_financial):
        data = {"financial": sample_financial}
        result = build_lightweight_summary(data, "000001.SZ")
        assert "000001" in result
        assert len(result) > 100

    def test_format_moneyflow_trend(self):
        df = pd.DataFrame([
            {"trade_date": f"202501{i:02d}", "buy_elg_amount": 1e7,
             "sell_elg_amount": 5e6, "buy_lg_amount": 5e6, "sell_lg_amount": 3e6,
             "buy_md_amount": 0, "sell_md_amount": 0,
             "buy_sm_amount": 0, "sell_sm_amount": 0}
            for i in range(1, 26)
        ])
        result = _format_trend_summary(df, "moneyflow")
        assert "主力资金" in result

    def test_zero_values_handled(self):
        """零值不应被当作缺失数据丢弃"""
        data = {"income": pd.DataFrame([{"end_date": "20241231", "total_revenue": 1e9, "net_profit": 0.0}])}
        result = build_lightweight_summary(data, "000001.SZ")
        assert "净利润: 0" in result or "0.00" in result

    def test_empty_data_safe(self):
        """空数据不应崩溃"""
        result = get_template_data_summary({}, "000001.SZ", SYSTEM_TEMPLATES[0])
        assert result == ""

    def test_missing_columns_safe(self):
        """缺少关键列不应崩溃"""
        df = pd.DataFrame([{"some_col": 1}])
        result = _format_table(df, {"roe"}, max_rows=3)
        assert len(result) >= 0


class TestTemplatePromptAssembly:
    def test_data_required_keys(self):
        for t in SYSTEM_TEMPLATES:
            assert len(t["data_required"]["primary"]) > 0

    def test_section_guidance_not_empty(self):
        for t in SYSTEM_TEMPLATES:
            for s in t["analysis_sections"]:
                assert len(s.get("guidance", "")) > 15, \
                    f"{t['name']} section {s['title']} guidance too short"
