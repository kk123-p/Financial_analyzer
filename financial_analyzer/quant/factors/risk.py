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


class LogMarketCap(BaseFactor):
    name = "log_market_cap"
    category = "risk"
    label = "对数市值"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        total_mv = _safe_val(input_data.daily, "total_mv")
        if total_mv is None or total_mv <= 0:
            return None
        return self._validate_result(-np.log(total_mv))


class AvgTurnover(BaseFactor):
    name = "avg_turnover"
    category = "risk"
    label = "20日平均换手率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        daily = input_data.daily
        if daily is None or daily.empty:
            return None
        turnover_col = next(
            (c for c in ["turnover_rate", "turn"] if c in daily.columns), None
        )
        if turnover_col is not None:
            vals = daily[turnover_col].dropna()
            if len(vals) < 1:
                return None
            return self._validate_result(float(vals.iloc[:20].mean()))
        # fallback: compute from vol / total_mv
        if "vol" not in daily.columns or "total_mv" not in daily.columns:
            return None
        vol = daily["vol"].dropna().iloc[:20]
        mv = daily["total_mv"].dropna().iloc[:20]
        count = min(len(vol), len(mv))
        if count < 1:
            return None
        ratio = vol.iloc[:count].values / mv.iloc[:count].values
        return self._validate_result(float(np.mean(ratio)))
