"""风险因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.risk import DebtRatioFactor, CurrentRatioFactor
from financial_analyzer.quant.factors.base import FactorInput


class TestDebtRatioFactor:
    def test_normal(self):
        balance = pd.DataFrame({
            "total_liab": [4000],
            "total_assets": [10000],
        })
        inp = FactorInput("600519", balance=balance)
        result = DebtRatioFactor().compute(inp)
        assert result == pytest.approx(-0.40, rel=1e-4)

    def test_no_balance(self):
        result = DebtRatioFactor().compute(FactorInput("600519"))
        assert result is None

    def test_zero_assets(self):
        balance = pd.DataFrame({"total_liab": [4000], "total_assets": [0]})
        inp = FactorInput("600519", balance=balance)
        result = DebtRatioFactor().compute(inp)
        assert result is None


class TestCurrentRatioFactor:
    def test_too_high(self):
        balance = pd.DataFrame({
            "total_assets": [10000],
            "total_liab": [1000],
        })
        inp = FactorInput("600519", balance=balance)
        result = CurrentRatioFactor().compute(inp)
        assert result is not None
