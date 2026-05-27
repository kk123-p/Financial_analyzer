"""低波动因子"""
from typing import Optional
import numpy as np
from .base import BaseFactor, FactorInput


def _daily_returns(daily) -> Optional[np.ndarray]:
    if daily is None or "close" not in daily.columns:
        return None
    prices = daily["close"].dropna().values
    if len(prices) < 3:
        return None
    return np.diff(prices) / prices[:-1]


class Volatility60D(BaseFactor):
    name = "volatility_60d"
    category = "low_vol"
    label = "60日波动率"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        rets = _daily_returns(input_data.daily)
        if rets is None or len(rets) < 60:
            return None
        vol = float(np.std(rets[-60:]))
        if vol == 0:
            return self._validate_result(0.0)
        return self._validate_result(-vol)


class MaxDrawdown120D(BaseFactor):
    name = "max_drawdown_120d"
    category = "low_vol"
    label = "120日最大回撤"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        if input_data.daily is None or "close" not in input_data.daily.columns:
            return None
        prices = input_data.daily["close"].dropna().values
        if len(prices) < 120:
            return None
        recent = prices[:120][::-1]  # 时间正序
        peak = recent[0]
        max_dd = 0.0
        for p in recent:
            if p > peak:
                peak = p
            dd = (p - peak) / peak
            if dd < max_dd:
                max_dd = dd
        return self._validate_result(max_dd)


class DownsideDeviation(BaseFactor):
    name = "downside_deviation"
    category = "low_vol"
    label = "下行偏差"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        rets = _daily_returns(input_data.daily)
        if rets is None or len(rets) < 120:
            return None
        recent = rets[-120:]
        negative = recent[recent < 0]
        if len(negative) < 2:
            return None
        return self._validate_result(-float(np.std(negative)))
