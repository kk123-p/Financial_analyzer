"""滚动绩效指标计算模块"""
import numpy as np
import pandas as pd
from typing import Optional


class RollingMetricsCalculator:
    """滚动绩效指标计算器"""

    def __init__(self, window: int = 12):
        self.window = window

    def rolling_sharpe(self, monthly_returns: pd.Series) -> pd.Series:
        """滚动 Sharpe（年化）"""
        if len(monthly_returns) < self.window:
            return pd.Series(dtype=float)
        rolling_mean = monthly_returns.rolling(self.window).mean()
        rolling_std = monthly_returns.rolling(self.window).std()
        return (rolling_mean / rolling_std * np.sqrt(12)).dropna()

    def rolling_drawdown(self, equity_curve: pd.Series) -> pd.Series:
        """滚动最大回撤"""
        if len(equity_curve) < self.window:
            return pd.Series(dtype=float)
        rolling_max = equity_curve.rolling(self.window, min_periods=1).max()
        drawdown = (equity_curve - rolling_max) / rolling_max
        return drawdown

    def rolling_alpha_beta(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        window: Optional[int] = None,
    ) -> tuple[pd.Series, pd.Series]:
        """滚动 Alpha / Beta（相对基准）"""
        w = window or self.window
        aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        if len(aligned) < w:
            return pd.Series(dtype=float), pd.Series(dtype=float)

        port = aligned.iloc[:, 0]
        bench = aligned.iloc[:, 1]

        betas = pd.Series(index=port.index, dtype=float)
        alphas = pd.Series(index=port.index, dtype=float)

        for i in range(w - 1, len(port)):
            y = port.iloc[i - w + 1: i + 1].values
            x = bench.iloc[i - w + 1: i + 1].values
            if np.std(x) < 1e-10:
                betas.iloc[i] = 0.0
                alphas.iloc[i] = np.mean(y) * 12
            else:
                cov = np.cov(y, x)
                beta = cov[0, 1] / cov[1, 1]
                alpha = np.mean(y) - beta * np.mean(x)
                betas.iloc[i] = beta
                alphas.iloc[i] = alpha * 12

        return alphas.dropna(), betas.dropna()

    def compute_all(
        self,
        monthly_returns: list[float],
        equity_curve: list[float],
        benchmark_returns: Optional[list[float]] = None,
    ) -> dict:
        """计算所有滚动指标"""
        port_ret = pd.Series(monthly_returns)
        equity = pd.Series(equity_curve)

        result = {
            "rolling_sharpe": self.rolling_sharpe(port_ret).tolist(),
            "rolling_drawdown": self.rolling_drawdown(equity).tolist(),
        }

        if benchmark_returns:
            bench_ret = pd.Series(benchmark_returns)
            alpha, beta = self.rolling_alpha_beta(port_ret, bench_ret)
            result["rolling_alpha"] = alpha.tolist()
            result["rolling_beta"] = beta.tolist()

        return result
