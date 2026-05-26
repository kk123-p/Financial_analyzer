"""低波动因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.low_vol import (
    Volatility60D, MaxDrawdown120D
)
from financial_analyzer.quant.factors.base import FactorInput


class TestVolatility60D:
    def test_normal(self):
        daily = pd.DataFrame({"close": [10.0, 10.1, 9.9, 10.0, 10.2] * 20})
        inp = FactorInput("600519", daily=daily)
        result = Volatility60D().compute(inp)
        assert result is not None
        assert result <= 0  # 低波动得分更高 (取负)

    def test_insufficient_data(self):
        daily = pd.DataFrame({"close": [10.0]})
        inp = FactorInput("600519", daily=daily)
        result = Volatility60D().compute(inp)
        assert result is None

    def test_no_daily(self):
        result = Volatility60D().compute(FactorInput("600519"))
        assert result is None


class TestMaxDrawdown120D:
    def test_normal(self):
        prices = [10.0] * 30 + [12.0] * 30 + [8.0] * 30 + [9.0] * 30
        daily = pd.DataFrame({"close": prices})
        inp = FactorInput("600519", daily=daily)
        result = MaxDrawdown120D().compute(inp)
        assert result is not None
        assert result >= -1.0
