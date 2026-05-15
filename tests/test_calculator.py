"""
FinancialCalculator 单元测试
"""
import pytest
import pandas as pd
import numpy as np

from financial_analyzer.calculator.financial import FinancialCalculator as FC


# ============================================================================
# safe_divide
# ============================================================================
class TestSafeDivide:
    def test_normal(self):
        assert FC.safe_divide(10, 2) == 5.0

    def test_zero_denominator(self):
        assert FC.safe_divide(10, 0) is None

    def test_none_denominator(self):
        assert FC.safe_divide(10, None) is None

    def test_none_numerator(self):
        assert FC.safe_divide(None, 2) is None

    def test_both_none(self):
        assert FC.safe_divide(None, None) is None

    def test_nan_denominator(self):
        assert FC.safe_divide(10, np.nan) is None

    def test_nan_numerator(self):
        assert FC.safe_divide(np.nan, 2) is None

    def test_negative(self):
        assert FC.safe_divide(-10, 2) == -5.0

    def test_float(self):
        result = FC.safe_divide(1, 3)
        assert result is not None
        assert abs(result - 0.333333) < 1e-5

    def test_zero_numerator(self):
        assert FC.safe_divide(0, 5) == 0.0


# ============================================================================
# format_value
# ============================================================================
class TestFormatValue:
    def test_normal(self):
        assert FC.format_value(1234.5678, 2) == "1,234.57"

    def test_with_unit(self):
        result = FC.format_value(12.345, 2, "亿")
        assert "亿" in result
        assert "12.35" in result

    def test_none(self):
        assert FC.format_value(None) == "N/A"

    def test_nan(self):
        assert FC.format_value(np.nan) == "N/A"

    def test_custom_default(self):
        assert FC.format_value(None, default="--") == "--"

    def test_zero(self):
        assert FC.format_value(0, 2) == "0.00"

    def test_negative(self):
        result = FC.format_value(-5.678, 2)
        assert "-5.68" in result


# ============================================================================
# format_percentage
# ============================================================================
class TestFormatPercentage:
    def test_normal(self):
        assert FC.format_percentage(15.5) == "15.50%"

    def test_none(self):
        assert FC.format_percentage(None) == "N/A"

    def test_nan(self):
        assert FC.format_percentage(np.nan) == "N/A"

    def test_zero(self):
        assert FC.format_percentage(0) == "0.00%"

    def test_negative(self):
        assert FC.format_percentage(-3.14) == "-3.14%"

    def test_custom_decimal(self):
        assert FC.format_percentage(12.3456, 3) == "12.346%"


# ============================================================================
# format_change
# ============================================================================
class TestFormatChange:
    def test_positive(self):
        assert FC.format_change(5.2) == "+5.20%"

    def test_negative(self):
        assert FC.format_change(-3.1) == "-3.10%"

    def test_zero(self):
        assert FC.format_change(0) == "+0.00%"

    def test_none(self):
        assert FC.format_change(None) == "N/A"


# ============================================================================
# calc_yoy_growth
# ============================================================================
class TestCalcYoYGrowth:
    def test_normal(self):
        result = FC.calc_yoy_growth(120, 100)
        assert result == pytest.approx(20.0)

    def test_decline(self):
        result = FC.calc_yoy_growth(80, 100)
        assert result == pytest.approx(-20.0)

    def test_zero_previous(self):
        assert FC.calc_yoy_growth(100, 0) is None

    def test_none_previous(self):
        assert FC.calc_yoy_growth(100, None) is None

    def test_none_current(self):
        assert FC.calc_yoy_growth(None, 100) is None

    def test_nan(self):
        assert FC.calc_yoy_growth(np.nan, 100) is None

    def test_negative_previous(self):
        # 从 -50 到 100: (100 - (-50)) / abs(-50) * 100 = 300%
        result = FC.calc_yoy_growth(100, -50)
        assert result == pytest.approx(300.0)


# ============================================================================
# calc_cagr
# ============================================================================
class TestCalcCAGR:
    def test_normal_growth(self):
        # 100 -> 150 -> 200 over 2 years
        # CAGR = (200/100)^(1/2) - 1 = 41.42%
        values = [200, 150, 100]  # newest first
        result = FC.calc_cagr(values, 2)
        assert result is not None
        assert abs(result - 41.42) < 0.5

    def test_single_value(self):
        assert FC.calc_cagr([100], 1) is None

    def test_empty(self):
        assert FC.calc_cagr([], 1) is None

    def test_zero_start(self):
        assert FC.calc_cagr([100, 0], 1) is None

    def test_negative_start(self):
        assert FC.calc_cagr([100, -50], 1) is None

    def test_zero_years(self):
        assert FC.calc_cagr([100, 200], 0) is None

    def test_decline(self):
        # 200 -> 100 over 2 years: (100/200)^(1/2) - 1 = -29.29%
        values = [100, 150, 200]
        result = FC.calc_cagr(values, 2)
        assert result is not None
        assert result < 0
        assert abs(result - (-29.29)) < 0.5


# ============================================================================
# calc_structure_ratio
# ============================================================================
class TestCalcStructureRatio:
    def test_normal(self):
        assert FC.calc_structure_ratio(30, 100) == pytest.approx(30.0)

    def test_zero_total(self):
        assert FC.calc_structure_ratio(30, 0) is None

    def test_none(self):
        assert FC.calc_structure_ratio(None, 100) is None


# ============================================================================
# calculate_technical_indicators
# ============================================================================
class TestTechnicalIndicators:
    @pytest.fixture
    def sample_df(self):
        """生成 60 天的模拟日线数据"""
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=60, freq="B")
        close = 100 + np.cumsum(np.random.randn(60) * 2)
        return pd.DataFrame({
            "trade_date": dates.strftime("%Y%m%d"),
            "open": close + np.random.randn(60) * 0.5,
            "high": close + abs(np.random.randn(60)) * 1.5,
            "low": close - abs(np.random.randn(60)) * 1.5,
            "close": close,
            "vol": np.random.randint(10000, 100000, 60),
        })

    def test_has_ma_columns(self, sample_df):
        result = FC.calculate_technical_indicators(sample_df)
        for col in ["MA5", "MA10", "MA20", "MA60"]:
            assert col in result.columns

    def test_has_rsi(self, sample_df):
        result = FC.calculate_technical_indicators(sample_df)
        assert "RSI14" in result.columns
        # RSI 应在 0-100 之间
        rsi = result["RSI14"].dropna()
        assert (rsi >= 0).all() and (rsi <= 100).all()

    def test_has_macd(self, sample_df):
        result = FC.calculate_technical_indicators(sample_df)
        for col in ["MACD", "Signal", "Histogram"]:
            assert col in result.columns

    def test_has_bollinger(self, sample_df):
        result = FC.calculate_technical_indicators(sample_df)
        for col in ["BB_Upper", "BB_Middle", "BB_Lower"]:
            assert col in result.columns
        # 上轨 > 中轨 > 下轨
        valid = result.dropna(subset=["BB_Upper", "BB_Lower"])
        assert (valid["BB_Upper"] >= valid["BB_Lower"]).all()

    def test_empty_df(self):
        result = FC.calculate_technical_indicators(pd.DataFrame())
        assert result.empty

    def test_no_close_column(self):
        df = pd.DataFrame({"open": [1, 2, 3]})
        result = FC.calculate_technical_indicators(df)
        assert len(result) == 3  # 原样返回


# ============================================================================
# calculate_financial_ratios
# ============================================================================
class TestFinancialRatios:
    @pytest.fixture
    def balance_df(self):
        return pd.DataFrame([{
            "total_cur_assets": 500,
            "total_cur_liab": 300,
            "inventories": 100,
            "total_assets": 1000,
            "total_liab": 600,
            "total_hldr_eqy_exc_min_int": 400,
        }])

    @pytest.fixture
    def income_df(self):
        return pd.DataFrame([{
            "total_revenue": 800,
            "net_profit": 100,
            "oper_cost": 500,
        }])

    def test_current_ratio(self, balance_df, income_df):
        ratios = FC.calculate_financial_ratios(balance_df, income_df, None)
        assert ratios["current_ratio"] == pytest.approx(500 / 300)

    def test_quick_ratio(self, balance_df, income_df):
        ratios = FC.calculate_financial_ratios(balance_df, income_df, None)
        assert ratios["quick_ratio"] == pytest.approx(400 / 300)

    def test_debt_ratio(self, balance_df, income_df):
        ratios = FC.calculate_financial_ratios(balance_df, income_df, None)
        assert ratios["debt_ratio"] == pytest.approx(600 / 1000)

    def test_gross_margin(self, balance_df, income_df):
        ratios = FC.calculate_financial_ratios(balance_df, income_df, None)
        assert ratios["gross_margin"] == pytest.approx(37.5)

    def test_net_margin(self, balance_df, income_df):
        ratios = FC.calculate_financial_ratios(balance_df, income_df, None)
        assert ratios["net_margin"] == pytest.approx(12.5)

    def test_none_balance(self, income_df):
        ratios = FC.calculate_financial_ratios(None, income_df, None)
        assert "current_ratio" not in ratios
        assert "gross_margin" in ratios
