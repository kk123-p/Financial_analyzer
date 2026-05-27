"""因子绩效归因"""
import math
import logging
from typing import Optional

from ..models import FactorMatrix

logger = logging.getLogger(__name__)


class FactorAttribution:
    """因子绩效归因 — 分析哪些因子对收益贡献最大"""

    def compute_attribution(self,
                            factor_matrix_history: list[FactorMatrix],
                            portfolio_returns: list[float]) -> dict[str, float]:
        """计算每个因子与后续收益的相关性作为归因得分

        对每个因子：取每期截面上持仓股票的因子均值，
        与下一期组合收益率求相关系数。

        Args:
            factor_matrix_history: 每期的因子矩阵列表
            portfolio_returns: 每期的组合收益率列表

        Returns:
            {factor_name: attribution_score}
        """
        if len(factor_matrix_history) < 2 or not portfolio_returns:
            return {}

        # 收集所有因子名称
        factor_names: set[str] = set()
        for matrix in factor_matrix_history:
            for scores in matrix.scores.values():
                factor_names.update(scores.keys())

        if not factor_names:
            return {}

        attribution: dict[str, float] = {}

        for fname in factor_names:
            # 对每个因子，取每期截面上全市场因子均值
            factor_means = []
            for matrix in factor_matrix_history:
                vals = [
                    scores.get(fname)
                    for scores in matrix.scores.values()
                    if fname in scores
                    and scores[fname] is not None
                    and scores[fname] == scores[fname]  # not NaN
                ]
                if vals:
                    factor_means.append(sum(vals) / len(vals))
                else:
                    factor_means.append(0.0)

            # 因子均值序列 vs 下一期收益（对齐长度）
            n = min(len(factor_means) - 1, len(portfolio_returns))
            if n < 2:
                attribution[fname] = 0.0
                continue

            x = factor_means[:n]
            y = portfolio_returns[:n]
            attribution[fname] = self._correlation(x, y)

        return attribution

    def compute_factor_turnover(self,
                                factor_matrix_history: list[FactorMatrix]) -> dict[str, float]:
        """计算每期因子排名的变化程度

        对每个因子，比较相邻两期的截面排名，计算平均排名变化比例。

        Returns:
            {factor_name: turnover_score}  0=完全不变, 1=完全翻转
        """
        if len(factor_matrix_history) < 2:
            return {}

        factor_names: set[str] = set()
        for matrix in factor_matrix_history:
            for scores in matrix.scores.values():
                factor_names.update(scores.keys())

        turnover: dict[str, float] = {}

        for fname in factor_names:
            changes = []
            prev_ranks = None

            for matrix in factor_matrix_history:
                # 当期排名
                stock_vals = {}
                for code, scores in matrix.scores.items():
                    val = scores.get(fname)
                    if val is not None and val == val:
                        stock_vals[code] = val

                if not stock_vals:
                    prev_ranks = None
                    continue

                sorted_codes = sorted(stock_vals, key=lambda c: stock_vals[c], reverse=True)
                ranks = {code: i for i, code in enumerate(sorted_codes)}

                if prev_ranks is not None:
                    # 计算共同股票的排名变化
                    common = set(ranks.keys()) & set(prev_ranks.keys())
                    if common:
                        n = len(sorted_codes)
                        total_change = sum(
                            abs(ranks[c] - prev_ranks[c]) for c in common
                        )
                        # 归一化：最大可能变化 = n * (n-1) / 2
                        max_change = n * (n - 1) / 2 if n > 1 else 1
                        changes.append(total_change / max_change / len(common) * n)

                prev_ranks = ranks

            turnover[fname] = round(sum(changes) / len(changes), 4) if changes else 0.0

        return turnover

    @staticmethod
    def _correlation(x: list[float], y: list[float]) -> float:
        """皮尔逊相关系数"""
        n = len(x)
        if n < 2:
            return 0.0

        mean_x = sum(x) / n
        mean_y = sum(y) / n

        cov = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        var_x = sum((v - mean_x) ** 2 for v in x)
        var_y = sum((v - mean_y) ** 2 for v in y)

        denom = math.sqrt(var_x * var_y)
        if denom == 0:
            return 0.0

        return cov / denom
