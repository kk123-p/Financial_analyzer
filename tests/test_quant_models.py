"""quant models 单元测试"""
import pytest
from datetime import date
from financial_analyzer.quant.models import (
    StockInfo, FactorValue, FactorMatrix, SignalResult,
    TradeList, FactorConfig
)


class TestStockInfo:
    def test_create_valid(self):
        s = StockInfo(code="600519", name="贵州茅台", industry="白酒", market="主板")
        assert s.code == "600519"
        assert s.industry == "白酒"

    def test_optional_fields_default(self):
        s = StockInfo(code="000001", name="平安银行")
        assert s.industry == ""
        assert s.market == ""
        assert s.is_st is False
        assert s.is_suspended is False
        assert s.listed_date is None


class TestFactorValue:
    def test_create(self):
        fv = FactorValue(stock_code="600519", factor_name="pe", raw_value=15.2, z_score=0.5)
        assert fv.raw_value == 15.2
        assert fv.z_score == 0.5

    def test_default_values(self):
        fv = FactorValue(stock_code="000001", factor_name="roe")
        assert fv.raw_value is None
        assert fv.z_score is None
        assert fv.percentile is None


class TestFactorMatrix:
    def test_empty_matrix(self):
        m = FactorMatrix(date=date(2026, 5, 29))
        assert m.date == date(2026, 5, 29)
        assert len(m.stocks) == 0

    def test_add_stock_scores(self):
        m = FactorMatrix(date=date(2026, 5, 29))
        m.stocks = ["600519", "000858"]
        m.scores = {
            "600519": {"pe": 1.2, "roe": 0.8},
            "000858": {"pe": -0.5, "roe": 1.5},
        }
        assert m.get_score("600519", "pe") == 1.2
        assert m.get_score("000858", "roe") == 1.5
        assert m.get_score("600519", "nonexist") is None

    def test_composite_score(self):
        m = FactorMatrix(date=date(2026, 5, 29))
        m.stocks = ["600519"]
        m.scores = {"600519": {"pe": 1.0, "roe": 2.0}}
        weights = {"pe": 0.5, "roe": 0.5}
        result = m.composite_score("600519", weights)
        assert result == 1.5


class TestSignalResult:
    def test_create(self):
        sr = SignalResult(
            stock_code="600519",
            stock_name="贵州茅台",
            action="buy",
            composite_score=1.25,
            target_weight=0.15,
            reason="因子综合得分排名第3",
        )
        assert sr.action == "buy"
        assert sr.composite_score == 1.25


class TestTradeList:
    def test_create(self):
        tl = TradeList(
            date=date(2026, 5, 29),
            universe="沪深300",
            signals=[
                SignalResult("600519", "贵州茅台", "buy", 1.25, 0.15, "排名第3"),
                SignalResult("000858", "五粮液", "sell", 0.1, 0.0, "排名跌出前30"),
            ],
        )
        assert len(tl.buys) == 1
        assert len(tl.sells) == 1

    def test_empty_trade_list(self):
        tl = TradeList(date=date(2026, 5, 29), universe="沪深300")
        assert tl.buys == []
        assert tl.sells == []
