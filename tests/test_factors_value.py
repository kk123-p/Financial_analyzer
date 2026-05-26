"""价值因子测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.value import (
    PEFactor, PBFactor, PSFactor, DividendYieldFactor, FCFYieldFactor
)
from financial_analyzer.quant.factors.base import FactorInput


def make_daily(close=10.0, total_mv=1e6):
    return pd.DataFrame({"close": [close], "total_mv": [total_mv]})

def make_basic(pe=15.0, pb=2.0, total_share=1000):
    return pd.DataFrame({"pe": [pe], "pb": [pb], "total_share": [total_share]})

def make_balance(equity=5000, total_assets=10000):
    return pd.DataFrame({
        "total_equity": [equity],
        "total_assets": [total_assets],
        "total_liab": [total_assets - equity],
    })

def make_cashflow(n_cashflow_act=500):
    return pd.DataFrame({"n_cashflow_act": [n_cashflow_act]})

def make_income(revenue=3000, net_profit=300):
    return pd.DataFrame({"revenue": [revenue], "net_profit": [net_profit]})

def basic_input(code="600519", **kwargs):
    return FactorInput(
        stock_code=code,
        daily=kwargs.get("daily", make_daily()),
        basic=kwargs.get("basic", make_basic()),
        balance=kwargs.get("balance", make_balance()),
        cashflow=kwargs.get("cashflow", make_cashflow()),
        income=kwargs.get("income", make_income()),
    )


class TestPEFactor:
    def test_normal(self):
        inp = basic_input(basic=make_basic(pe=12.5))
        result = PEFactor().compute(inp)
        # PE因子: -1/PE (低PE更好), 方向negative
        assert result == pytest.approx(-1 / 12.5, rel=1e-4)

    def test_no_basic(self):
        inp = basic_input(basic=None)
        result = PEFactor().compute(inp)
        assert result is None

    def test_negative_pe(self):
        inp = basic_input(basic=make_basic(pe=-5.0))
        result = PEFactor().compute(inp)
        assert result is None  # 负PE无意义

    def test_pe_zero(self):
        inp = basic_input(basic=make_basic(pe=0))
        result = PEFactor().compute(inp)
        assert result is None


class TestPBFactor:
    def test_normal(self):
        inp = basic_input(basic=make_basic(pb=1.5))
        result = PBFactor().compute(inp)
        assert result == pytest.approx(-1 / 1.5, rel=1e-4)

    def test_no_data(self):
        result = PBFactor().compute(FactorInput("600519"))
        assert result is None


class TestDividendYieldFactor:
    def test_no_dividend_data(self):
        # 无分红数据返回 None
        result = DividendYieldFactor().compute(basic_input())
        assert result is None
