"""量化系统数据模型"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class StockInfo:
    """股票基础信息"""
    code: str
    name: str
    industry: str = ""
    market: str = ""
    is_st: bool = False
    is_suspended: bool = False
    listed_date: Optional[date] = None


@dataclass
class FactorValue:
    """单个因子的计算结果"""
    stock_code: str
    factor_name: str
    raw_value: Optional[float] = None
    z_score: Optional[float] = None
    percentile: Optional[float] = None


@dataclass
class FactorConfig:
    """因子配置"""
    name: str
    label: str
    category: str               # value/quality/growth/momentum/sentiment/low_vol/risk
    direction: str = "positive"  # positive=越大越好, negative=越小越好
    weight: float = 1.0
    enabled: bool = True


@dataclass
class FactorMatrix:
    """全市场因子矩阵（截面数据）"""
    date: date
    stocks: list[str] = field(default_factory=list)
    scores: dict[str, dict[str, float]] = field(default_factory=dict)
    industries: dict[str, str] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def get_score(self, stock_code: str, factor_name: str) -> Optional[float]:
        return self.scores.get(stock_code, {}).get(factor_name)

    def composite_score(self, stock_code: str, weights: dict[str, float]) -> float:
        """加权综合得分"""
        stock_scores = self.scores.get(stock_code, {})
        total = 0.0
        for name, weight in weights.items():
            score = stock_scores.get(name, 0.0)
            total += score * weight
        return total


@dataclass
class SignalResult:
    """单只股票的调仓信号"""
    stock_code: str
    stock_name: str
    action: str          # buy / sell / hold / increase / decrease
    composite_score: float
    target_weight: float
    reason: str


@dataclass
class TradeList:
    """一次调仓的完整清单"""
    date: date
    universe: str
    signals: list[SignalResult] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def buys(self) -> list[SignalResult]:
        return [s for s in self.signals if s.action == "buy"]

    @property
    def sells(self) -> list[SignalResult]:
        return [s for s in self.signals if s.action == "sell"]


@dataclass
class ICRecord:
    """单月 IC 记录"""
    date: date
    factor_name: str
    ic_value: float
    n_stocks: int
    p_value: Optional[float] = None


@dataclass
class ICSummary:
    """因子 IC 汇总统计"""
    factor_name: str
    mean_ic: float
    std_ic: float
    ir: float
    ic_positive_pct: float
    t_stat: float
    n_months: int


@dataclass
class ICDecayRecord:
    """单月、单持仓周期的 IC 记录"""
    date: date
    factor_name: str
    horizon: int
    ic_value: float
    n_stocks: int


@dataclass
class DecayCurve:
    """因子衰减曲线 — 不同持仓周期的 IC 均值"""
    factor_name: str
    horizons: list[int]
    mean_ic_by_horizon: list[float]
    ic_positive_pct_by_horizon: list[float]
    n_months_by_horizon: list[int]
