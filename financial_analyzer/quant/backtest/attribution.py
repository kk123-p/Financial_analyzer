"""因子绩效归因"""
import math
import logging
from typing import Optional

import numpy as np

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

    def multi_factor_attribution(
        self,
        factor_matrix_history: list[FactorMatrix],
        monthly_returns: list[dict[str, float]],
    ) -> dict[str, dict[str, float]]:
        """多因子截面 OLS 回归归因

        每月底对所有股票做截面回归:
            R_i = beta_1*F_1 + beta_2*F_2 + ... + epsilon

        Args:
            factor_matrix_history: 每期的因子矩阵列表
            monthly_returns: 每期的个股收益率列表 [{stock_code: return}, ...]

        Returns:
            {factor_name: {"mean_beta": float, "t_stat": float}}
        """
        if not factor_matrix_history or not monthly_returns:
            return {}

        factor_names: list[str] = []
        seen: set[str] = set()
        for matrix in factor_matrix_history:
            for scores in matrix.scores.values():
                for fname in scores:
                    if fname not in seen:
                        seen.add(fname)
                        factor_names.append(fname)

        if not factor_names:
            return {}

        n_factors = len(factor_names)
        all_betas: list[list[float]] = [[] for _ in range(n_factors)]
        valid_periods = 0

        for t, matrix in enumerate(factor_matrix_history):
            if t >= len(monthly_returns):
                break

            stock_returns = monthly_returns[t]
            if not stock_returns:
                continue

            X_rows = []
            y_vals = []
            for code, ret in stock_returns.items():
                scores = matrix.scores.get(code)
                if scores is None:
                    continue
                row = []
                skip = False
                for fname in factor_names:
                    val = scores.get(fname)
                    if val is None or val != val:
                        skip = True
                        break
                    row.append(val)
                if skip:
                    continue
                X_rows.append(row)
                y_vals.append(ret)

            if len(X_rows) < n_factors + 2:
                continue

            X = np.array(X_rows, dtype=np.float64)
            y = np.array(y_vals, dtype=np.float64)

            try:
                betas, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
            except np.linalg.LinAlgError:
                continue

            for j in range(n_factors):
                all_betas[j].append(betas[j])
            valid_periods += 1

        if valid_periods < 3:
            return {}

        result: dict[str, dict[str, float]] = {}
        for j, fname in enumerate(factor_names):
            betas_j = all_betas[j]
            n = len(betas_j)
            mean_beta = sum(betas_j) / n
            if n >= 2:
                var_b = sum((b - mean_beta) ** 2 for b in betas_j) / (n - 1)
                t_stat = mean_beta / (math.sqrt(var_b / n)) if var_b > 0 else 0.0
            else:
                t_stat = 0.0
            result[fname] = {
                "mean_beta": round(mean_beta, 6),
                "t_stat": round(t_stat, 4),
            }

        return result

    @staticmethod
    def industry_attribution(
        holdings_by_industry: dict[str, list[str]],
        monthly_returns: list[dict[str, float]],
    ) -> dict[str, float]:
        """行业归因 — 按行业分组计算各行业对组合收益的贡献

        Args:
            holdings_by_industry: {industry: [stock_codes]}
            monthly_returns: 每期的个股收益率列表 [{stock_code: return}, ...]

        Returns:
            {industry: contribution_pct}  占总收益的百分比
        """
        if not holdings_by_industry or not monthly_returns:
            return {}

        industry_contrib: dict[str, float] = {ind: 0.0 for ind in holdings_by_industry}
        total_return_sum = 0.0

        for stock_returns in monthly_returns:
            if not stock_returns:
                continue

            period_total = sum(stock_returns.values())
            total_return_sum += period_total

            for industry, codes in holdings_by_industry.items():
                ind_ret = sum(stock_returns.get(c, 0.0) for c in codes)
                industry_contrib[industry] += ind_ret

        if total_return_sum == 0:
            return {ind: 0.0 for ind in industry_contrib}

        return {
            ind: round(contrib / total_return_sum * 100, 2)
            for ind, contrib in industry_contrib.items()
        }
