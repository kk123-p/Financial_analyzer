"""成长因子"""
from typing import Optional
import numpy as np
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


class ROETrend(BaseFactor):
    name = "roe_trend"
    category = "growth"
    label = "ROE趋势"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        inc = input_data.income
        bal = input_data.balance
        if inc is None or bal is None:
            return None
        if "net_profit" not in inc.columns or "total_equity" not in bal.columns:
            return None
        np_vals = inc["net_profit"].dropna().values
        eq_vals = bal["total_equity"].dropna().values
        count = min(len(np_vals), len(eq_vals))
        if count < 3:
            return None
        roes = []
        for i in range(count):
            eq = float(eq_vals[i])
            if eq <= 0:
                return None
            roes.append(float(np_vals[i]) / eq)
        x = np.arange(len(roes), dtype=float)
        slope = np.polyfit(x, roes, 1)[0]
        return self._validate_result(float(slope))
