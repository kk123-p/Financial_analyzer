"""参数网格搜索模块"""
import logging
import itertools
from ..models import FactorConfig

logger = logging.getLogger(__name__)


class GridSearchEngine:
    """参数网格搜索引擎"""

    def __init__(self, backtest_engine_factory):
        """
        Args:
            backtest_engine_factory: 可调用对象，接受 factor_configs 和 kwargs 返回 BacktestEngine
        """
        self.engine_factory = backtest_engine_factory

    def search(
        self,
        param_grid: dict[str, list],
        base_configs: list[FactorConfig],
        pool: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000,
        top_n: int = 30,
    ) -> list[dict]:
        """执行网格搜索

        Args:
            param_grid: {factor_name: [weight_values]} 如 {"pe": [0.1, 0.2, 0.3], "roe": [0.5, 1.0]}
            base_configs: 基础因子配置
            pool: 选股池
            start_date, end_date: 回测区间
            initial_capital: 初始资金
            top_n: TOP-N

        Returns:
            [{params, sharpe, total_return, max_drawdown, annualized_return}]
        """
        factor_names = list(param_grid.keys())
        weight_values = list(param_grid.values())
        combinations = list(itertools.product(*weight_values))

        results = []
        total = len(combinations)

        for idx, combo in enumerate(combinations):
            params = dict(zip(factor_names, combo))

            custom_configs = []
            for c in base_configs:
                new_weight = params.get(c.name, c.weight)
                custom_configs.append(FactorConfig(
                    name=c.name, label=c.label, category=c.category,
                    direction=c.direction, weight=new_weight, enabled=c.enabled,
                ))

            try:
                engine = self.engine_factory(
                    factor_configs=custom_configs,
                    pool=pool,
                    start_date=start_date,
                    end_date=end_date,
                )
                result = engine.run(
                    start_date=start_date,
                    end_date=end_date,
                    pool=pool,
                    initial_capital=initial_capital,
                    top_n=top_n,
                )

                metrics = result.metrics
                results.append({
                    'params': params,
                    'sharpe': round(metrics.sharpe_ratio, 4) if metrics else 0,
                    'total_return': round(metrics.total_return, 6) if metrics else 0,
                    'annualized_return': round(metrics.annualized_return, 6) if metrics else 0,
                    'max_drawdown': round(metrics.max_drawdown, 6) if metrics else 0,
                })

                if (idx + 1) % 5 == 0:
                    logger.info(f"网格搜索进度: {idx+1}/{total}")

            except Exception as e:
                logger.warning(f"参数组合 {params} 失败: {e}")
                results.append({
                    'params': params,
                    'sharpe': 0,
                    'total_return': 0,
                    'annualized_return': 0,
                    'max_drawdown': 0,
                    'error': str(e),
                })

        results.sort(key=lambda x: x.get('sharpe', 0), reverse=True)
        return results
