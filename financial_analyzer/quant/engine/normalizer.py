"""截面标准化器 — Z-score / 分位数 / 行业中性化"""
import numpy as np
from ..models import FactorMatrix


class CrossSectionalNormalizer:
    """截面因子标准化"""

    def __init__(self, method: str = "zscore"):
        self.method = method

    def normalize(self, matrix: FactorMatrix) -> FactorMatrix:
        if len(matrix.stocks) < 2:
            return matrix

        factor_names = set()
        for scores in matrix.scores.values():
            factor_names.update(scores.keys())

        for fname in factor_names:
            values = []
            stocks_with_factor = []
            for s in matrix.stocks:
                val = matrix.get_score(s, fname)
                if val is not None and val == val:  # not NaN
                    values.append(val)
                    stocks_with_factor.append(s)

            if len(values) < 2:
                continue

            if self.method == "zscore":
                normalized = self._zscore(values)
            elif self.method == "rank":
                normalized = self._rank_normalize(values)
            else:
                normalized = values

            for s, nv in zip(stocks_with_factor, normalized):
                matrix.scores[s][fname] = nv

        return matrix

    def _zscore(self, values: list[float]) -> list[float]:
        arr = np.array(values)
        mean = arr.mean()
        std = arr.std()
        if std == 0:
            return [0.0] * len(values)
        return ((arr - mean) / std).tolist()

    def _rank_normalize(self, values: list[float]) -> list[float]:
        arr = np.array(values)
        n = len(arr)
        if n <= 1:
            return [0.0] * n
        ranks = np.argsort(np.argsort(arr)).astype(float)
        return (2 * ranks / (n - 1) - 1).tolist()
