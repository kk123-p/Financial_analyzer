"""因子基类测试"""
import pytest
import pandas as pd
import numpy as np
from financial_analyzer.quant.factors.base import BaseFactor, FactorInput


class TestFactorInput:
    def test_create(self):
        daily = pd.DataFrame({"close": [10, 11, 12]})
        fi = FactorInput(stock_code="600519", daily=daily)
        assert fi.stock_code == "600519"
        assert len(fi.daily) == 3


class TestBaseFactor:
    def test_name_and_category(self):
        class TestFactor(BaseFactor):
            name = "test_factor"
            category = "value"
            label = "测试因子"
            direction = "positive"

            def compute(self, input_data):
                return 1.0

        f = TestFactor(weight=1.0)
        assert f.name == "test_factor"
        assert f.category == "value"
        assert f.weight == 1.0
        assert f.direction == "positive"

    def test_compute_abstract(self):
        class IncompleteFactor(BaseFactor):
            pass

        with pytest.raises(TypeError):
            IncompleteFactor()

    def test_compute_returns_factor_value(self):
        class SimpleFactor(BaseFactor):
            name = "simple"
            category = "test"
            label = "测试"

            def compute(self, input_data):
                return 0.75

        f = SimpleFactor()
        result = f.compute(FactorInput("600519", pd.DataFrame()))
        assert result == 0.75

    def test_compute_handles_nan(self):
        class NaNReturningFactor(BaseFactor):
            name = "nan_factor"
            category = "test"
            label = "NaN测试"

            def compute(self, input_data):
                return BaseFactor._validate_result(float('nan'))

        f = NaNReturningFactor()
        result = f.compute(FactorInput("600519", pd.DataFrame()))
        assert result is None
