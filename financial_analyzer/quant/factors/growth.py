"""成长因子"""
from typing import Optional
from .base import BaseFactor, FactorInput


def _safe_growth(df, col) -> Optional[float]:
    """计算同比增速"""
    if df is None or col not in df.columns:
        return None
    vals = df[col].dropna().values
    if len(vals) < 2:
        return None
    current = float(vals[0])
    previous = float(vals[1])
    if previous == 0:
        return None
    return (current - previous) / previous


class RevenueGrowthFactor(BaseFactor):
    name = "revenue_growth"
    category = "growth"
    label = "营收增长率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return self._validate_result(_safe_growth(input_data.income, "revenue"))


class NetProfitGrowthFactor(BaseFactor):
    name = "net_profit_growth"
    category = "growth"
    label = "净利润增长率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return self._validate_result(_safe_growth(input_data.income, "net_profit"))


class CashflowGrowthFactor(BaseFactor):
    name = "cashflow_growth"
    category = "growth"
    label = "经营现金流增长率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return self._validate_result(_safe_growth(input_data.cashflow, "n_cashflow_act"))
