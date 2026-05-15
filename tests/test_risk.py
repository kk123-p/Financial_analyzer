"""
RiskAssessmentModel 单元测试
"""
import pytest
import pandas as pd

from financial_analyzer.risk.assessment import RiskAssessmentModel


# ============================================================================
# 初始化与行业阈值
# ============================================================================
class TestInit:
    def test_default(self):
        model = RiskAssessmentModel()
        assert model.industry == "default"
        assert model.market == "CN"
        assert model.thresholds["debt_ratio_max"] == 70

    def test_bank_industry(self):
        model = RiskAssessmentModel(industry="银行")
        assert model.thresholds["debt_ratio_max"] == 95
        assert model.thresholds["current_ratio_min"] == 0

    def test_tech_industry(self):
        model = RiskAssessmentModel(industry="科技")
        assert model.thresholds["debt_ratio_max"] == 60

    def test_unknown_industry_falls_back_to_default(self):
        model = RiskAssessmentModel(industry="未知行业")
        assert model.thresholds == RiskAssessmentModel.INDUSTRY_THRESHOLDS["default"]

    def test_us_market_adjustment(self):
        cn = RiskAssessmentModel(industry="制造业", market="CN")
        us = RiskAssessmentModel(industry="制造业", market="US")
        assert us.thresholds["debt_ratio_max"] == cn.thresholds["debt_ratio_max"] + 10

    def test_us_market_cap(self):
        """美股调整后不超过 95"""
        model = RiskAssessmentModel(industry="银行", market="US")
        assert model.thresholds["debt_ratio_max"] <= 95


# ============================================================================
# assess_solvency_risk
# ============================================================================
class TestSolvencyRisk:
    @pytest.fixture
    def model(self):
        return RiskAssessmentModel()

    def test_all_excellent(self, model):
        result = model.assess_solvency_risk(
            current_ratio=3.0, quick_ratio=2.5, cash_ratio=None,
            debt_ratio=30, interest_coverage=10
        )
        assert result["score"] == 100  # 25+25+25+25
        assert len(result["details"]) == 4
        assert len(result["warnings"]) == 0

    def test_all_poor(self, model):
        result = model.assess_solvency_risk(
            current_ratio=0.5, quick_ratio=0.3, cash_ratio=None,
            debt_ratio=90, interest_coverage=0.5
        )
        assert result["score"] == 0
        assert len(result["warnings"]) >= 3

    def test_all_none(self, model):
        result = model.assess_solvency_risk(
            current_ratio=None, quick_ratio=None, cash_ratio=None,
            debt_ratio=None, interest_coverage=None
        )
        assert result["score"] == 0
        assert len(result["details"]) == 0

    def test_partial_values(self, model):
        result = model.assess_solvency_risk(
            current_ratio=2.0, quick_ratio=None, cash_ratio=None,
            debt_ratio=None, interest_coverage=None
        )
        assert 0 < result["score"] < 100

    def test_score_range(self, model):
        """任何输入组合的分数都应在 0-100 之间"""
        for cr in [None, 0.5, 1.0, 2.0, 5.0]:
            for dr in [None, 30, 60, 80, 95]:
                result = model.assess_solvency_risk(cr, None, None, dr, None)
                assert 0 <= result["score"] <= 100


# ============================================================================
# assess_profit_quality_risk
# ============================================================================
class TestProfitQualityRisk:
    @pytest.fixture
    def model(self):
        return RiskAssessmentModel()

    def test_excellent(self, model):
        result = model.assess_profit_quality_risk(
            net_profit=100, deduct_profit=95, op_cashflow=130,
            gross_margin=50, net_margin=20
        )
        assert result["score"] >= 90  # 30+40+15+15

    def test_poor(self, model):
        result = model.assess_profit_quality_risk(
            net_profit=100, deduct_profit=30, op_cashflow=-10,
            gross_margin=10, net_margin=2
        )
        assert result["score"] < 30
        assert len(result["warnings"]) >= 3

    def test_all_none(self, model):
        result = model.assess_profit_quality_risk(
            net_profit=None, deduct_profit=None, op_cashflow=None,
            gross_margin=None, net_margin=None
        )
        assert result["score"] == 0

    def test_negative_profit(self, model):
        result = model.assess_profit_quality_risk(
            net_profit=-50, deduct_profit=None, op_cashflow=None,
            gross_margin=None, net_margin=-5
        )
        # 应该有亏损警告
        assert any("亏损" in w or "负" in w for w in result["warnings"])


# ============================================================================
# assess_operation_risk
# ============================================================================
class TestOperationRisk:
    @pytest.fixture
    def model(self):
        return RiskAssessmentModel()

    def test_excellent(self, model):
        result = model.assess_operation_risk(
            ar_turnover=12, inv_turnover=10, ar_days=20, inv_days=30
        )
        assert result["score"] == 100

    def test_poor(self, model):
        result = model.assess_operation_risk(
            ar_turnover=1, inv_turnover=1, ar_days=120, inv_days=200
        )
        assert result["score"] < 40
        assert len(result["warnings"]) >= 2

    def test_all_none(self, model):
        result = model.assess_operation_risk(
            ar_turnover=None, inv_turnover=None, ar_days=None, inv_days=None
        )
        assert result["score"] == 0

    def test_turnover_vs_days_fallback(self, model):
        """只有 days 没有 turnover 时也能评分"""
        result = model.assess_operation_risk(
            ar_turnover=None, inv_turnover=None, ar_days=30, inv_days=45
        )
        assert result["score"] > 0


# ============================================================================
# check_warning_signals
# ============================================================================
class TestWarningSignals:
    @pytest.fixture
    def model(self):
        return RiskAssessmentModel()

    def test_healthy_company(self, model):
        balance = pd.DataFrame([{
            "total_assets": 1000, "total_liab": 500,
            "total_cur_assets": 400, "total_cur_liab": 200,
        }])
        income = pd.DataFrame([{
            "net_profit": 100, "total_revenue": 800,
        }])
        cashflow = pd.DataFrame([{"n_cashflow_act": 150}])
        fina = pd.DataFrame([{"roe": 15}])

        warnings, score = model.check_warning_signals(balance, income, cashflow, fina)
        assert score >= 80
        assert len(warnings) == 0

    def test_loss_making_company(self, model):
        balance = pd.DataFrame([{
            "total_assets": 1000, "total_liab": 500,
            "total_cur_assets": 400, "total_cur_liab": 200,
        }])
        income = pd.DataFrame([{
            "net_profit": -50, "total_revenue": 800,
        }])
        cashflow = pd.DataFrame([{"n_cashflow_act": 150}])
        fina = pd.DataFrame([{"roe": 15}])

        warnings, score = model.check_warning_signals(balance, income, cashflow, fina)
        assert score < 100
        assert any("亏损" in w for w in warnings)

    def test_high_debt(self, model):
        balance = pd.DataFrame([{
            "total_assets": 1000, "total_liab": 850,
            "total_cur_assets": 400, "total_cur_liab": 200,
        }])
        income = pd.DataFrame([{
            "net_profit": 100, "total_revenue": 800,
        }])

        warnings, score = model.check_warning_signals(balance, income, None, None)
        assert any("资产负债率" in w for w in warnings)

    def test_all_none(self, model):
        warnings, score = model.check_warning_signals(None, None, None, None)
        assert score == 100
        assert len(warnings) == 0

    def test_score_floor_at_zero(self, model):
        """分数不应低于 0"""
        balance = pd.DataFrame([{
            "total_assets": 1000, "total_liab": 950,
            "total_cur_assets": 100, "total_cur_liab": 500,
        }])
        income = pd.DataFrame([{
            "net_profit": -100, "total_revenue": -10,
        }])
        cashflow = pd.DataFrame([{"n_cashflow_act": -50}])
        fina = pd.DataFrame([{"roe": 1}])

        warnings, score = model.check_warning_signals(balance, income, cashflow, fina)
        assert score >= 0


# ============================================================================
# calculate_total_risk_score
# ============================================================================
class TestTotalRiskScore:
    @pytest.fixture
    def model(self):
        return RiskAssessmentModel()

    def test_perfect_score(self, model):
        solvency = {"score": 100}
        profit = {"score": 100}
        operation = {"score": 100}
        warning = 100
        total = model.calculate_total_risk_score(solvency, profit, operation, warning)
        assert total == 100

    def test_zero_score(self, model):
        solvency = {"score": 0}
        profit = {"score": 0}
        operation = {"score": 0}
        warning = 0
        total = model.calculate_total_risk_score(solvency, profit, operation, warning)
        assert total == 0

    def test_weights_sum_to_one(self, model):
        """权重之和应为 1"""
        weights = RiskAssessmentModel.RISK_WEIGHTS
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_none_handling(self, model):
        total = model.calculate_total_risk_score(None, None, None, 50)
        assert total == 10  # 50 * 0.2


# ============================================================================
# get_risk_level
# ============================================================================
class TestRiskLevel:
    @pytest.fixture
    def model(self):
        return RiskAssessmentModel()

    def test_low_risk(self, model):
        level, icon = model.get_risk_level(85)
        assert level == "低风险"
        assert "🟢" in icon

    def test_medium_risk(self, model):
        level, icon = model.get_risk_level(65)
        assert level == "中风险"
        assert "🟡" in icon

    def test_high_medium_risk(self, model):
        level, icon = model.get_risk_level(45)
        assert level == "较高风险"
        assert "🟠" in icon

    def test_high_risk(self, model):
        level, icon = model.get_risk_level(20)
        assert level == "高风险"
        assert "🔴" in icon

    def test_boundary_80(self, model):
        level, _ = model.get_risk_level(80)
        assert level == "低风险"

    def test_boundary_60(self, model):
        level, _ = model.get_risk_level(60)
        assert level == "中风险"

    def test_boundary_40(self, model):
        level, _ = model.get_risk_level(40)
        assert level == "较高风险"
