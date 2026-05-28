"""仓位分配策略测试"""
import numpy as np
import pytest
from financial_analyzer.quant.engine.position_sizer import (
    EqualWeightSizer,
    RiskParitySizer,
    MinVarianceSizer,
    KellySizer,
    MarketCapSizer,
    SIZERS,
)


@pytest.fixture
def scores():
    return {"A": 2.0, "B": 1.5, "C": 1.0, "D": 0.5}


@pytest.fixture
def cov_matrix():
    # 4x4 正定协方差矩阵
    return np.array([
        [0.04, 0.01, 0.005, 0.002],
        [0.01, 0.03, 0.006, 0.003],
        [0.005, 0.006, 0.025, 0.004],
        [0.002, 0.003, 0.004, 0.02],
    ])


@pytest.fixture
def stock_codes():
    return ["A", "B", "C", "D"]


class TestEqualWeightSizer:
    def test_equal_weights(self, scores):
        sizer = EqualWeightSizer()
        weights = sizer.compute_weights(scores)
        assert len(weights) == 4
        for w in weights.values():
            assert abs(w - 0.25) < 1e-10
        assert abs(sum(weights.values()) - 1.0) < 1e-10

    def test_empty_scores(self):
        sizer = EqualWeightSizer()
        assert sizer.compute_weights({}) == {}

    def test_single_stock(self):
        sizer = EqualWeightSizer()
        weights = sizer.compute_weights({"A": 1.0})
        assert weights == {"A": 1.0}


class TestRiskParitySizer:
    def test_weights_sum_to_one(self, scores, cov_matrix, stock_codes):
        sizer = RiskParitySizer()
        weights = sizer.compute_weights(scores, cov_matrix, stock_codes)
        assert abs(sum(weights.values()) - 1.0) < 1e-6
        assert len(weights) == 4

    def test_all_positive(self, scores, cov_matrix, stock_codes):
        sizer = RiskParitySizer()
        weights = sizer.compute_weights(scores, cov_matrix, stock_codes)
        for w in weights.values():
            assert w >= 0

    def test_fallback_to_equal_without_cov(self, scores):
        sizer = RiskParitySizer()
        weights = sizer.compute_weights(scores)
        for w in weights.values():
            assert abs(w - 0.25) < 1e-10

    def test_low_vol_gets_higher_weight(self, cov_matrix, stock_codes):
        # D has lowest variance (0.02), should get higher weight
        sizer = RiskParitySizer()
        scores = {"A": 1.0, "B": 1.0, "C": 1.0, "D": 1.0}
        weights = sizer.compute_weights(scores, cov_matrix, stock_codes)
        assert weights["D"] > weights["A"]


class TestMinVarianceSizer:
    def test_weights_sum_to_one(self, scores, cov_matrix, stock_codes):
        sizer = MinVarianceSizer()
        weights = sizer.compute_weights(scores, cov_matrix, stock_codes)
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_all_positive(self, scores, cov_matrix, stock_codes):
        sizer = MinVarianceSizer()
        weights = sizer.compute_weights(scores, cov_matrix, stock_codes)
        for w in weights.values():
            assert w >= 0

    def test_fallback_to_equal_without_cov(self, scores):
        sizer = MinVarianceSizer()
        weights = sizer.compute_weights(scores)
        for w in weights.values():
            assert abs(w - 0.25) < 1e-10

    def test_singular_matrix_fallback(self, scores, stock_codes):
        # Singular matrix should fallback to equal weight
        singular = np.ones((4, 4))
        sizer = MinVarianceSizer()
        weights = sizer.compute_weights(scores, singular, stock_codes)
        assert abs(sum(weights.values()) - 1.0) < 1e-6


class TestKellySizer:
    def test_weights_sum_to_one(self, scores):
        sizer = KellySizer()
        weights = sizer.compute_weights(scores)
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_higher_score_gets_higher_weight(self, scores):
        sizer = KellySizer()
        weights = sizer.compute_weights(scores)
        # A has highest score, should get most weight
        assert weights["A"] > weights["B"]
        # C and D have low scores, Kelly clamps to 0
        assert weights["C"] == 0.0
        assert weights["D"] == 0.0

    def test_equal_scores_equal_weights(self):
        sizer = KellySizer()
        weights = sizer.compute_weights({"A": 1.0, "B": 1.0, "C": 1.0})
        for w in weights.values():
            assert abs(w - 1.0/3) < 1e-10

    def test_empty_scores(self):
        sizer = KellySizer()
        assert sizer.compute_weights({}) == {}


class TestMarketCapSizer:
    def test_weights_sum_to_one(self, scores):
        sizer = MarketCapSizer()
        weights = sizer.compute_weights(scores)
        assert abs(sum(weights.values()) - 1.0) < 1e-6

    def test_higher_score_gets_higher_weight(self, scores):
        sizer = MarketCapSizer()
        weights = sizer.compute_weights(scores)
        assert weights["A"] > weights["B"] > weights["C"] > weights["D"]

    def test_empty_scores(self):
        sizer = MarketCapSizer()
        assert sizer.compute_weights({}) == {}


class TestSizersRegistry:
    def test_all_sizers_registered(self):
        assert set(SIZERS.keys()) == {"equal", "risk_parity", "min_variance", "kelly", "market_cap"}

    def test_all_sizers_instantiable(self, scores):
        for name, cls in SIZERS.items():
            sizer = cls()
            weights = sizer.compute_weights(scores)
            assert abs(sum(weights.values()) - 1.0) < 1e-6, f"{name} weights don't sum to 1"
