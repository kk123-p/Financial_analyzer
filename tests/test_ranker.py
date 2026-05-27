"""排名与硬过滤测试"""
import pytest
from datetime import date
from financial_analyzer.quant.engine.ranker import Ranker
from financial_analyzer.quant.models import StockInfo


@pytest.fixture
def stocks():
    return [
        StockInfo("A", "股A", "白酒", is_st=False, is_suspended=False),
        StockInfo("B", "股B", "银行", is_st=True, is_suspended=False),
        StockInfo("C", "股C", "电池", is_st=False, is_suspended=True),
        StockInfo("D", "股D", "银行", is_st=False, is_suspended=False),
        StockInfo("E", "股E", "白酒", is_st=False, is_suspended=False),
    ]

@pytest.fixture
def scores():
    return {"A": 1.5, "B": 0.8, "C": 2.0, "D": -0.5, "E": 0.3}

class TestRanker:
    def test_rank_and_filter_top_n(self, stocks, scores):
        ranker = Ranker(top_n=3)

        ranked = ranker.rank(scores, stocks)
        assert len(ranked) <= 3
        codes = [s.code for s in ranked]
        assert "B" not in codes  # ST
        assert "C" not in codes  # suspended
        assert codes == ["A", "E", "D"]  # by score desc

    def test_max_price_filter(self, stocks, scores):
        ranker = Ranker(top_n=5, max_price=15.0)
        prices = {"A": 10.0, "B": 8.0, "C": 20.0, "D": 12.0, "E": 14.0}

        ranked = ranker.rank(scores, stocks, prices=prices)
        codes = [s.code for s in ranked]
        assert "C" not in codes  # 20 > 15

    def test_empty_scores(self, stocks):
        ranker = Ranker()
        ranked = ranker.rank({}, stocks)
        assert ranked == []
