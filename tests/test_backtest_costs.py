"""交易成本精细化测试"""
from datetime import date
from unittest.mock import MagicMock

import pytest

from financial_analyzer.quant.backtest.engine import BacktestEngine


def _make_engine(slippage_pct=0.1, stamp_tax=True, commission_rate=0.001):
    engine = BacktestEngine(
        universe_manager=MagicMock(),
        data_fetcher=MagicMock(),
        factor_matrix_builder=MagicMock(),
        normalizer=MagicMock(),
        scorer=MagicMock(),
        ranker=MagicMock(),
        optimizer=MagicMock(),
        signal_generator=MagicMock(cash_reserve=0.0),
        commission_rate=commission_rate,
        slippage_pct=slippage_pct,
        stamp_tax=stamp_tax,
    )
    engine._reset_cost_tracking()
    return engine


class TestSlippageBuy:
    def test_buy_price_includes_slippage(self):
        engine = _make_engine(slippage_pct=0.1)
        trade_list = MagicMock()
        trade_list.sells = []
        signal = MagicMock(stock_code="000001.SZ")
        trade_list.buys = [signal]

        holdings = {}
        cash = 100000.0
        prices = {"000001.SZ": 10.0}

        engine._execute_trades(trade_list, holdings, cash, prices, date(2024, 1, 31))

        # exec_price = 10.0 * (1 + 0.1/100) = 10.01
        # shares = int(100000 / 10.01 / 100) * 100 = 9900
        # cost = 9900 * 10.01 = 99099.0
        # commission = 99099.0 * 0.001 = 99.099
        # slippage = 9900 * (10.01 - 10.0) = 9900 * 0.01 = 99.0
        assert holdings["000001.SZ"] == 9900
        assert abs(engine._total_slippage_cost - 99.0) < 0.01

    def test_buy_zero_slippage(self):
        engine = _make_engine(slippage_pct=0.0)
        trade_list = MagicMock()
        trade_list.sells = []
        signal = MagicMock(stock_code="000001.SZ")
        trade_list.buys = [signal]

        holdings = {}
        cash = 100000.0
        prices = {"000001.SZ": 10.0}

        engine._execute_trades(trade_list, holdings, cash, prices, date(2024, 1, 31))

        assert engine._total_slippage_cost == 0.0


class TestSlippageSell:
    def test_sell_price_reduced_by_slippage(self):
        engine = _make_engine(slippage_pct=0.1)
        trade_list = MagicMock()
        signal = MagicMock(stock_code="000001.SZ")
        trade_list.sells = [signal]
        trade_list.buys = []

        holdings = {"000001.SZ": 1000}
        cash = 0.0
        prices = {"000001.SZ": 10.0}

        cash_after = engine._execute_trades(trade_list, holdings, cash, prices, date(2024, 1, 31))

        # exec_price = 10.0 * (1 - 0.1/100) = 9.99
        # proceeds = 1000 * 9.99 = 9990.0
        # commission = 9990.0 * 0.001 = 9.99
        # stamp_tax = 9990.0 * 0.0005 = 4.995
        # slippage = 1000 * (10.0 - 9.99) = 10.0
        assert abs(engine._total_slippage_cost - 10.0) < 0.01
        expected_cash = 9990.0 - 9.99 - 4.995
        assert abs(cash_after - expected_cash) < 0.01


class TestStampTax:
    def test_stamp_tax_applied_on_sell(self):
        engine = _make_engine(stamp_tax=True, slippage_pct=0.0)
        trade_list = MagicMock()
        signal = MagicMock(stock_code="000001.SZ")
        trade_list.sells = [signal]
        trade_list.buys = []

        holdings = {"000001.SZ": 1000}
        cash = 0.0
        prices = {"000001.SZ": 10.0}

        cash_after = engine._execute_trades(trade_list, holdings, cash, prices, date(2024, 1, 31))

        # proceeds = 1000 * 10.0 = 10000.0
        # commission = 10000.0 * 0.001 = 10.0
        # stamp_tax = 10000.0 * 0.0005 = 5.0
        expected_stamp = 10000.0 * 0.0005
        assert abs(engine._total_stamp_tax - expected_stamp) < 0.01
        expected_cash = 10000.0 - 10.0 - 5.0
        assert abs(cash_after - expected_cash) < 0.01

    def test_no_stamp_tax_when_disabled(self):
        engine = _make_engine(stamp_tax=False, slippage_pct=0.0)
        trade_list = MagicMock()
        signal = MagicMock(stock_code="000001.SZ")
        trade_list.sells = [signal]
        trade_list.buys = []

        holdings = {"000001.SZ": 1000}
        cash = 0.0
        prices = {"000001.SZ": 10.0}

        cash_after = engine._execute_trades(trade_list, holdings, cash, prices, date(2024, 1, 31))

        assert engine._total_stamp_tax == 0.0
        # Only commission deducted
        expected_cash = 10000.0 - 10.0
        assert abs(cash_after - expected_cash) < 0.01


class TestCommission:
    def test_commission_tracked(self):
        engine = _make_engine(commission_rate=0.001, slippage_pct=0.0, stamp_tax=False)
        trade_list = MagicMock()
        signal = MagicMock(stock_code="000001.SZ")
        trade_list.sells = [signal]
        trade_list.buys = []

        holdings = {"000001.SZ": 1000}
        cash = 0.0
        prices = {"000001.SZ": 10.0}

        engine._execute_trades(trade_list, holdings, cash, prices, date(2024, 1, 31))

        expected_commission = 10000.0 * 0.001
        assert abs(engine._total_commission - expected_commission) < 0.01


class TestCostBreakdown:
    def test_cost_breakdown_fields(self):
        from financial_analyzer.quant.backtest.models import BacktestResult

        result = BacktestResult(
            start_date="20230101",
            end_date="20231231",
            initial_capital=100000,
            final_value=105000,
            cost_breakdown={
                "commission": 100.0,
                "slippage_cost": 50.0,
                "stamp_tax": 25.0,
                "total_cost": 175.0,
            },
        )
        assert result.cost_breakdown["commission"] == 100.0
        assert result.cost_breakdown["total_cost"] == 175.0

    def test_cost_breakdown_default_empty(self):
        from financial_analyzer.quant.backtest.models import BacktestResult

        result = BacktestResult(
            start_date="20230101",
            end_date="20231231",
            initial_capital=100000,
            final_value=100000,
        )
        assert result.cost_breakdown == {}
