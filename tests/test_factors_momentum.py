"""动量因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.momentum import (
    PriceMomentum3M, PriceMomentum6M, PriceMomentum12M
)
from financial_analyzer.quant.factors.base import FactorInput


def make_daily_prices(prices: list):
    return pd.DataFrame({"close": prices})


class TestPriceMomentum3M:
    def test_positive_momentum(self):
        daily = make_daily_prices([12.0, 11.0, 10.5, 10.0])
        inp = FactorInput("600519", daily=daily)
        result = PriceMomentum3M().compute(inp)
        assert result == pytest.approx(0.20, rel=1e-4)  # (12-10)/10

    def test_insufficient_data(self):
        daily = make_daily_prices([10.0])
        inp = FactorInput("600519", daily=daily)
        result = PriceMomentum3M().compute(inp)
        assert result is None

    def test_no_daily(self):
        result = PriceMomentum3M().compute(FactorInput("600519"))
        assert result is None

    def test_zero_start_price(self):
        daily = make_daily_prices([10.0, 0])
        inp = FactorInput("600519", daily=daily)
        result = PriceMomentum3M().compute(inp)
        assert result is None


class TestPriceMomentum12M:
    def test_annual_momentum(self):
        daily = make_daily_prices([15.0, 14.0, 13.0, 12.0, 10.0])
        inp = FactorInput("600519", daily=daily)
        result = PriceMomentum12M().compute(inp)
        assert result == pytest.approx(0.50, rel=1e-4)
