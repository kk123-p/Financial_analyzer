"""因子归因模块测试"""
import math
from datetime import date

import pytest
import numpy as np

from financial_analyzer.quant.models import FactorMatrix
from financial_analyzer.quant.backtest.attribution import FactorAttribution


@pytest.fixture
def fa():
    return FactorAttribution()


@pytest.fixture
def simple_factor_history():
    """构造简单的因子矩阵历史: 3 期, 2 个因子, 5 只股票"""
    history = []
    np.random.seed(42)
    for t in range(4):
        stocks = [f"S{i:03d}" for i in range(10)]
        scores = {}
        for s in stocks:
            scores[s] = {
                "momentum": float(np.random.randn()),
                "value": float(np.random.randn()),
            }
        industries = {
            f"S{i:03d}": "银行" if i < 4 else ("医药" if i < 7 else "科技")
            for i in range(10)
        }
        history.append(FactorMatrix(
            date=date(2024, 1 + t, 28),
            stocks=stocks,
            scores=scores,
            industries=industries,
        ))
    return history


@pytest.fixture
def simple_monthly_returns():
    """构造 3 期的个股收益率"""
    np.random.seed(123)
    returns = []
    for _ in range(3):
        rets = {f"S{i:03d}": float(np.random.randn() * 0.05) for i in range(10)}
        returns.append(rets)
    return returns


class TestMultiFactorAttribution:
    def test_returns_empty_with_no_data(self, fa):
        assert fa.multi_factor_attribution([], []) == {}

    def test_returns_empty_with_single_period(self, fa, simple_factor_history):
        single = [simple_factor_history[0]]
        returns = [{"S000": 0.01}]
        assert fa.multi_factor_attribution(single, returns) == {}

    def test_basic_shape(self, fa, simple_factor_history, simple_monthly_returns):
        result = fa.multi_factor_attribution(simple_factor_history, simple_monthly_returns)
        assert isinstance(result, dict)
        assert "momentum" in result
        assert "value" in result
        for fname, stats in result.items():
            assert "mean_beta" in stats
            assert "t_stat" in stats
            assert isinstance(stats["mean_beta"], float)
            assert isinstance(stats["t_stat"], float)

    def test_known_relationship(self, fa):
        """当因子与收益有确定性线性关系时, 回归应捕获系数"""
        history = []
        returns = []
        for t in range(5):
            stocks = ["A", "B", "C", "D", "E"]
            scores = {}
            stock_rets = {}
            for i, s in enumerate(stocks):
                f1 = float(i)  # 0, 1, 2, 3, 4
                f2 = float(4 - i)  # 4, 3, 2, 1, 0
                scores[s] = {"f1": f1, "f2": f2}
                stock_rets[s] = 0.5 * f1 + 0.3 * f2 + float(np.random.randn() * 0.001)
            history.append(FactorMatrix(
                date=date(2024, t + 1, 28),
                stocks=stocks,
                scores=scores,
            ))
            returns.append(stock_rets)

        result = fa.multi_factor_attribution(history, returns)
        assert abs(result["f1"]["mean_beta"] - 0.5) < 0.1
        assert abs(result["f2"]["mean_beta"] - 0.3) < 0.1
        assert abs(result["f1"]["t_stat"]) > 2.0  # 应该显著

    def test_rounding(self, fa, simple_factor_history, simple_monthly_returns):
        result = fa.multi_factor_attribution(simple_factor_history, simple_monthly_returns)
        for stats in result.values():
            assert len(str(stats["mean_beta"]).split(".")[-1]) <= 6
            assert len(str(stats["t_stat"]).split(".")[-1]) <= 4


class TestIndustryAttribution:
    def test_returns_empty_with_no_data(self, fa):
        assert fa.industry_attribution({}, []) == {}

    def test_returns_empty_with_zero_total(self, fa):
        holdings = {"银行": ["A", "B"]}
        returns = [{"A": 0.0, "B": 0.0}]
        result = fa.industry_attribution(holdings, returns)
        assert result == {"银行": 0.0}

    def test_basic_shape(self, fa, simple_monthly_returns):
        holdings = {
            "银行": ["S000", "S001", "S002", "S003"],
            "医药": ["S004", "S005", "S006"],
            "科技": ["S007", "S008", "S009"],
        }
        result = fa.industry_attribution(holdings, simple_monthly_returns)
        assert isinstance(result, dict)
        assert set(result.keys()) == {"银行", "医药", "科技"}
        for pct in result.values():
            assert isinstance(pct, float)

    def test_percentages_sum_to_100(self, fa, simple_monthly_returns):
        holdings = {
            "银行": ["S000", "S001", "S002", "S003"],
            "医药": ["S004", "S005", "S006"],
            "科技": ["S007", "S008", "S009"],
        }
        result = fa.industry_attribution(holdings, simple_monthly_returns)
        total = sum(result.values())
        assert abs(total - 100.0) < 0.1

    def test_known_contribution(self, fa):
        """当只有两个行业且收益确定时, 验证贡献比例"""
        holdings = {"银行": ["A"], "医药": ["B"]}
        returns = [
            {"A": 0.10, "B": 0.02},
            {"A": 0.06, "B": 0.04},
        ]
        result = fa.industry_attribution(holdings, returns)
        # 银行: (0.10+0.06) / (0.12+0.10) * 100 = 16/22 * 100
        expected_bank = round(16 / 22 * 100, 2)
        assert abs(result["银行"] - expected_bank) < 0.01

    def test_stocks_not_in_returns(self, fa):
        """股票不在收益率字典中时应视为 0"""
        holdings = {"银行": ["A", "B"], "医药": ["C"]}
        returns = [{"A": 0.10, "C": 0.05}]  # B missing
        result = fa.industry_attribution(holdings, returns)
        # 银行: 0.10, 医药: 0.05, total: 0.15
        assert abs(result["银行"] - round(0.10 / 0.15 * 100, 2)) < 0.01
        assert abs(result["医药"] - round(0.05 / 0.15 * 100, 2)) < 0.01


class TestCorrelation:
    def test_perfect_positive(self, fa):
        assert abs(fa._correlation([1, 2, 3], [2, 4, 6]) - 1.0) < 1e-10

    def test_perfect_negative(self, fa):
        assert abs(fa._correlation([1, 2, 3], [6, 4, 2]) - (-1.0)) < 1e-10

    def test_zero_variance(self, fa):
        assert fa._correlation([1, 1, 1], [1, 2, 3]) == 0.0

    def test_short_list(self, fa):
        assert fa._correlation([1], [2]) == 0.0
