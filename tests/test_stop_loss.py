"""止盈止损模块测试"""
import pytest
from financial_analyzer.quant.risk.stop_loss import StopLossManager


class TestStockStopLoss:
    def test_no_trigger_within_range(self):
        slm = StopLossManager(stop_loss_pct=-10.0, take_profit_pct=30.0)
        assert slm.check_stock_stop(100.0, 105.0) is None
        assert slm.check_stock_stop(100.0, 90.1) is None
        assert slm.check_stock_stop(100.0, 129.0) is None

    def test_stop_loss_triggered(self):
        slm = StopLossManager(stop_loss_pct=-10.0, take_profit_pct=30.0)
        assert slm.check_stock_stop(100.0, 89.0) == "stop_loss"
        assert slm.check_stock_stop(100.0, 90.0) == "stop_loss"

    def test_take_profit_triggered(self):
        slm = StopLossManager(stop_loss_pct=-10.0, take_profit_pct=30.0)
        assert slm.check_stock_stop(100.0, 130.0) == "take_profit"
        assert slm.check_stock_stop(100.0, 150.0) == "take_profit"

    def test_zero_cost_price(self):
        slm = StopLossManager(stop_loss_pct=-10.0, take_profit_pct=30.0)
        assert slm.check_stock_stop(0.0, 100.0) is None

    def test_custom_thresholds(self):
        slm = StopLossManager(stop_loss_pct=-5.0, take_profit_pct=20.0)
        assert slm.check_stock_stop(100.0, 94.0) == "stop_loss"
        assert slm.check_stock_stop(100.0, 96.0) is None
        assert slm.check_stock_stop(100.0, 120.0) == "take_profit"
        assert slm.check_stock_stop(100.0, 119.0) is None


class TestPortfolioStopLoss:
    def test_no_portfolio_stop(self):
        slm = StopLossManager(stop_loss_pct=-10.0, take_profit_pct=30.0)
        assert slm.check_portfolio_stop(20.0) is False

    def test_portfolio_stop_not_triggered(self):
        slm = StopLossManager(
            stop_loss_pct=-10.0, take_profit_pct=30.0, portfolio_stop_pct=20.0
        )
        assert slm.check_portfolio_stop(19.0) is False

    def test_portfolio_stop_triggered(self):
        slm = StopLossManager(
            stop_loss_pct=-10.0, take_profit_pct=30.0, portfolio_stop_pct=20.0
        )
        assert slm.check_portfolio_stop(20.0) is True
        assert slm.check_portfolio_stop(25.0) is True
