"""情绪因子"""
from typing import Optional
from .base import BaseFactor, FactorInput


class NorthBoundFlowFactor(BaseFactor):
    name = "north_bound_flow"
    category = "sentiment"
    label = "北向资金净流入"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        hk = input_data.hk_hold
        if hk is None or hk.empty or "vol" not in hk.columns:
            return None
        vals = hk["vol"].dropna().values
        if len(vals) == 0:
            return None
        total = float(vals.sum())
        avg = float(vals.mean())
        if avg == 0:
            return None
        return self._validate_result(total / avg)


class MarginChangeFactor(BaseFactor):
    name = "margin_change"
    category = "sentiment"
    label = "融资净买入"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        margin = input_data.margin
        if margin is None or margin.empty:
            return None
        col = next((c for c in ["rzye", "fin_balance"] if c in margin.columns), None)
        if col is None:
            return None
        vals = margin[col].dropna().values
        if len(vals) < 2:
            return None
        current = float(vals[0])
        previous = float(vals[1])
        if previous == 0:
            return None
        return self._validate_result((current - previous) / previous)
