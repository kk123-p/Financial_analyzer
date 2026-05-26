"""动量因子"""
from typing import Optional
from .base import BaseFactor, FactorInput


def _price_momentum(daily, lookback: int) -> Optional[float]:
    """计算过去N期的价格动量

    使用 min(lookback, len(prices)-1) 作为实际回溯期，
    确保在有足够数据时使用完整回溯期，数据不足时使用全部可用数据。
    """
    if daily is None or "close" not in daily.columns:
        return None
    prices = daily["close"].dropna().values
    if len(prices) < 2:
        return None
    effective_lookback = min(lookback, len(prices) - 1)
    current = float(prices[0])
    start = float(prices[effective_lookback])
    if start == 0:
        return None
    return (current - start) / start


class PriceMomentum3M(BaseFactor):
    name = "momentum_3m"
    category = "momentum"
    label = "3个月价格动量"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return self._validate_result(_price_momentum(input_data.daily, 60))


class PriceMomentum6M(BaseFactor):
    name = "momentum_6m"
    category = "momentum"
    label = "6个月价格动量"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return self._validate_result(_price_momentum(input_data.daily, 120))


class PriceMomentum12M(BaseFactor):
    name = "momentum_12m"
    category = "momentum"
    label = "12个月价格动量"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        return self._validate_result(_price_momentum(input_data.daily, 250))


class VolumeMomentum(BaseFactor):
    name = "volume_momentum"
    category = "momentum"
    label = "成交量动量"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        if input_data.daily is None or "vol" not in input_data.daily.columns:
            return None
        vols = input_data.daily["vol"].dropna().values
        if len(vols) < 21:
            return None
        recent = float(vols[:5].mean())
        past = float(vols[5:21].mean())
        if past == 0:
            return None
        return self._validate_result((recent - past) / past)
