"""质量因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.quality import (
    ROEFactor, GrossMarginFactor, NetMarginFactor
)
from financial_analyzer.quant.factors.base import FactorInput


class TestROEFactor:
    def test_normal(self):
        income = pd.DataFrame({"net_profit": [500]})
        balance = pd.DataFrame({"total_equity": [5000]})
        inp = FactorInput("600519", income=income, balance=balance)
        result = ROEFactor().compute(inp)
        assert result == pytest.approx(0.10, rel=1e-4)

    def test_no_equity(self):
        income = pd.DataFrame({"net_profit": [500]})
        inp = FactorInput("600519", income=income)
        result = ROEFactor().compute(inp)
        assert result is None

    def test_zero_equity(self):
        income = pd.DataFrame({"net_profit": [500]})
        balance = pd.DataFrame({"total_equity": [0]})
        inp = FactorInput("600519", income=income, balance=balance)
        result = ROEFactor().compute(inp)
        assert result is None


class TestGrossMarginFactor:
    def test_normal(self):
        income = pd.DataFrame({"revenue": [3000], "oper_cost": [1800]})
        inp = FactorInput("600519", income=income)
        result = GrossMarginFactor().compute(inp)
        assert result == pytest.approx(0.40, rel=1e-4)

    def test_no_oper_cost(self):
        income = pd.DataFrame({"revenue": [3000]})
        inp = FactorInput("600519", income=income)
        result = GrossMarginFactor().compute(inp)
        assert result is None


class TestNetMarginFactor:
    def test_normal(self):
        income = pd.DataFrame({"revenue": [3000], "net_profit": [450]})
        inp = FactorInput("600519", income=income)
        result = NetMarginFactor().compute(inp)
        assert result == pytest.approx(0.15, rel=1e-4)

    def test_no_revenue(self):
        income = pd.DataFrame({"net_profit": [450]})
        inp = FactorInput("600519", income=income)
        result = NetMarginFactor().compute(inp)
        assert result is None

    def test_negative_net_profit(self):
        income = pd.DataFrame({"revenue": [3000], "net_profit": [-100]})
        inp = FactorInput("600519", income=income)
        result = NetMarginFactor().compute(inp)
        assert result is None
