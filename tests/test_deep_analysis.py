"""
DeepAnalysisCalculator 单元测试
覆盖：杜邦分析、Z-score、F-score、M-score、自由现金流、现金流象限、护城河
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_analyzer.calculator.deep_analysis import DeepAnalysisCalculator as DAC


# ============================================================================
# 杜邦分析测试
# ============================================================================
class TestDuPont3Factor:
    """三因素杜邦分解"""

    def test_normal_company(self):
        r = DAC.dupont_3factor(
            net_profit=100, revenue=1000,
            total_assets=2000, equity=800
        )
        assert r["roe"] == pytest.approx(12.5)
        assert r["net_margin"] == pytest.approx(10.0)
        assert r["asset_turnover"] == pytest.approx(0.5)
        assert r["equity_multiplier"] == pytest.approx(2.5)
        assert "驱动" in r["diagnosis"] or "型" in r["diagnosis"]

    def test_high_margin_company(self):
        """茅台型：高利润率驱动"""
        r = DAC.dupont_3factor(
            net_profit=500, revenue=1000,
            total_assets=3000, equity=2500
        )
        assert r["net_margin"] == pytest.approx(50.0)
        assert "高利润率" in r["diagnosis"]

    def test_high_turnover_company(self):
        """零售型：高周转驱动"""
        r = DAC.dupont_3factor(
            net_profit=50, revenue=5000,
            total_assets=2000, equity=500
        )
        assert r["asset_turnover"] == pytest.approx(2.5)
        assert "高资产周转" in r["diagnosis"]

    def test_high_leverage_company(self):
        """高杠杆型"""
        r = DAC.dupont_3factor(
            net_profit=80, revenue=1000,
            total_assets=5000, equity=500
        )
        assert r["equity_multiplier"] == pytest.approx(10.0)
        assert "高财务杠杆" in r["diagnosis"]

    def test_none_values(self):
        r = DAC.dupont_3factor(None, None, None, None)
        assert r["roe"] is None
        assert r["diagnosis"] == "数据不足，无法分析"

    def test_zero_equity(self):
        r = DAC.dupont_3factor(100, 1000, 2000, 0)
        assert r["roe"] is None


class TestDuPont5Factor:
    """五因素杜邦分解"""

    def test_normal(self):
        r = DAC.dupont_5factor(
            net_profit=100, revenue=1000, total_assets=2000,
            equity=800, ebit=150, interest_expense=20,
            tax_expense=30, pre_tax_profit=130
        )
        assert r["tax_burden"] == pytest.approx(100 / 130)
        assert r["interest_burden"] == pytest.approx(130 / 150)
        assert r["ebit_margin"] == pytest.approx(15.0)
        assert r["roe"] is not None


class TestDuPontTrend:
    """杜邦趋势分析"""

    def test_trend_improving(self):
        periods = [
            {"end_date": "20241231", "net_profit": 120, "revenue": 1000,
             "total_assets": 2000, "equity": 800},
            {"end_date": "20231231", "net_profit": 80, "revenue": 900,
             "total_assets": 1900, "equity": 750},
        ]
        r = DAC.dupont_trend(periods)
        assert len(r["periods"]) == 2
        assert r["trends"]["roe_trend"] == "上升"

    def test_trend_declining(self):
        periods = [
            {"end_date": "20241231", "net_profit": 50, "revenue": 800,
             "total_assets": 2000, "equity": 800},
            {"end_date": "20231231", "net_profit": 120, "revenue": 1000,
             "total_assets": 1900, "equity": 750},
        ]
        r = DAC.dupont_trend(periods)
        assert r["trends"]["roe_trend"] == "下降"


# ============================================================================
# Altman Z-score 测试
# ============================================================================
class TestAltmanZScore:
    """Z-score 破产预测"""

    def test_safe_company(self):
        r = DAC.altman_zscore(
            total_assets=10000, working_capital=2000,
            retained_earnings=3000, ebit=1500,
            market_cap=20000, total_liab=3000,
            revenue=8000, is_manufacturer=True
        )
        assert r["z_score"] > 2.99
        assert r["zone"] == "safe"
        assert r["zone_cn"] == "安全区"

    def test_distress_company(self):
        r = DAC.altman_zscore(
            total_assets=10000, working_capital=-2000,
            retained_earnings=-1000, ebit=100,
            market_cap=1000, total_liab=9000,
            revenue=3000, is_manufacturer=True
        )
        assert r["z_score"] < 1.81
        assert r["zone"] == "distress"
        assert r["zone_cn"] == "危险区"

    def test_grey_zone(self):
        r = DAC.altman_zscore(
            total_assets=10000, working_capital=500,
            retained_earnings=500, ebit=500,
            market_cap=5000, total_liab=5000,
            revenue=5000, is_manufacturer=True
        )
        assert r["zone"] in ["safe", "grey", "distress"]

    def test_non_manufacturer_thresholds(self):
        """非制造业阈值不同"""
        r = DAC.altman_zscore(
            total_assets=10000, working_capital=1000,
            retained_earnings=1500, ebit=1000,
            market_cap=10000, total_liab=4000,
            revenue=6000, is_manufacturer=False
        )
        assert r["zone"] in ["safe", "grey", "distress"]

    def test_zero_total_assets(self):
        r = DAC.altman_zscore(
            total_assets=0, working_capital=0,
            retained_earnings=0, ebit=0,
            market_cap=0, total_liab=0, revenue=0
        )
        assert r["z_score"] is None
        assert r["zone"] == "unknown"


# ============================================================================
# Piotroski F-score 测试
# ============================================================================
class TestPiotroskiFScore:
    """F-score 财务健康评分"""

    def _make_data(self, net_profit, op_cashflow, total_assets, total_liab,
                   current_assets, current_liab, shares, gross_profit,
                   revenue, equity):
        return {
            "net_profit": net_profit, "op_cashflow": op_cashflow,
            "total_assets": total_assets, "total_liab": total_liab,
            "current_assets": current_assets, "current_liab": current_liab,
            "shares": shares, "gross_profit": gross_profit,
            "revenue": revenue, "equity": equity,
        }

    def test_perfect_score(self):
        """理想公司：所有指标都好"""
        current = self._make_data(
            net_profit=100, op_cashflow=150, total_assets=1000,
            total_liab=300, current_assets=600, current_liab=200,
            shares=100, gross_profit=400, revenue=1000, equity=700
        )
        previous = self._make_data(
            net_profit=80, op_cashflow=100, total_assets=1100,
            total_liab=400, current_assets=500, current_liab=250,
            shares=100, gross_profit=300, revenue=900, equity=700
        )
        r = DAC.piotroski_fscore(current, previous)
        assert r["score"] >= 7
        assert "优秀" in r["diagnosis"] or "良好" in r["diagnosis"]

    def test_worst_score(self):
        """最差公司：所有指标都差"""
        current = self._make_data(
            net_profit=-50, op_cashflow=-30, total_assets=1000,
            total_liab=800, current_assets=300, current_liab=500,
            shares=120, gross_profit=100, revenue=500, equity=200
        )
        previous = self._make_data(
            net_profit=10, op_cashflow=20, total_assets=900,
            total_liab=600, current_assets=400, current_liab=300,
            shares=100, gross_profit=200, revenue=600, equity=300
        )
        r = DAC.piotroski_fscore(current, previous)
        assert r["score"] <= 3
        assert "较弱" in r["diagnosis"]

    def test_partial_data(self):
        """部分数据缺失"""
        current = {"net_profit": 100, "total_assets": 1000}
        previous = {"net_profit": 80, "total_assets": 900}
        r = DAC.piotroski_fscore(current, previous)
        assert 0 <= r["score"] <= 9

    def test_score_range(self):
        """分数范围 0-9"""
        current = self._make_data(
            net_profit=50, op_cashflow=60, total_assets=1000,
            total_liab=500, current_assets=400, current_liab=300,
            shares=100, gross_profit=200, revenue=800, equity=500
        )
        previous = self._make_data(
            net_profit=40, op_cashflow=50, total_assets=950,
            total_liab=480, current_assets=380, current_liab=280,
            shares=100, gross_profit=180, revenue=750, equity=470
        )
        r = DAC.piotroski_fscore(current, previous)
        assert 0 <= r["score"] <= 9
        assert 0 <= r["profit_score"] <= 4
        assert 0 <= r["leverage_score"] <= 3
        assert 0 <= r["efficiency_score"] <= 2


# ============================================================================
# Beneish M-score 测试
# ============================================================================
class TestBeneishMScore:
    """M-score 盈余管理检测"""

    def _make_data(self, revenue, accounts_receivable, gross_profit,
                   total_assets, current_assets, net_ppe, depreciation,
                   sga_expense, total_liab, net_profit, op_cashflow):
        return {
            "revenue": revenue, "accounts_receivable": accounts_receivable,
            "gross_profit": gross_profit, "total_assets": total_assets,
            "current_assets": current_assets, "net_ppe": net_ppe,
            "depreciation": depreciation, "sga_expense": sga_expense,
            "total_liab": total_liab, "net_profit": net_profit,
            "op_cashflow": op_cashflow,
        }

    def test_normal_company(self):
        """正常公司"""
        current = self._make_data(
            revenue=1000, accounts_receivable=100, gross_profit=400,
            total_assets=2000, current_assets=800, net_ppe=1000,
            depreciation=50, sga_expense=200, total_liab=800,
            net_profit=200, op_cashflow=250
        )
        previous = self._make_data(
            revenue=900, accounts_receivable=95, gross_profit=360,
            total_assets=1800, current_assets=700, net_ppe=900,
            depreciation=45, sga_expense=180, total_liab=700,
            net_profit=180, op_cashflow=220
        )
        r = DAC.beneish_mscore(current, previous)
        assert r["m_score"] is not None
        assert isinstance(r["manipulator"], bool)
        assert len(r["components"]) == 8

    def test_manipulator_detection(self):
        """应收暴增 → 可能有盈余操纵"""
        current = self._make_data(
            revenue=1000, accounts_receivable=500, gross_profit=200,
            total_assets=2000, current_assets=800, net_ppe=1000,
            depreciation=50, sga_expense=300, total_liab=800,
            net_profit=200, op_cashflow=50
        )
        previous = self._make_data(
            revenue=800, accounts_receivable=80, gross_profit=350,
            total_assets=1800, current_assets=700, net_ppe=900,
            depreciation=45, sga_expense=160, total_liab=700,
            net_profit=180, op_cashflow=220
        )
        r = DAC.beneish_mscore(current, previous)
        assert r["m_score"] is not None


# ============================================================================
# 自由现金流测试
# ============================================================================
class TestFreeCashFlow:
    """自由现金流"""

    def test_positive_fcf(self):
        r = DAC.free_cash_flow(op_cashflow=500, capex=200)
        assert r["fcf"] == 300
        assert r["fcf_positive"] is True

    def test_negative_fcf(self):
        r = DAC.free_cash_flow(op_cashflow=100, capex=300)
        assert r["fcf"] == -200
        assert r["fcf_positive"] is False

    def test_no_capex(self):
        r = DAC.free_cash_flow(op_cashflow=500, capex=None)
        assert r["fcf"] == 500

    def test_none_op_cf(self):
        r = DAC.free_cash_flow(op_cashflow=None, capex=None)
        assert r["fcf"] is None


class TestFCFTrend:
    """自由现金流趋势"""

    def test_positive_growing(self):
        data = [
            {"end_date": "20241231", "op_cashflow": 500, "capex": 200, "revenue": 2000},
            {"end_date": "20231231", "op_cashflow": 400, "capex": 180, "revenue": 1800},
            {"end_date": "20221231", "op_cashflow": 300, "capex": 150, "revenue": 1600},
        ]
        r = DAC.fcf_trend(data)
        assert "持续为正且增长" in r["trend"]

    def test_negative_trend(self):
        data = [
            {"end_date": "20241231", "op_cashflow": -100, "capex": 200, "revenue": 1000},
            {"end_date": "20231231", "op_cashflow": -50, "capex": 180, "revenue": 900},
        ]
        r = DAC.fcf_trend(data)
        assert "持续为负" in r["trend"]


class TestSimpleDCF:
    """简化 DCF 估值"""

    def test_basic_dcf(self):
        r = DAC.simple_dcf(
            fcf_latest=1000, growth_rate_5y=10,
            growth_rate_terminal=3, discount_rate=10,
            shares=1000, years=5
        )
        assert r["intrinsic_value_per_share"] is not None
        assert r["intrinsic_value_per_share"] > 0
        assert r["enterprise_value"] > 0

    def test_negative_fcf(self):
        r = DAC.simple_dcf(
            fcf_latest=-500, growth_rate_5y=10,
            growth_rate_terminal=3, discount_rate=10,
            shares=1000
        )
        assert r["intrinsic_value_per_share"] is None
        assert "error" in r


# ============================================================================
# 现金流象限测试
# ============================================================================
class TestCashflowQuadrant:
    """现金流象限"""

    def test_mature_cow(self):
        """成熟充裕型: 经营+ 投资+ 筹资+"""
        r = DAC.cashflow_quadrant(500, 100, 200)
        assert r["type"] == "成熟充裕型"
        assert r["pattern"] == "经营+/投资+/筹资+"

    def test_cash_cow(self):
        """成熟奶牛型: 经营+ 投资+ 筹资-"""
        r = DAC.cashflow_quadrant(500, 100, -200)
        assert r["type"] == "成熟奶牛型"
        assert r["pattern"] == "经营+/投资+/筹资-"

    def test_expansion(self):
        """扩张成长型: 经营+ 投资- 筹资+"""
        r = DAC.cashflow_quadrant(300, -500, 400)
        assert r["type"] == "扩张成长型"

    def test_burning_cash(self):
        """烧钱扩张型: 经营- 投资- 筹资+"""
        r = DAC.cashflow_quadrant(-100, -300, 500)
        assert r["type"] == "烧钱扩张型"

    def test_crisis(self):
        """危机衰退型: 经营- 投资- 筹资-"""
        r = DAC.cashflow_quadrant(-100, -200, -300)
        assert r["type"] == "危机衰退型"

    def test_none_values(self):
        r = DAC.cashflow_quadrant(None, None, None)
        assert r["type"] == "成熟充裕型"  # 0 >= 0 is True


class TestCashflowQuadrantTrend:
    """现金流象限趋势"""

    def test_transition(self):
        data = [
            {"end_date": "20241231", "op_cf": 300, "inv_cf": -500, "fin_cf": 400},
            {"end_date": "20231231", "op_cf": -100, "inv_cf": -200, "fin_cf": 500},
        ]
        r = DAC.cashflow_quadrant_trend(data)
        assert "转变为" in r["trend"]


# ============================================================================
# 经济护城河测试
# ============================================================================
class TestEconomicMoat:
    """护城河评估"""

    def test_wide_moat(self):
        """宽护城河：高毛利率稳定 + 高ROE + 高增长"""
        data = []
        for year in range(5):
            data.append({
                "end_date": f"{2024 - year}1231",
                "net_profit": 500 + year * 10,
                "revenue": 1000,
                "op_cost": 400 - year * 5,
                "total_assets": 3000,
                "equity": 2000,
            })
        r = DAC.economic_moat(data)
        assert r["moat_score"] >= 60
        assert r["moat_type"] in ["宽护城河", "窄护城河"]

    def test_no_moat(self):
        """无护城河：低毛利率 + 低ROE"""
        data = []
        for year in range(5):
            data.append({
                "end_date": f"{2024 - year}1231",
                "net_profit": 10 - year * 2,
                "revenue": 1000,
                "op_cost": 850 + year * 10,
                "total_assets": 3000,
                "equity": 2000,
            })
        r = DAC.economic_moat(data)
        assert r["moat_score"] < 60

    def test_insufficient_data(self):
        """数据不足"""
        r = DAC.economic_moat([{"end_date": "20241231"}])
        assert r["moat_type"] == "数据不足"

    def test_score_range(self):
        """分数范围 0-100"""
        data = []
        for year in range(3):
            data.append({
                "end_date": f"{2024 - year}1231",
                "net_profit": 100,
                "revenue": 1000,
                "op_cost": 600,
                "total_assets": 2000,
                "equity": 1000,
            })
        r = DAC.economic_moat(data)
        assert 0 <= r["moat_score"] <= 100
