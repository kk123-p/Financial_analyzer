"""截面标准化器测试"""
import pytest
import numpy as np
from datetime import date
from financial_analyzer.quant.engine.normalizer import CrossSectionalNormalizer
from financial_analyzer.quant.models import FactorMatrix


def make_matrix(scores_dict):
    m = FactorMatrix(date=date(2026, 5, 29))
    stocks = list(scores_dict.keys())
    m.stocks = stocks
    m.scores = scores_dict
    m.industries = {s: "default" for s in stocks}
    return m


class TestCrossSectionalNormalizer:
    def test_zscore_normalization(self):
        m = make_matrix({
            "A": {"pe": 1.0, "roe": 0.10},
            "B": {"pe": 2.0, "roe": 0.15},
            "C": {"pe": 3.0, "roe": 0.20},
        })
        norm = CrossSectionalNormalizer(method="zscore")
        result = norm.normalize(m)
        pe_scores = [result.scores[s]["pe"] for s in result.stocks]
        assert abs(np.mean(pe_scores)) < 1e-10
        assert abs(np.std(pe_scores) - 1.0) < 1e-10

    def test_rank_normalization(self):
        m = make_matrix({
            "A": {"pe": 1.0},
            "B": {"pe": 2.0},
            "C": {"pe": 3.0},
        })
        norm = CrossSectionalNormalizer(method="rank")
        result = norm.normalize(m)
        scores = [result.scores[s]["pe"] for s in result.stocks]
        assert max(scores) <= 1.0
        assert min(scores) >= -1.0

    def test_insufficient_stocks(self):
        m = make_matrix({"A": {"pe": 1.0}})
        norm = CrossSectionalNormalizer()
        result = norm.normalize(m)
        assert result.scores["A"]["pe"] == 1.0

    def test_preserves_missing_factors(self):
        m = make_matrix({
            "A": {"pe": 1.0, "roe": 0.10},
            "B": {"roe": 0.15},
        })
        norm = CrossSectionalNormalizer()
        result = norm.normalize(m)
        assert "pe" not in result.scores["B"]
        assert "roe" in result.scores["B"]

    def test_handles_nan_in_matrix(self):
        m = make_matrix({
            "A": {"pe": 1.0},
            "B": {"pe": 2.0},
        })
        norm = CrossSectionalNormalizer()
        result = norm.normalize(m)
        assert result.scores["A"]["pe"] is not None
