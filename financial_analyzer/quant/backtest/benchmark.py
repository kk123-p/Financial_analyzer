"""基准指数对比模块"""
import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

BENCHMARK_CODES = {
    "沪深300": "000300.SH",
    "中证500": "000905.SH",
    "中证1000": "000852.SH",
    "上证50": "000016.SH",
    "创业板指": "399006.SZ",
}


class BenchmarkComparator:
    """基准指数对比器"""

    def __init__(self, benchmark_code: str = "000300.SH"):
        self.benchmark_code = benchmark_code

    def compute_excess_returns(
        self, portfolio_returns: pd.Series, benchmark_returns: pd.Series
    ) -> pd.Series:
        """计算超额收益"""
        aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        if aligned.empty:
            return pd.Series(dtype=float)
        return aligned.iloc[:, 0] - aligned.iloc[:, 1]

    def compute_information_ratio(self, excess_returns: pd.Series) -> float:
        """计算信息比率 = 年化超额收益 / 跟踪误差"""
        if len(excess_returns) < 2:
            return 0.0
        ann_excess = excess_returns.mean() * 12
        tracking_error = excess_returns.std() * np.sqrt(12)
        return float(ann_excess / tracking_error) if tracking_error > 1e-10 else 0.0

    def compute_tracking_error(self, excess_returns: pd.Series) -> float:
        """计算跟踪误差"""
        if len(excess_returns) < 2:
            return 0.0
        return float(excess_returns.std() * np.sqrt(12))

    def compute_full_comparison(
        self,
        portfolio_monthly_returns: pd.Series,
        benchmark_monthly_returns: pd.Series,
    ) -> dict:
        """完整的基准对比结果"""
        excess = self.compute_excess_returns(portfolio_monthly_returns, benchmark_monthly_returns)
        return {
            "benchmark_code": self.benchmark_code,
            "excess_returns": excess.tolist(),
            "information_ratio": round(self.compute_information_ratio(excess), 4),
            "tracking_error": round(self.compute_tracking_error(excess), 4),
            "benchmark_total_return": round(float(benchmark_monthly_returns.sum()), 6),
            "benchmark_annualized": round(float(benchmark_monthly_returns.mean() * 12), 6),
        }
