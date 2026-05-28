"""回测数据模型"""
from dataclasses import dataclass, field
from typing import Optional

from .metrics import PerformanceMetrics


@dataclass
class PortfolioSnapshot:
    """某一时间点的组合快照"""
    date: str
    holdings: dict[str, float] = field(default_factory=dict)  # {stock_code: weight}
    cash: float = 0.0
    total_value: float = 0.0


@dataclass
class BacktestResult:
    """回测结果"""
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    metrics: Optional[PerformanceMetrics] = None
    snapshots: list[PortfolioSnapshot] = field(default_factory=list)
    trades: list = field(default_factory=list)  # list of TradeList
    attribution: dict[str, float] = field(default_factory=dict)  # factor attribution
    factor_ic: dict = field(default_factory=dict)  # factor IC/IR analysis
    factor_decay: dict = field(default_factory=dict)  # factor decay curves
    correlation_matrix: dict = field(default_factory=dict)  # {labels, matrix}
    annual_performance: dict = field(default_factory=dict)  # {factor: [{year, q1..q5, long_short}]}
    composite_score: list = field(default_factory=list)  # [{factor, ic_mean, ir, max_corr, score}]
    benchmark_returns: list = field(default_factory=list)
    excess_returns: list = field(default_factory=list)
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    benchmark_code: str = ""
    rolling_sharpe: list = field(default_factory=list)
    rolling_drawdown: list = field(default_factory=list)
    rolling_alpha: list = field(default_factory=list)
    rolling_beta: list = field(default_factory=list)
    cost_breakdown: dict = field(default_factory=dict)
    risk_events: list = field(default_factory=list)
