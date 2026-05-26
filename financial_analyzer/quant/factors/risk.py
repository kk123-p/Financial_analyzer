"""风险因子"""
from typing import Optional
import numpy as np
from .base import BaseFactor, FactorInput


def _safe_val(df, col) -> Optional[float]:
    if df is None or col not in df.columns:
        return None
    v = df[col].iloc[0]
    try:
        f = float(v)
        return f if f == f else None
    except (ValueError, TypeError):
        return None


class DebtRatioFactor(BaseFactor):
    name = "debt_ratio"
    category = "risk"
    label = "资产负债率"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        liab = _safe_val(input_data.balance, "total_liab")
        assets = _safe_val(input_data.balance, "total_assets")
        if liab is None or assets is None or assets <= 0:
            return None
        ratio = liab / assets
        return self._validate_result(-ratio)


class CurrentRatioFactor(BaseFactor):
    name = "current_ratio"
    category = "risk"
    label = "流动比率 (最优区间)"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        assets = _safe_val(input_data.balance, "total_assets")
        liab = _safe_val(input_data.balance, "total_liab")
        if assets is None or liab is None or liab == 0:
            return None
        ratio = assets / liab
        optimal = 2.0
        return self._validate_result(-abs(ratio - optimal))
