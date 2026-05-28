"""批量回测运行器测试"""
import time
import pytest
from unittest.mock import MagicMock

from financial_analyzer.quant.backtest.batch_backtest import BatchBacktestRunner
from financial_analyzer.quant.engine.strategy_template import StrategyTemplate
from financial_analyzer.quant.backtest.metrics import PerformanceMetrics
from financial_analyzer.quant.backtest.models import BacktestResult, PortfolioSnapshot


@pytest.fixture
def sample_templates():
    return [
        StrategyTemplate(
            name="价值策略",
            description="低PE高ROE",
            factors=[{"name": "pe", "weight": 1.0, "direction": -1},
                     {"name": "roe", "weight": 1.5, "direction": 1}],
            position_sizer="equal",
            risk={},
            top_n=20,
        ),
        StrategyTemplate(
            name="动量策略",
            description="高动量",
            factors=[{"name": "momentum_3m", "weight": 1.0, "direction": 1}],
            position_sizer="equal",
            risk={},
            top_n=30,
        ),
    ]


def _make_result(sharpe, total_return, max_drawdown=-0.1, win_rate=0.6):
    metrics = PerformanceMetrics(
        total_return=total_return,
        annualized_return=total_return * 0.8,
        sharpe_ratio=sharpe,
        max_drawdown=max_drawdown,
        win_rate=win_rate,
    )
    return BacktestResult(
        start_date="20230101",
        end_date="20240101",
        initial_capital=100000,
        final_value=100000 * (1 + total_return),
        metrics=metrics,
        snapshots=[
            PortfolioSnapshot(date="20230131", total_value=100000),
            PortfolioSnapshot(date="20230228", total_value=105000),
        ],
    )


class TestBatchBacktestRunner:

    def test_run_batch_returns_batch_id(self, sample_templates):
        def factory(template):
            engine = MagicMock()
            engine.run.return_value = _make_result(1.5, 0.15)
            return engine

        runner = BatchBacktestRunner(factory)
        batch_id = runner.run_batch(
            strategies=sample_templates,
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        assert batch_id.startswith("batch_")
        assert len(batch_id) > 6

    def test_batch_status_exists(self, sample_templates):
        def factory(template):
            engine = MagicMock()
            engine.run.return_value = _make_result(1.5, 0.15)
            return engine

        runner = BatchBacktestRunner(factory)
        batch_id = runner.run_batch(
            strategies=sample_templates,
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        status = runner.get_batch_status(batch_id)
        assert status is not None
        assert 'status' in status
        assert 'strategies' in status

    def test_batch_completes(self, sample_templates):
        def factory(template):
            engine = MagicMock()
            engine.run.return_value = _make_result(1.5, 0.15)
            return engine

        runner = BatchBacktestRunner(factory)
        batch_id = runner.run_batch(
            strategies=sample_templates,
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        for _ in range(50):
            time.sleep(0.1)
            status = runner.get_batch_status(batch_id)
            if status and status['status'] == 'done':
                break

        result = runner.get_batch_result(batch_id)
        assert result is not None
        assert result['status'] == 'done'
        assert 'ranking' in result
        assert len(result['ranking']) == 2

    def test_batch_ranking_sorted_by_sharpe(self, sample_templates):
        def factory(template):
            engine = MagicMock()
            if template.name == "价值策略":
                engine.run.return_value = _make_result(2.0, 0.20)
            else:
                engine.run.return_value = _make_result(1.0, 0.10)
            return engine

        runner = BatchBacktestRunner(factory)
        batch_id = runner.run_batch(
            strategies=sample_templates,
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        for _ in range(50):
            time.sleep(0.1)
            status = runner.get_batch_status(batch_id)
            if status and status['status'] == 'done':
                break

        result = runner.get_batch_result(batch_id)
        assert result['ranking'][0]['name'] == "价值策略"
        assert result['ranking'][0]['sharpe'] == 2.0
        assert result['ranking'][1]['name'] == "动量策略"
        assert result['ranking'][1]['sharpe'] == 1.0

    def test_batch_error_handling(self, sample_templates):
        def factory(template):
            engine = MagicMock()
            if template.name == "价值策略":
                engine.run.return_value = _make_result(1.5, 0.15)
            else:
                engine.run.side_effect = RuntimeError("数据异常")
            return engine

        runner = BatchBacktestRunner(factory)
        batch_id = runner.run_batch(
            strategies=sample_templates,
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        for _ in range(50):
            time.sleep(0.1)
            status = runner.get_batch_status(batch_id)
            if status and status['status'] == 'done':
                break

        result = runner.get_batch_result(batch_id)
        assert result['status'] == 'done'

        names = [r['name'] for r in result['ranking']]
        assert "价值策略" in names

    def test_batch_result_includes_metrics(self, sample_templates):
        def factory(template):
            engine = MagicMock()
            engine.run.return_value = _make_result(1.8, 0.18, -0.05, 0.65)
            return engine

        runner = BatchBacktestRunner(factory)
        batch_id = runner.run_batch(
            strategies=[sample_templates[0]],
            pool="沪深300",
            start_date="20230101",
            end_date="20240101",
        )

        for _ in range(50):
            time.sleep(0.1)
            status = runner.get_batch_status(batch_id)
            if status and status['status'] == 'done':
                break

        result = runner.get_batch_result(batch_id)
        entry = result['ranking'][0]
        assert entry['sharpe'] == 1.8
        assert entry['total_return'] == 0.18
        assert entry['win_rate'] == 0.65
        assert 'equity_curve' in entry

    def test_nonexistent_batch(self):
        runner = BatchBacktestRunner(lambda t: MagicMock())
        assert runner.get_batch_status("batch_nonexistent") is None
        assert runner.get_batch_result("batch_nonexistent") is None
