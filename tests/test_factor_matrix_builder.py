"""因子矩阵构建器测试"""
import pytest
import pandas as pd
import numpy as np
from datetime import date
from financial_analyzer.quant.engine.factor_matrix import FactorMatrixBuilder
from financial_analyzer.quant.factors.value import PEFactor, PBFactor
from financial_analyzer.quant.factors.quality import ROEFactor
from financial_analyzer.quant.models import StockInfo

class TestFactorMatrixBuilder:
    def test_build_empty_stocks(self):
        builder = FactorMatrixBuilder(factors=[PEFactor()])
        matrix = builder.build([], {})
        assert len(matrix.stocks) == 0

    def test_build_with_data(self):
        builder = FactorMatrixBuilder(factors=[PEFactor(), PBFactor()])
        stocks = [StockInfo("600519", "茅台")]
        data = {
            "600519": {
                "basic": pd.DataFrame({"pe": [15.0], "pb": [3.0]}),
            }
        }
        matrix = builder.build(stocks, data)
        assert len(matrix.stocks) == 1
        assert "600519" in matrix.scores
        assert "pe" in matrix.scores["600519"]
        assert "pb" in matrix.scores["600519"]

    def test_factor_registry(self):
        builder = FactorMatrixBuilder(factors=[])
        builder.register(PEFactor(weight=1.0))
        builder.register(PBFactor(weight=0.5))
        assert len(builder.factors) == 2

    def test_all_factors_category(self):
        from financial_analyzer.quant.factors.value import PEFactor
        from financial_analyzer.quant.factors.quality import ROEFactor
        from financial_analyzer.quant.factors.growth import RevenueGrowthFactor
        from financial_analyzer.quant.factors.momentum import PriceMomentum3M
        from financial_analyzer.quant.factors.sentiment import NorthBoundFlowFactor
        from financial_analyzer.quant.factors.low_vol import Volatility60D
        from financial_analyzer.quant.factors.risk import DebtRatioFactor

        factors = [
            PEFactor(), ROEFactor(), RevenueGrowthFactor(),
            PriceMomentum3M(), NorthBoundFlowFactor(),
            Volatility60D(), DebtRatioFactor(),
        ]
        builder = FactorMatrixBuilder(factors=factors)
        categories = set(f.category for f in builder.factors)
        assert len(categories) == 7
