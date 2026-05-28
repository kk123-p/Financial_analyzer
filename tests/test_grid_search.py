"""网格搜索引擎测试"""
import pytest
from unittest.mock import MagicMock, patch

from financial_analyzer.quant.engine.grid_search import GridSearchEngine
from financial_analyzer.quant.models import FactorConfig
from financial_analyzer.quant.backtest.metrics import PerformanceMetrics
from financial_analyzer.quant.backtest.models import BacktestResult


@pytest.fixture
def base_configs():
    return [
        FactorConfig(name="pe", label="PE", category="value", weight=1.0),
        FactorConfig(name="roe", label="ROE", category="quality", weight=1.5),
        FactorConfig(name="momentum_3m", label="3月动量", category="momentum", weight=0.5),
    ]


@pytest.fixture
def mock_metrics():
    return PerformanceMetrics(
        total_return=0.15,
        annualized_return=0.12,
        sharpe_ratio=1.5,
        max_drawdown=-0.08,
        win_rate=0.6,
    )


@pytest.fixture
def mock_backtest_result(mock_metrics):
    return BacktestResult(
        start_date="20230101",
        end_date="20240101",
        initial_capital=100000,
        final_value=115000,
        metrics=mock_metrics,
    )


def _make_engine_factory(mock_result):
    def factory(factor_configs, pool, start_date, end_date):
        engine = MagicMock()
        engine.run.return_value = mock_result
        engine.factor_configs = factor_configs
        return engine
    return factory


class TestGridSearchEngine:

    def test_single_factor_grid(self, base_configs, mock_backtest_result):
        factory = _make_engine_factory(mock_backtest_result)
        engine = GridSearchEngine(factory)

        results = engine.search(
            param_grid={"pe": [0.5, 1.0, 1.5]},
            base_configs=base_configs,
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        assert len(results) == 3
        for r in results:
            assert 'params' in r
            assert 'sharpe' in r
            assert 'total_return' in r
            assert 'max_drawdown' in r
            assert r['sharpe'] == 1.5

    def test_multi_factor_grid(self, base_configs, mock_backtest_result):
        factory = _make_engine_factory(mock_backtest_result)
        engine = GridSearchEngine(factory)

        results = engine.search(
            param_grid={"pe": [0.5, 1.0], "roe": [1.0, 2.0]},
            base_configs=base_configs,
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        assert len(results) == 4

    def test_sorted_by_sharpe(self, base_configs):
        call_count = [0]

        def varying_factory(factor_configs, pool, start_date, end_date):
            call_count[0] += 1
            engine = MagicMock()
            metrics = PerformanceMetrics(
                total_return=0.1 * call_count[0],
                annualized_return=0.08 * call_count[0],
                sharpe_ratio=call_count[0] * 0.5,
                max_drawdown=-0.1,
                win_rate=0.5,
            )
            engine.run.return_value = BacktestResult(
                start_date="20230101", end_date="20240101",
                initial_capital=100000, final_value=110000, metrics=metrics,
            )
            return engine

        engine = GridSearchEngine(varying_factory)
        results = engine.search(
            param_grid={"pe": [0.1, 0.2, 0.3]},
            base_configs=base_configs,
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        sharpes = [r['sharpe'] for r in results]
        assert sharpes == sorted(sharpes, reverse=True)

    def test_error_handling(self, base_configs):
        def failing_factory(factor_configs, pool, start_date, end_date):
            engine = MagicMock()
            engine.run.side_effect = ValueError("数据不足")
            return engine

        engine = GridSearchEngine(failing_factory)
        results = engine.search(
            param_grid={"pe": [0.5]},
            base_configs=base_configs,
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        assert len(results) == 1
        assert results[0]['sharpe'] == 0
        assert 'error' in results[0]

    def test_weight_override(self, base_configs, mock_backtest_result):
        captured_configs = []

        def capturing_factory(factor_configs, pool, start_date, end_date):
            captured_configs.append(factor_configs)
            engine = MagicMock()
            engine.run.return_value = mock_backtest_result
            return engine

        engine = GridSearchEngine(capturing_factory)
        engine.search(
            param_grid={"pe": [0.7]},
            base_configs=base_configs,
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        configs = captured_configs[0]
        pe_cfg = next(c for c in configs if c.name == "pe")
        roe_cfg = next(c for c in configs if c.name == "roe")

        assert pe_cfg.weight == 0.7
        assert roe_cfg.weight == 1.5

    def test_empty_grid(self, base_configs, mock_backtest_result):
        factory = _make_engine_factory(mock_backtest_result)
        engine = GridSearchEngine(factory)

        results = engine.search(
            param_grid={},
            base_configs=base_configs,
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        assert len(results) == 1
