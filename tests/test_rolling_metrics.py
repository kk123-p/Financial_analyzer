"""滚动绩效指标测试"""
import numpy as np
import pandas as pd
import pytest

from financial_analyzer.quant.backtest.rolling_metrics import RollingMetricsCalculator


@pytest.fixture
def calc():
    return RollingMetricsCalculator(window=3)


@pytest.fixture
def long_returns():
    """24 个月的模拟月度收益率"""
    np.random.seed(42)
    return pd.Series(np.random.normal(0.01, 0.05, 24))


@pytest.fixture
def long_equity():
    """24 个月的模拟净值曲线"""
    np.random.seed(42)
    returns = np.random.normal(0.01, 0.05, 24)
    curve = [1000.0]
    for r in returns:
        curve.append(curve[-1] * (1 + r))
    return pd.Series(curve)


class TestRollingSharpe:
    def test_returns_empty_when_insufficient_data(self, calc):
        short = pd.Series([0.01, 0.02])
        result = calc.rolling_sharpe(short)
        assert len(result) == 0

    def test_returns_series_with_correct_length(self, calc, long_returns):
        result = calc.rolling_sharpe(long_returns)
        assert len(result) == len(long_returns) - calc.window + 1

    def test_values_are_finite(self, calc, long_returns):
        result = calc.rolling_sharpe(long_returns)
        assert np.all(np.isfinite(result.values))

    def test_different_window(self):
        calc5 = RollingMetricsCalculator(window=5)
        returns = pd.Series(np.random.normal(0.01, 0.05, 20))
        result = calc5.rolling_sharpe(returns)
        assert len(result) == 20 - 5 + 1


class TestRollingDrawdown:
    def test_returns_empty_when_insufficient_data(self, calc):
        short = pd.Series([100, 101])
        result = calc.rolling_drawdown(short)
        assert len(result) == 0

    def test_returns_series_same_length_as_input(self, calc, long_equity):
        result = calc.rolling_drawdown(long_equity)
        assert len(result) == len(long_equity)

    def test_drawdown_is_non_positive(self, calc, long_equity):
        result = calc.rolling_drawdown(long_equity)
        assert np.all(result.values <= 0.0 + 1e-10)

    def test_drawdown_at_peak_is_zero(self):
        equity = pd.Series([100, 110, 105, 120, 115])
        calc3 = RollingMetricsCalculator(window=3)
        result = calc3.rolling_drawdown(equity)
        # At index 3 (value=120), rolling max is 120, drawdown should be 0
        assert abs(result.iloc[3]) < 1e-10


class TestRollingAlphaBeta:
    def test_returns_empty_when_insufficient_data(self, calc):
        port = pd.Series([0.01, 0.02])
        bench = pd.Series([0.005, 0.015])
        alpha, beta = calc.rolling_alpha_beta(port, bench)
        assert len(alpha) == 0
        assert len(beta) == 0

    def test_returns_correct_length(self, calc):
        np.random.seed(42)
        port = pd.Series(np.random.normal(0.01, 0.05, 20))
        bench = pd.Series(np.random.normal(0.008, 0.04, 20))
        alpha, beta = calc.rolling_alpha_beta(port, bench)
        assert len(alpha) == 20 - calc.window + 1
        assert len(beta) == 20 - calc.window + 1

    def test_beta_near_one_for_identical_returns(self):
        calc12 = RollingMetricsCalculator(window=12)
        ret = pd.Series(np.random.normal(0.01, 0.05, 24))
        alpha, beta = calc12.rolling_alpha_beta(ret, ret)
        # Beta should be ~1.0 for identical series
        assert np.allclose(beta.values, 1.0, atol=0.01)

    def test_zero_std_benchmark(self, calc):
        port = pd.Series([0.01, 0.02, 0.03, 0.01, 0.02])
        bench = pd.Series([0.0, 0.0, 0.0, 0.0, 0.0])
        alpha, beta = calc.rolling_alpha_beta(port, bench)
        assert np.all(beta.values == 0.0)

    def test_custom_window(self):
        np.random.seed(42)
        port = pd.Series(np.random.normal(0.01, 0.05, 20))
        bench = pd.Series(np.random.normal(0.008, 0.04, 20))
        calc = RollingMetricsCalculator(window=12)
        alpha, beta = calc.rolling_alpha_beta(port, bench, window=6)
        assert len(alpha) == 20 - 6 + 1


class TestComputeAll:
    def test_basic_compute_all(self, calc):
        monthly = [0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.015, -0.005, 0.02, 0.01, -0.01, 0.03, 0.02, -0.02, 0.01]
        equity = [100 * (1 + r) for r in [0] + monthly]
        result = RollingMetricsCalculator(window=3).compute_all(monthly, equity)
        assert "rolling_sharpe" in result
        assert "rolling_drawdown" in result
        assert len(result["rolling_sharpe"]) > 0
        assert len(result["rolling_drawdown"]) > 0

    def test_compute_all_with_benchmark(self, calc):
        monthly = [0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.015, -0.005, 0.02, 0.01, -0.01, 0.03, 0.02, -0.02, 0.01]
        bench = [0.005, -0.01, 0.02, 0.005, -0.005, 0.01, 0.01, -0.002, 0.015, 0.008, -0.005, 0.02, 0.015, -0.01, 0.008]
        equity = [100 * (1 + r) for r in [0] + monthly]
        result = RollingMetricsCalculator(window=3).compute_all(monthly, equity, bench)
        assert "rolling_alpha" in result
        assert "rolling_beta" in result
        assert len(result["rolling_alpha"]) > 0
        assert len(result["rolling_beta"]) > 0

    def test_compute_all_without_benchmark(self):
        monthly = [0.01, -0.02, 0.03, 0.01, -0.01, 0.02, 0.015, -0.005, 0.02, 0.01, -0.01, 0.03]
        equity = [100 * (1 + r) for r in [0] + monthly]
        result = RollingMetricsCalculator(window=3).compute_all(monthly, equity, benchmark_returns=None)
        assert "rolling_alpha" not in result
        assert "rolling_beta" not in result
