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


class TestComputeCorrelationMatrix:
    def test_basic(self):
        """构造已知相关性的因子数据，验证矩阵正确"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]

        # 因子A和B完全正相关（都等于索引），因子C与A负相关
        for month in range(1, 4):
            factor_values = {}
            for i, s in enumerate(stocks):
                factor_values[s] = {
                    "factor_a": float(i),
                    "factor_b": float(i) * 2.0,  # 与A完全正相关
                    "factor_c": float(n - i),  # 与A完全负相关
                }
            analyzer.store_monthly_matrix(
                factor_values, ref_date=date(2025, month, 28)
            )

        labels, matrix = analyzer.compute_correlation_matrix()
        assert len(labels) == 3
        assert len(matrix) == 3
        assert len(matrix[0]) == 3

        # 找到各因子的索引
        idx = {lbl.replace(" [高相关]", ""): i for i, lbl in enumerate(labels)}

        # factor_a 与 factor_b: 完全正相关 -> 接近 1.0
        assert matrix[idx["factor_a"]][idx["factor_b"]] > 0.95
        # factor_a 与 factor_c: 完全负相关 -> 接近 -1.0
        assert matrix[idx["factor_a"]][idx["factor_c"]] < -0.95
        # 对角线应为 1.0
        for i in range(3):
            assert abs(matrix[i][i] - 1.0) < 1e-4

    def test_high_correlation_label(self):
        """高相关因子在 labels 中标记"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]

        for month in range(1, 4):
            factor_values = {}
            for i, s in enumerate(stocks):
                factor_values[s] = {
                    "x": float(i),
                    "y": float(i) * 1.5,  # 高相关
                    "z": float(n - i) * 0.01 + float(i) * 0.99,  # 弱相关
                }
            analyzer.store_monthly_matrix(
                factor_values, ref_date=date(2025, month, 28)
            )

        labels, _ = analyzer.compute_correlation_matrix()
        label_map = {lbl.replace(" [高相关]", ""): lbl for lbl in labels}
        # x 和 y 完全正相关，应标记
        assert "[高相关]" in label_map["x"]
        assert "[高相关]" in label_map["y"]

    def test_empty(self):
        """无数据时返回空"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        labels, matrix = analyzer.compute_correlation_matrix()
        assert labels == []
        assert matrix == []

    def test_reset_clears_matrices(self):
        """reset 清除 _monthly_matrices"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 20
        stocks = [f"S{i:04d}" for i in range(n)]
        factor_values = {s: {"a": 1.0, "b": 2.0} for s in stocks}
        analyzer.store_monthly_matrix(factor_values, ref_date=date(2025, 1, 31))
        assert len(analyzer._monthly_matrices) == 1
        analyzer.reset()
        assert len(analyzer._monthly_matrices) == 0


class TestComputeAnnualPerformance:
    def test_basic(self):
        """验证年度分组和多空收益：单调递增因子应产生正 long_short"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 100
        stocks = [f"S{i:04d}" for i in range(n)]

        # 3 months of data in the same year
        for month in range(1, 4):
            factor_values = {s: {"momentum": float(i)} for i, s in enumerate(stocks)}
            # Returns correlated with factor (higher factor -> higher return)
            fwd_returns = {s: float(i) * 0.001 for i, s in enumerate(stocks)}
            analyzer.store_monthly_matrix(
                factor_values,
                ref_date=date(2025, month * 2 + 1, 28),
                market_returns=fwd_returns,
            )

        monthly_returns = [
            (date(2025, 3, 28), {s: float(i) * 0.001 for i, s in enumerate(stocks)}),
            (date(2025, 5, 28), {s: float(i) * 0.001 for i, s in enumerate(stocks)}),
            (date(2025, 7, 28), {s: float(i) * 0.001 for i, s in enumerate(stocks)}),
        ]

        result = analyzer.compute_annual_performance(monthly_returns)
        assert "momentum" in result
        assert len(result["momentum"]) == 1
        entry = result["momentum"][0]
        assert entry["year"] == 2025
        # Q5 (top) should have higher return than Q1 (bottom)
        assert entry["q5_return"] > entry["q1_return"]
        assert entry["long_short_return"] > 0

    def test_empty_returns(self):
        """无收益率数据时返回空"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]
        factor_values = {s: {"pe": float(i)} for i, s in enumerate(stocks)}
        analyzer.store_monthly_matrix(factor_values, ref_date=date(2025, 1, 31))

        result = analyzer.compute_annual_performance([])
        assert result == {}

    def test_multi_year(self):
        """多年数据应按年度分别计算"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 60
        stocks = [f"S{i:04d}" for i in range(n)]

        for year in [2024, 2025]:
            for month in [3, 6]:
                factor_values = {s: {"pe": float(i)} for i, s in enumerate(stocks)}
                fwd_returns = {s: float(i) * 0.001 for i, s in enumerate(stocks)}
                analyzer.store_monthly_matrix(
                    factor_values,
                    ref_date=date(year, month, 28),
                    market_returns=fwd_returns,
                )

        monthly_returns = [
            (date(2024, 3, 28), {s: float(i) * 0.001 for i, s in enumerate(stocks)}),
            (date(2024, 6, 28), {s: float(i) * 0.001 for i, s in enumerate(stocks)}),
            (date(2025, 3, 28), {s: float(i) * 0.001 for i, s in enumerate(stocks)}),
            (date(2025, 6, 28), {s: float(i) * 0.001 for i, s in enumerate(stocks)}),
        ]

        result = analyzer.compute_annual_performance(monthly_returns)
        assert "pe" in result
        assert len(result["pe"]) == 2
        years = [e["year"] for e in result["pe"]]
        assert 2024 in years
        assert 2025 in years

    def test_quintile_monotonic(self):
        """正相关因子的 quintile 收益应单调递增"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 100
        stocks = [f"S{i:04d}" for i in range(n)]
        factor_values = {s: {"alpha": float(i)} for i, s in enumerate(stocks)}
        fwd_returns = {s: float(i) * 0.002 for i, s in enumerate(stocks)}

        analyzer.store_monthly_matrix(
            factor_values, ref_date=date(2025, 6, 30), market_returns=fwd_returns,
        )
        monthly_returns = [(date(2025, 6, 30), fwd_returns)]

        result = analyzer.compute_annual_performance(monthly_returns)
        entry = result["alpha"][0]
        q_returns = [entry[f"q{i}_return"] for i in range(1, 6)]
        for i in range(len(q_returns) - 1):
            assert q_returns[i] <= q_returns[i + 1], (
                f"Q{i+1} return {q_returns[i]} > Q{i+2} return {q_returns[i+1]}"
            )


class TestComputeCompositeScore:
    def test_basic(self):
        """验证综合评分计算和排序"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]

        # Set up IC history for two factors
        from financial_analyzer.quant.models import ICRecord

        ic_values_a = [0.08, 0.10, 0.06, 0.09, 0.07]
        ic_values_b = [0.02, 0.03, 0.01, 0.02, 0.03]

        for i, (ica, icb) in enumerate(zip(ic_values_a, ic_values_b)):
            analyzer._ic_history.setdefault("factor_a", []).append(
                ICRecord(date=date(2025, i + 1, 28), factor_name="factor_a",
                         ic_value=ica, n_stocks=n)
            )
            analyzer._ic_history.setdefault("factor_b", []).append(
                ICRecord(date=date(2025, i + 1, 28), factor_name="factor_b",
                         ic_value=icb, n_stocks=n)
            )

        # Store monthly matrices with low correlation between factors
        # factor_a is linear, factor_b is sinusoidal -> low Spearman correlation
        for month in range(1, 6):
            factor_values = {}
            for i, s in enumerate(stocks):
                factor_values[s] = {
                    "factor_a": float(i),
                    "factor_b": float(np.sin(i * 0.628) * 25 + 25),  # oscillating, low corr
                }
            analyzer.store_monthly_matrix(
                factor_values, ref_date=date(2025, month, 28)
            )

        result = analyzer.compute_composite_score()
        assert len(result) == 2

        # factor_a has higher IC, should rank first
        assert result[0]["factor"] == "factor_a"
        assert result[0]["score"] > result[1]["score"]

        # Verify fields exist
        for entry in result:
            assert "factor" in entry
            assert "ic_mean" in entry
            assert "ir" in entry
            assert "max_corr" in entry
            assert "score" in entry

    def test_empty_ic_history(self):
        """无 IC 历史时返回空列表"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        result = analyzer.compute_composite_score()
        assert result == []

    def test_high_corr_penalizes_score(self):
        """高相关因子应被惩罚（score 降低）"""
        analyzer = FactorAnalyzer(min_sample_size=5)
        n = 50
        stocks = [f"S{i:04d}" for i in range(n)]
        from financial_analyzer.quant.models import ICRecord

        # Two factors with identical IC stats
        for i in range(5):
            analyzer._ic_history.setdefault("x", []).append(
                ICRecord(date=date(2025, i + 1, 28), factor_name="x",
                         ic_value=0.06, n_stocks=n)
            )
            analyzer._ic_history.setdefault("y", []).append(
                ICRecord(date=date(2025, i + 1, 28), factor_name="y",
                         ic_value=0.06, n_stocks=n)
            )

        # x and y are perfectly correlated
        for month in range(1, 6):
            factor_values = {s: {"x": float(i), "y": float(i)} for i, s in enumerate(stocks)}
            analyzer.store_monthly_matrix(factor_values, ref_date=date(2025, month, 28))

        result = analyzer.compute_composite_score()
        # Both should have max_corr close to 1.0, penalizing the score
        for entry in result:
            assert entry["max_corr"] > 0.9
            # score = IC_mean * IR * (1 - max_corr) should be near 0
            assert abs(entry["score"]) < 0.01
