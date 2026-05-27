"""绩效指标计算"""
import math
from dataclasses import dataclass, field


@dataclass
class PerformanceMetrics:
    """回测绩效指标"""
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    volatility: float = 0.0
    calmar_ratio: float = 0.0
    monthly_returns: list = field(default_factory=list)
    benchmark_return: float = 0.0


class MetricsCalculator:
    """绩效指标计算器"""

    @staticmethod
    def compute(portfolio_values: list[float],
                risk_free_rate: float = 0.03) -> PerformanceMetrics:
        """从组合净值序列计算所有指标

        Args:
            portfolio_values: 每个调仓日的组合总市值列表
            risk_free_rate: 年化无风险利率
        """
        if len(portfolio_values) < 2:
            return PerformanceMetrics()

        # 计算月度收益率
        monthly_returns = []
        for i in range(1, len(portfolio_values)):
            prev = portfolio_values[i - 1]
            if prev > 0:
                monthly_returns.append(portfolio_values[i] / prev - 1)
            else:
                monthly_returns.append(0.0)

        total_return = portfolio_values[-1] / portfolio_values[0] - 1
        years = (len(portfolio_values) - 1) / 12.0  # 月频

        ann_ret = MetricsCalculator.annualized_return(total_return, max(years, 1 / 12))
        vol = MetricsCalculator.volatility(monthly_returns)
        sharpe = MetricsCalculator.sharpe_ratio(monthly_returns, risk_free_rate)
        mdd = MetricsCalculator.max_drawdown(portfolio_values)
        wr = MetricsCalculator.win_rate(monthly_returns)
        calmar = ann_ret / abs(mdd) if mdd != 0 else 0.0

        return PerformanceMetrics(
            total_return=round(total_return, 6),
            annualized_return=round(ann_ret, 6),
            sharpe_ratio=round(sharpe, 4),
            max_drawdown=round(mdd, 6),
            win_rate=round(wr, 4),
            volatility=round(vol, 6),
            calmar_ratio=round(calmar, 4),
            monthly_returns=[round(r, 6) for r in monthly_returns],
        )

    @staticmethod
    def annualized_return(total_return: float, years: float) -> float:
        """年化收益率"""
        if years <= 0:
            return 0.0
        if total_return <= -1:
            return -1.0
        return (1 + total_return) ** (1 / years) - 1

    @staticmethod
    def sharpe_ratio(returns: list[float], risk_free_rate: float) -> float:
        """夏普比率（年化）"""
        if not returns:
            return 0.0
        monthly_rf = risk_free_rate / 12
        excess = [r - monthly_rf for r in returns]
        mean_excess = sum(excess) / len(excess)
        variance = sum((e - mean_excess) ** 2 for e in excess) / len(excess)
        std = math.sqrt(variance)
        if std == 0:
            return 0.0
        return mean_excess / std * math.sqrt(12)

    @staticmethod
    def max_drawdown(values: list[float]) -> float:
        """最大回撤（返回负数）"""
        if not values:
            return 0.0
        peak = values[0]
        mdd = 0.0
        for v in values:
            if v > peak:
                peak = v
            dd = (v - peak) / peak if peak > 0 else 0
            if dd < mdd:
                mdd = dd
        return mdd

    @staticmethod
    def win_rate(monthly_returns: list[float]) -> float:
        """月度胜率"""
        if not monthly_returns:
            return 0.0
        wins = sum(1 for r in monthly_returns if r > 0)
        return wins / len(monthly_returns)

    @staticmethod
    def volatility(monthly_returns: list[float]) -> float:
        """年化波动率"""
        if not monthly_returns:
            return 0.0
        mean = sum(monthly_returns) / len(monthly_returns)
        variance = sum((r - mean) ** 2 for r in monthly_returns) / len(monthly_returns)
        return math.sqrt(variance) * math.sqrt(12)
