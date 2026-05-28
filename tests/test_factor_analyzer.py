"""FactorAnalyzer 单元测试"""
import pytest
from datetime import date
import numpy as np

from financial_analyzer.quant.models import FactorMatrix
from financial_analyzer.quant.engine.factor_analyzer import FactorAnalyzer


def _build_matrix(factor_values: dict[str, dict[str, float]]) -> FactorMatrix:
    """辅助：从 {factor: {stock: val}} 构建 FactorMatrix"""
    m = FactorMatrix(date=date(2025, 1, 31))
    all_stocks = set()
    for vals in factor_values.values():
        all_stocks.update(vals.keys())
    m.stocks = list(all_stocks)
    m.scores = {}
    for stock in all_stocks:
        m.scores[stock] = {}
        for fname, vals in factor_values.items():
            if stock in vals:
                m.scores[stock][fname] = vals[stock]
    return m


class TestComputeMonthlyICBasic:
    def test_basic(self):
        """构造已知单调递增数据，验证 IC 接近 1.0"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]
        factor_vals = {s: float(i) for i, s in enumerate(stocks)}
        forward_returns = {s: float(i) * 0.01 for i, s in enumerate(stocks)}
        matrix = _build_matrix({"pe": factor_vals})
        result = analyzer.compute_monthly_ic(matrix, forward_returns, ref_date=date(2025, 1, 31))
        assert result["pe"] is not None
        assert result["pe"] > 0.95

    def test_negative_correlation(self):
        """构造单调递减数据，验证 IC 接近 -1.0"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]
        factor_vals = {s: float(i) for i, s in enumerate(stocks)}
        forward_returns = {s: -float(i) * 0.01 for i, s in enumerate(stocks)}
        matrix = _build_matrix({"pe": factor_vals})
        result = analyzer.compute_monthly_ic(matrix, forward_returns, ref_date=date(2025, 1, 31))
        assert result["pe"] is not None
        assert result["pe"] < -0.95

    def test_no_correlation(self):
        """构造无相关数据，验证 IC 接近 0"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 100
        stocks = [f"S{i:04d}" for i in range(n)]
        factor_vals = {s: float(i) for i, s in enumerate(stocks)}
        # 交替正负收益
        forward_returns = {s: 0.01 if i % 2 == 0 else -0.01 for i, s in enumerate(stocks)}
        matrix = _build_matrix({"pe": factor_vals})
        result = analyzer.compute_monthly_ic(matrix, forward_returns, ref_date=date(2025, 1, 31))
        assert result["pe"] is not None
        assert abs(result["pe"]) < 0.2


class TestComputeMonthlyICBelowThreshold:
    def test_below_threshold(self):
        """样本量 < min_sample_size 时 IC 为 None"""
        analyzer = FactorAnalyzer(min_sample_size=30)
        stocks = [f"S{i:04d}" for i in range(10)]
        factor_vals = {s: float(i) for i, s in enumerate(stocks)}
        forward_returns = {s: 0.01 for i, s in enumerate(stocks)}
        matrix = _build_matrix({"pe": factor_vals})
        result = analyzer.compute_monthly_ic(matrix, forward_returns, ref_date=date(2025, 1, 31))
        assert result["pe"] is None

    def test_constant_values(self):
        """常数因子值时 IC 为 0"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]
        factor_vals = {s: 1.0 for s in stocks}
        forward_returns = {s: float(i) * 0.01 for i, s in enumerate(stocks)}
        matrix = _build_matrix({"pe": factor_vals})
        result = analyzer.compute_monthly_ic(matrix, forward_returns, ref_date=date(2025, 1, 31))
        assert result["pe"] == 0.0


class TestComputeICSummary:
    def test_summary_basic(self):
        """累积多月 IC 后汇总统计正确"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        ic_values = [0.05, 0.03, 0.07, 0.02, 0.06]
        from financial_analyzer.quant.models import ICRecord
        for i, ic in enumerate(ic_values):
            analyzer._ic_history.setdefault("pe", []).append(
                ICRecord(date=date(2025, i+1, 28), factor_name="pe",
                         ic_value=ic, n_stocks=100)
            )
        summaries = analyzer.compute_ic_summary()
        assert "pe" in summaries
        s = summaries["pe"]
        assert s.n_months == 5
        assert abs(s.mean_ic - np.mean(ic_values)) < 1e-10
        assert abs(s.std_ic - np.std(ic_values, ddof=1)) < 1e-10
        assert s.ic_positive_pct == 1.0
        assert s.ir > 0
        assert s.t_stat > 0


class TestComputeICSummaryInsufficientMonths:
    def test_insufficient_months(self):
        """有效月数 < 3 时返回空"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        from financial_analyzer.quant.models import ICRecord
        for i in range(2):
            analyzer._ic_history.setdefault("pe", []).append(
                ICRecord(date=date(2025, i+1, 28), factor_name="pe",
                         ic_value=0.05, n_stocks=100)
            )
        summaries = analyzer.compute_ic_summary()
        assert "pe" not in summaries

    def test_insufficient_after_filtering_nan(self):
        """过滤 nan 后不足 3 个月时返回空"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        from financial_analyzer.quant.models import ICRecord
        analyzer._ic_history.setdefault("pe", []).append(
            ICRecord(date=date(2025, 1, 28), factor_name="pe",
                     ic_value=0.05, n_stocks=100)
        )
        analyzer._ic_history["pe"].append(
            ICRecord(date=date(2025, 2, 28), factor_name="pe",
                     ic_value=float('nan'), n_stocks=10)
        )
        analyzer._ic_history["pe"].append(
            ICRecord(date=date(2025, 3, 28), factor_name="pe",
                     ic_value=0.03, n_stocks=100)
        )
        summaries = analyzer.compute_ic_summary()
        assert "pe" not in summaries


class TestReset:
    def test_reset(self):
        """reset 后历史清空"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        from financial_analyzer.quant.models import ICRecord
        analyzer._ic_history.setdefault("pe", []).append(
            ICRecord(date=date(2025, 1, 28), factor_name="pe",
                     ic_value=0.05, n_stocks=100)
        )
        assert len(analyzer._ic_history) == 1
        analyzer.reset()
        assert len(analyzer._ic_history) == 0


class TestComputeMultiHorizonIC:
    def test_basic(self):
        """多周期 IC 计算正确：单调递增数据 IC 接近 1.0"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]
        factor_values = {s: {"pe": float(i)} for i, s in enumerate(stocks)}
        fwd_returns = {
            1: {s: float(i) * 0.01 for i, s in enumerate(stocks)},
            3: {s: float(i) * 0.02 for i, s in enumerate(stocks)},
        }
        result = analyzer.compute_multi_horizon_ic(
            factor_values, fwd_returns, ref_date=date(2025, 1, 31)
        )
        assert 1 in result and 3 in result
        assert result[1]["pe"] > 0.95
        assert result[3]["pe"] > 0.95
        # decay_history should have 2 records
        assert len(analyzer._decay_history["pe"]) == 2

    def test_different_factors(self):
        """不同因子独立计算"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]
        factor_values = {
            s: {"pe": float(i), "pb": -float(i)} for i, s in enumerate(stocks)
        }
        fwd_returns = {1: {s: float(i) * 0.01 for i, s in enumerate(stocks)}}
        result = analyzer.compute_multi_horizon_ic(
            factor_values, fwd_returns, ref_date=date(2025, 1, 31)
        )
        assert result[1]["pe"] > 0.95
        assert result[1]["pb"] < -0.95


class TestComputeDecayCurve:
    def test_basic(self):
        """衰减曲线汇总正确"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]

        # Run 3 months of data
        for month in range(1, 4):
            factor_values = {s: {"pe": float(i)} for i, s in enumerate(stocks)}
            fwd_returns = {
                1: {s: float(i) * 0.01 for i, s in enumerate(stocks)},
                3: {s: float(i) * 0.005 for i, s in enumerate(stocks)},
            }
            analyzer.compute_multi_horizon_ic(
                factor_values, fwd_returns, ref_date=date(2025, month, 28)
            )

        curves = analyzer.compute_decay_curve()
        assert "pe" in curves
        dc = curves["pe"]
        assert dc.factor_name == "pe"
        assert dc.horizons == [1, 3]
        assert len(dc.mean_ic_by_horizon) == 2
        assert dc.n_months_by_horizon == [3, 3]
        # IC should be high for both horizons
        assert dc.mean_ic_by_horizon[0] > 0.9
        assert dc.mean_ic_by_horizon[1] > 0.9
        assert dc.ic_positive_pct_by_horizon[0] == 1.0

    def test_empty(self):
        """无历史时返回空字典"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        curves = analyzer.compute_decay_curve()
        assert curves == {}


class TestDecayReset:
    def test_reset(self):
        """reset 清除衰减历史"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]
        factor_values = {s: {"pe": float(i)} for i, s in enumerate(stocks)}
        fwd_returns = {1: {s: float(i) * 0.01 for i, s in enumerate(stocks)}}
        analyzer.compute_multi_horizon_ic(
            factor_values, fwd_returns, ref_date=date(2025, 1, 31)
        )
        assert len(analyzer._decay_history) == 1
        analyzer.reset()
        assert len(analyzer._decay_history) == 0


class TestGetICTimeseries:
    def test_timeseries_format(self):
        """时序数据格式正确"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]
        factor_vals = {s: float(i) for i, s in enumerate(stocks)}
        forward_returns = {s: float(i) * 0.01 for i, s in enumerate(stocks)}
        matrix = _build_matrix({"pe": factor_vals})
        analyzer.compute_monthly_ic(matrix, forward_returns, ref_date=date(2025, 1, 31))
        ts = analyzer.get_ic_timeseries()
        assert "pe" in ts
        assert len(ts["pe"]) == 1
        entry = ts["pe"][0]
        assert "date" in entry
        assert "ic" in entry
        assert "n_stocks" in entry
        assert entry["date"] == "2025-01-31"
        assert entry["ic"] > 0.95
        assert entry["n_stocks"] == n
