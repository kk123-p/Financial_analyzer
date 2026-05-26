"""情绪因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.sentiment import (
    NorthBoundFlowFactor, MarginChangeFactor
)
from financial_analyzer.quant.factors.base import FactorInput


class TestNorthBoundFlowFactor:
    def test_positive_inflow(self):
        hk_hold = pd.DataFrame({"vol": [10000, 5000, 3000]})
        inp = FactorInput("600519", hk_hold=hk_hold)
        result = NorthBoundFlowFactor().compute(inp)
        total = 10000 + 5000 + 3000
        avg = total / 3
        assert result == pytest.approx(total / avg, rel=1e-4)

    def test_no_hk_hold(self):
        result = NorthBoundFlowFactor().compute(FactorInput("600519"))
        assert result is None


class TestMarginChangeFactor:
    def test_increase(self):
        margin = pd.DataFrame({"rzye": [1000, 800, 600]})
        inp = FactorInput("600519", margin=margin)
        result = MarginChangeFactor().compute(inp)
        assert result == pytest.approx(0.25, rel=1e-4)

    def test_no_margin(self):
        result = MarginChangeFactor().compute(FactorInput("600519"))
        assert result is None
