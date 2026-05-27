"""量化管道端到端集成测试"""
import pytest
import pandas as pd
import numpy as np
from datetime import date

from financial_analyzer.quant.models import StockInfo, FactorConfig
from financial_analyzer.quant.factors.value import PEFactor, PBFactor
from financial_analyzer.quant.factors.quality import ROEFactor
from financial_analyzer.quant.engine.factor_matrix import FactorMatrixBuilder
from financial_analyzer.quant.engine.normalizer import CrossSectionalNormalizer
from financial_analyzer.quant.engine.scorer import WeightedScorer
from financial_analyzer.quant.engine.ranker import Ranker
from financial_analyzer.quant.engine.optimizer import ConstraintOptimizer
from financial_analyzer.quant.engine.signal import SignalGenerator


def make_stock_data(code, pe=15.0, pb=2.0, roe_np=500, roe_eq=5000):
    return {
        "basic": pd.DataFrame({"pe": [pe], "pb": [pb]}),
        "income": pd.DataFrame({"net_profit": [roe_np]}),
        "balance": pd.DataFrame({"total_equity": [roe_eq]}),
    }


class TestQuantPipeline:
    """端到端管道测试 — 使用模拟数据"""

    def test_full_pipeline(self):
        stocks = [
            StockInfo("A", "股A", "白酒"),
            StockInfo("B", "股B", "银行"),
            StockInfo("C", "股C", "电池"),
            StockInfo("D", "股D", "银行"),
            StockInfo("E", "股E", "白酒"),
        ]
        stock_data = {
            "A": make_stock_data("A", pe=10, pb=1.5, roe_np=1000, roe_eq=8000),
            "B": make_stock_data("B", pe=20, pb=3.0, roe_np=300, roe_eq=3000),
            "C": make_stock_data("C", pe=25, pb=4.0, roe_np=200, roe_eq=2000),
            "D": make_stock_data("D", pe=15, pb=2.0, roe_np=400, roe_eq=5000),
            "E": make_stock_data("E", pe=12, pb=1.8, roe_np=800, roe_eq=6000),
        }

        factors = [PEFactor(), PBFactor(), ROEFactor()]
        builder = FactorMatrixBuilder(factors=factors)
        matrix = builder.build(stocks, stock_data)

        assert len(matrix.stocks) >= 1
        assert len(matrix.scores) >= 1

        normalizer = CrossSectionalNormalizer()
        matrix = normalizer.normalize(matrix)

        configs = [
            FactorConfig(name="pe", label="PE", category="value", weight=1.0),
            FactorConfig(name="pb", label="PB", category="value", weight=1.0),
            FactorConfig(name="roe", label="ROE", category="quality", weight=1.0),
        ]
        scorer = WeightedScorer(configs)
        scores = scorer.score(matrix)
        assert len(scores) >= 1

        ranker = Ranker(top_n=30)
        ranked = ranker.rank(scores, stocks)
        assert len(ranked) >= 1

        optimizer = ConstraintOptimizer(min_industries=1)
        optimized = optimizer.optimize(ranked, scores)
        assert len(optimized) >= 1

        gen = SignalGenerator()
        trade_list = gen.generate(optimized, scores, set(), "测试池")
        assert len(trade_list.buys) >= 1
        assert trade_list.universe == "测试池"

    def test_pipeline_with_missing_data(self):
        stocks = [
            StockInfo("A", "股A", "白酒"),
            StockInfo("B", "股B", "银行"),
        ]
        stock_data = {"A": make_stock_data("A")}

        factors = [PEFactor(), ROEFactor()]
        builder = FactorMatrixBuilder(factors=factors)
        matrix = builder.build(stocks, stock_data)

        assert "A" in matrix.scores
        assert "B" not in matrix.scores

        normalizer = CrossSectionalNormalizer()
        matrix = normalizer.normalize(matrix)
        # should not crash

    def test_small_universe(self):
        stocks = [
            StockInfo("A", "股A", "白酒"),
            StockInfo("B", "股B", "银行"),
        ]
        stock_data = {
            "A": make_stock_data("A"),
            "B": make_stock_data("B"),
        }

        factors = [PEFactor()]
        builder = FactorMatrixBuilder(factors=factors)
        matrix = builder.build(stocks, stock_data)

        normalizer = CrossSectionalNormalizer()
        matrix = normalizer.normalize(matrix)

        configs = [FactorConfig(name="pe", label="PE", category="value", weight=1.0)]
        scorer = WeightedScorer(configs)
        scores = scorer.score(matrix)

        ranker = Ranker(top_n=30)
        optimizer = ConstraintOptimizer(min_industries=1, min_stocks=1, max_stocks=2)
        gen = SignalGenerator()

        ranked = ranker.rank(scores, stocks)
        optimized = optimizer.optimize(ranked, scores)
        trade_list = gen.generate(optimized, scores, set(), "小池")

        assert len(trade_list.buys) <= 2
