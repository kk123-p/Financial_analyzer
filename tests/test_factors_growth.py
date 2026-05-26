"""成长因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.growth import RevenueGrowthFactor, NetProfitGrowthFactor
from financial_analyzer.quant.factors.base import FactorInput


class TestRevenueGrowthFactor:
    def test_positive_growth(self):
        income = pd.DataFrame({
            "revenue": [1200, 1000, 800],
        })
        inp = FactorInput("600519", income=income)
        result = RevenueGrowthFactor().compute(inp)
        assert result == pytest.approx(0.20, rel=1e-4)

    def test_negative_growth(self):
        income = pd.DataFrame({
            "revenue": [800, 1000, 1200],
        })
        inp = FactorInput("600519", income=income)
        result = RevenueGrowthFactor().compute(inp)
        assert result == pytest.approx(-0.20, rel=1e-4)

    def test_insufficient_data(self):
        income = pd.DataFrame({"revenue": [1200]})
        inp = FactorInput("600519", income=income)
        result = RevenueGrowthFactor().compute(inp)
        assert result is None

    def test_zero_previous(self):
        income = pd.DataFrame({"revenue": [1200, 0]})
        inp = FactorInput("600519", income=income)
        result = RevenueGrowthFactor().compute(inp)
        assert result is None


class TestNetProfitGrowthFactor:
    def test_positive_growth(self):
        income = pd.DataFrame({"net_profit": [150, 100]})
        inp = FactorInput("600519", income=income)
        result = NetProfitGrowthFactor().compute(inp)
        assert result == pytest.approx(0.50, rel=1e-4)

    def test_insufficient_data(self):
        income = pd.DataFrame({"net_profit": [150]})
        inp = FactorInput("600519", income=income)
        result = NetProfitGrowthFactor().compute(inp)
        assert result is None
