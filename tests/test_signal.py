"""信号生成器测试"""
import pytest
from datetime import date
from financial_analyzer.quant.engine.signal import SignalGenerator
from financial_analyzer.quant.models import StockInfo, TradeList


@pytest.fixture
def optimizer_output():
    return [
        StockInfo("A", "股A", "白酒"),
        StockInfo("D", "股D", "银行"),
        StockInfo("E", "股E", "电池"),
        StockInfo("B", "股B", "白酒"),
        StockInfo("F", "股F", "银行"),
    ]


@pytest.fixture
def scores():
    return {
        "A": 2.0, "D": 1.3, "E": 1.2, "B": 1.8, "F": 1.0,
        "G": 0.8, "H": 0.5, "C": 1.5,
        "OLD1": 0.3, "OLD2": -0.2,
    }


class TestSignalGenerator:
    def test_generate_buy_signals(self, optimizer_output, scores):
        gen = SignalGenerator()
        trade_list = gen.generate(
            optimized_stocks=optimizer_output,
            scores=scores,
            current_holdings={"OLD1", "OLD2"},
            universe="沪深300",
        )
        assert isinstance(trade_list, TradeList)
        assert trade_list.universe == "沪深300"

    def test_sell_signals_for_dropped_stocks(self, optimizer_output, scores):
        gen = SignalGenerator()
        trade_list = gen.generate(
            optimized_stocks=optimizer_output,
            scores=scores,
            current_holdings={"OLD1", "OLD2"},
            universe="沪深300",
        )
        sell_codes = [s.stock_code for s in trade_list.sells]
        assert "OLD1" in sell_codes
        assert "OLD2" in sell_codes

    def test_no_holdings_all_buys(self, optimizer_output, scores):
        gen = SignalGenerator()
        trade_list = gen.generate(
            optimized_stocks=optimizer_output,
            scores=scores,
            current_holdings=set(),
            universe="沪深300",
        )
        assert len(trade_list.sells) == 0
        assert len(trade_list.buys) == len(optimizer_output)

    def test_equal_weights(self, optimizer_output, scores):
        gen = SignalGenerator()
        trade_list = gen.generate(
            optimized_stocks=optimizer_output,
            scores=scores,
            current_holdings=set(),
            universe="中证500",
        )
        for signal in trade_list.buys:
            assert 0.15 <= signal.target_weight <= 0.25
