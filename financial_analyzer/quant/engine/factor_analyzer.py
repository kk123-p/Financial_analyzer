"""因子 IC/IR 分析器。"""
import logging
from datetime import date
from typing import Optional

import numpy as np
from scipy.stats import spearmanr

from ..models import ICRecord, ICSummary, ICDecayRecord, DecayCurve

logger = logging.getLogger(__name__)


class FactorAnalyzer:
    """因子 Information Coefficient / Information Ratio 分析器。"""

    def __init__(self, min_sample_size: int = 30):
        self.min_sample_size = min_sample_size
        self._ic_history: dict[str, list[ICRecord]] = {}
        self._decay_history: dict[str, list[ICDecayRecord]] = {}

    def compute_monthly_ic(
        self,
        matrix,
        forward_returns: dict[str, float],
        ref_date: Optional[date] = None,
    ) -> dict[str, Optional[float]]:
        """计算单月各因子的 IC（Spearman 秩相关）。

        Args:
            matrix: 标准化后的因子矩阵
            forward_returns: {stock_code: 下期收益率}
            ref_date: 当月调仓日期

        Returns:
            {factor_name: IC 值或 None（样本不足时）}
        """
        # matrix.scores 结构: {stock_code: {factor_name: value}}
        # 转置为 {factor_name: {stock_code: value}}
        factor_columns: dict[str, dict[str, float]] = {}
        for stock_code, stock_scores in matrix.scores.items():
            for factor_name, value in stock_scores.items():
                factor_columns.setdefault(factor_name, {})[stock_code] = value

        results = {}
        for factor_name, scores in factor_columns.items():
            common_stocks = [
                code for code in scores
                if code in forward_returns and not np.isnan(scores[code])
            ]
            if len(common_stocks) < self.min_sample_size:
                results[factor_name] = None
                record = ICRecord(
                    date=ref_date or date.today(),
                    factor_name=factor_name,
                    ic_value=float('nan'),
                    n_stocks=len(common_stocks),
                )
                self._ic_history.setdefault(factor_name, []).append(record)
                logger.debug(
                    f"因子 {factor_name}: 样本不足 ({len(common_stocks)}<{self.min_sample_size}), 跳过"
                )
                continue

            factor_vals = np.array([scores[s] for s in common_stocks])
            return_vals = np.array([forward_returns[s] for s in common_stocks])

            if np.std(factor_vals) < 1e-10 or np.std(return_vals) < 1e-10:
                ic_val = 0.0
                p_val = 1.0
            else:
                corr, p_val = spearmanr(factor_vals, return_vals)
                ic_val = float(corr) if not np.isnan(corr) else 0.0

            record = ICRecord(
                date=ref_date or date.today(),
                factor_name=factor_name,
                ic_value=ic_val,
                n_stocks=len(common_stocks),
                p_value=float(p_val),
            )
            self._ic_history.setdefault(factor_name, []).append(record)
            results[factor_name] = ic_val

        return results

    def compute_ic_summary(self) -> dict[str, ICSummary]:
        """汇总所有月份的 IC，计算均值/标准差/IR/胜率/t 统计量。"""
        summaries = {}
        for factor_name, records in self._ic_history.items():
            valid = [r for r in records if not np.isnan(r.ic_value)]
            if len(valid) < 3:
                logger.info(f"因子 {factor_name}: 有效 IC 月数不足 ({len(valid)}<3), 跳过汇总")
                continue

            ic_values = [r.ic_value for r in valid]
            mean_ic = float(np.mean(ic_values))
            std_ic = float(np.std(ic_values, ddof=1))
            ir = mean_ic / std_ic if std_ic > 1e-10 else 0.0
            ic_positive_pct = sum(1 for v in ic_values if v > 0) / len(ic_values)
            t_stat = mean_ic / (std_ic / np.sqrt(len(ic_values))) if std_ic > 1e-10 else 0.0

            summaries[factor_name] = ICSummary(
                factor_name=factor_name,
                mean_ic=mean_ic,
                std_ic=std_ic,
                ir=ir,
                ic_positive_pct=ic_positive_pct,
                t_stat=t_stat,
                n_months=len(valid),
            )

        return summaries

    def get_ic_timeseries(self) -> dict[str, list[dict]]:
        """返回各因子 IC 的时序数据，用于绘图。"""
        result = {}
        for factor_name, records in self._ic_history.items():
            result[factor_name] = [
                {
                    "date": r.date.isoformat(),
                    "ic": r.ic_value if not np.isnan(r.ic_value) else None,
                    "n_stocks": r.n_stocks,
                }
                for r in records
            ]
        return result

    def compute_multi_horizon_ic(
        self,
        factor_values: dict[str, dict[str, float]],
        forward_returns_by_horizon: dict[int, dict[str, float]],
        ref_date: date,
    ) -> dict[int, dict[str, Optional[float]]]:
        """计算多持仓周期的因子 IC。

        Args:
            factor_values: {stock_code: {factor_name: value}}
            forward_returns_by_horizon: {horizon: {stock_code: return}}
            ref_date: 当月调仓日期

        Returns:
            {horizon: {factor_name: IC 值或 None}}
        """
        results: dict[int, dict[str, Optional[float]]] = {}
        for horizon, fwd_returns in forward_returns_by_horizon.items():
            results[horizon] = {}
            for factor_name in set(
                fn for scores in factor_values.values() for fn in scores
            ):
                common_stocks = [
                    code for code in factor_values
                    if code in fwd_returns
                    and factor_name in factor_values[code]
                    and not np.isnan(factor_values[code][factor_name])
                ]
                if len(common_stocks) < self.min_sample_size:
                    results[horizon][factor_name] = None
                    self._decay_history.setdefault(factor_name, []).append(
                        ICDecayRecord(
                            date=ref_date,
                            factor_name=factor_name,
                            horizon=horizon,
                            ic_value=float("nan"),
                            n_stocks=len(common_stocks),
                        )
                    )
                    continue

                factor_vals = np.array(
                    [factor_values[s][factor_name] for s in common_stocks]
                )
                return_vals = np.array([fwd_returns[s] for s in common_stocks])

                if np.std(factor_vals) < 1e-10 or np.std(return_vals) < 1e-10:
                    ic_val = 0.0
                else:
                    corr, _ = spearmanr(factor_vals, return_vals)
                    ic_val = float(corr) if not np.isnan(corr) else 0.0

                results[horizon][factor_name] = ic_val
                self._decay_history.setdefault(factor_name, []).append(
                    ICDecayRecord(
                        date=ref_date,
                        factor_name=factor_name,
                        horizon=horizon,
                        ic_value=ic_val,
                        n_stocks=len(common_stocks),
                    )
                )

        return results

    def compute_decay_curve(self) -> dict[str, DecayCurve]:
        """汇总衰减历史，为每个因子生成 DecayCurve。"""
        curves: dict[str, DecayCurve] = {}
        for factor_name, records in self._decay_history.items():
            valid = [r for r in records if not np.isnan(r.ic_value)]
            if not valid:
                continue

            horizon_map: dict[int, list[float]] = {}
            for r in valid:
                horizon_map.setdefault(r.horizon, []).append(r.ic_value)

            horizons = sorted(horizon_map.keys())
            mean_ic_by_horizon = [
                float(np.mean(horizon_map[h])) for h in horizons
            ]
            ic_positive_pct_by_horizon = [
                sum(1 for v in horizon_map[h] if v > 0) / len(horizon_map[h])
                for h in horizons
            ]
            n_months_by_horizon = [len(horizon_map[h]) for h in horizons]

            curves[factor_name] = DecayCurve(
                factor_name=factor_name,
                horizons=horizons,
                mean_ic_by_horizon=mean_ic_by_horizon,
                ic_positive_pct_by_horizon=ic_positive_pct_by_horizon,
                n_months_by_horizon=n_months_by_horizon,
            )

        return curves

    def reset(self):
        """清空历史数据。"""
        self._ic_history.clear()
        self._decay_history.clear()
