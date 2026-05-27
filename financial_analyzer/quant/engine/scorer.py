"""加权综合打分器"""
from ..models import FactorMatrix, FactorConfig


class WeightedScorer:
    """按因子配置的权重计算综合得分"""

    def __init__(self, factor_configs: list[FactorConfig]):
        self.configs = {c.name: c for c in factor_configs}

    def score(self, matrix: FactorMatrix) -> dict[str, float]:
        """返回 {stock_code: composite_score}，按总权重归一化"""
        active_configs = {n: c for n, c in self.configs.items() if c.enabled}
        total_weight = sum(c.weight for c in active_configs.values())
        if total_weight == 0:
            return {stock: 0.0 for stock in matrix.stocks}

        result = {}
        for stock in matrix.stocks:
            total = 0.0
            for name, config in active_configs.items():
                score = matrix.get_score(stock, name)
                if score is not None:
                    total += score * config.weight
            result[stock] = total / total_weight

        return result
