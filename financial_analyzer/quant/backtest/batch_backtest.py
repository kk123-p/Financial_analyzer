"""批量回测对比模块"""
import logging
import threading
import uuid
from typing import Optional
from .engine import BacktestEngine
from ..engine.strategy_template import StrategyTemplate

logger = logging.getLogger(__name__)


class BatchBacktestRunner:
    """批量回测运行器"""

    def __init__(self, engine_factory):
        """
        Args:
            engine_factory: 可调用对象，接受 StrategyTemplate 返回配置好的 BacktestEngine
        """
        self.engine_factory = engine_factory
        self._tasks: dict[str, dict] = {}

    def run_batch(
        self,
        strategies: list[StrategyTemplate],
        pool: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000,
    ) -> str:
        """并行运行多个策略回测"""
        batch_id = "batch_" + uuid.uuid4().hex[:8]
        self._tasks[batch_id] = {
            'status': 'running',
            'strategies': {s.name: {'status': 'pending'} for s in strategies},
            'results': {},
        }

        def _run_strategy(template: StrategyTemplate):
            try:
                engine = self.engine_factory(template)
                result = engine.run(
                    start_date=start_date,
                    end_date=end_date,
                    pool=pool,
                    initial_capital=initial_capital,
                    top_n=template.top_n,
                )
                m = result.metrics
                self._tasks[batch_id]['results'][template.name] = {
                    'status': 'done',
                    'sharpe': round(m.sharpe_ratio, 4) if m else 0,
                    'total_return': round(m.total_return, 6) if m else 0,
                    'annualized_return': round(m.annualized_return, 6) if m else 0,
                    'max_drawdown': round(m.max_drawdown, 6) if m else 0,
                    'win_rate': round(m.win_rate, 4) if m else 0,
                    'equity_curve': [s.total_value for s in result.snapshots],
                }
                self._tasks[batch_id]['strategies'][template.name] = {'status': 'done'}
            except Exception as e:
                logger.error(f"策略 {template.name} 回测失败: {e}")
                self._tasks[batch_id]['results'][template.name] = {
                    'status': 'error', 'error': str(e),
                }
                self._tasks[batch_id]['strategies'][template.name] = {'status': 'error'}

        threads = []
        for t in strategies:
            th = threading.Thread(target=_run_strategy, args=(t,), daemon=True)
            th.start()
            threads.append(th)

        def _wait_all():
            for th in threads:
                th.join()
            self._tasks[batch_id]['status'] = 'done'

        threading.Thread(target=_wait_all, daemon=True).start()
        return batch_id

    def get_batch_status(self, batch_id: str) -> Optional[dict]:
        return self._tasks.get(batch_id)

    def get_batch_result(self, batch_id: str) -> Optional[dict]:
        task = self._tasks.get(batch_id)
        if not task or task['status'] != 'done':
            return task

        ranked = sorted(
            task['results'].items(),
            key=lambda x: x[1].get('sharpe', 0),
            reverse=True,
        )
        return {
            'status': 'done',
            'ranking': [
                {'name': name, **data} for name, data in ranked
            ],
        }
