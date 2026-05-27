"""加权打分器测试"""
import pytest
from datetime import date
from financial_analyzer.quant.engine.scorer import WeightedScorer
from financial_analyzer.quant.models import FactorMatrix, FactorConfig


def make_matrix():
    m = FactorMatrix(date=date(2026, 5, 29))
    m.stocks = ["A", "B", "C"]
    m.scores = {
        "A": {"pe": 0.5, "roe": 1.0, "momentum_3m": -0.3},
        "B": {"pe": -0.2, "roe": 0.5, "momentum_3m": 1.5},
        "C": {"pe": 1.2, "roe": -0.8, "momentum_3m": 0.2},
    }
    return m

def make_configs():
    return [
        FactorConfig(name="pe", label="PE", category="value", weight=1.0),
        FactorConfig(name="roe", label="ROE", category="quality", weight=1.0),
        FactorConfig(name="momentum_3m", label="3月动量", category="momentum", weight=0.5),
    ]

class TestWeightedScorer:
    def test_equal_weights(self):
        scorer = WeightedScorer(make_configs())
        scores = scorer.score(make_matrix())
        assert len(scores) == 3
        assert "A" in scores

    def test_custom_weights(self):
        configs = [
            FactorConfig(name="pe", label="PE", category="value", weight=2.0),
            FactorConfig(name="roe", label="ROE", category="quality", weight=0.5),
        ]
        scorer = WeightedScorer(configs)
        scores = scorer.score(make_matrix())
        # A: (2*0.5 + 0.5*1.0) / (2.0+0.5) = 1.5/2.5 = 0.6
        assert abs(scores["A"] - 0.6) < 1e-10

    def test_disabled_factor(self):
        configs = [
            FactorConfig(name="pe", label="PE", category="value", weight=1.0),
            FactorConfig(name="roe", label="ROE", category="quality", weight=1.0, enabled=False),
        ]
        scorer = WeightedScorer(configs)
        scores = scorer.score(make_matrix())
        # A: only pe: 0.5
        assert abs(scores["A"] - 0.5) < 1e-10

    def test_missing_factor_score(self):
        m = make_matrix()
        del m.scores["A"]["momentum_3m"]
        scorer = WeightedScorer(make_configs())
        scores = scorer.score(m)
        assert "A" in scores
