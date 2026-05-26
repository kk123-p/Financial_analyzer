"""约束优化器测试"""
import pytest
from datetime import date
from financial_analyzer.quant.engine.optimizer import ConstraintOptimizer
from financial_analyzer.quant.models import StockInfo


@pytest.fixture
def ranked_stocks():
    return [
        StockInfo("A", "股A", "白酒"),
        StockInfo("B", "股B", "白酒"),
        StockInfo("C", "股C", "白酒"),
        StockInfo("D", "股D", "银行"),
        StockInfo("E", "股E", "电池"),
        StockInfo("F", "股F", "银行"),
        StockInfo("G", "股G", "半导体"),
        StockInfo("H", "股H", "白酒"),
    ]

@pytest.fixture
def scores():
    return {"A": 2.0, "B": 1.8, "C": 1.5, "D": 1.3, "E": 1.2, "F": 1.0, "G": 0.8, "H": 0.5}

class TestConstraintOptimizer:
    def test_min_industries_constraint(self, ranked_stocks, scores):
        opt = ConstraintOptimizer(
            min_stocks=5, max_stocks=8,
            min_industries=3,
            max_industry_weight=0.40,
        )
        result = opt.optimize(ranked_stocks, scores)
        codes = [s.code for s in result]
        industries = set(s.industry for s in result)
        assert len(industries) >= 3
        assert 5 <= len(result) <= 8

    def test_max_industry_weight(self, ranked_stocks, scores):
        opt = ConstraintOptimizer(
            min_stocks=5, max_stocks=8,
            min_industries=1,
            max_industry_weight=0.40,
        )
        result = opt.optimize(ranked_stocks, scores)
        alcohol_count = sum(1 for s in result if s.industry == "白酒")
        max_allowed = int(len(result) * 0.40)
        assert alcohol_count <= max_allowed + 1  # 舍入容差

    def test_max_stocks_limit(self, ranked_stocks, scores):
        opt = ConstraintOptimizer(max_stocks=4, min_stocks=3, min_industries=1)
        result = opt.optimize(ranked_stocks, scores)
        assert len(result) <= 4

    def test_returns_empty_for_insufficient_input(self):
        opt = ConstraintOptimizer(min_industries=3)
        result = opt.optimize([], {})
        assert result == []
