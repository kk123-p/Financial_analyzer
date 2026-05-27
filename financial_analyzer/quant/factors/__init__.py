"""量化因子模块"""
from .base import BaseFactor, FactorInput
from .value import PEFactor, PBFactor, PSFactor, DividendYieldFactor, FCFYieldFactor, EV_EBITDA
from .quality import ROEFactor, ROICFactor, GrossMarginFactor, NetMarginFactor, PiotroskiFScore, AccrualsRatio
from .growth import RevenueGrowthFactor, NetProfitGrowthFactor, CashflowGrowthFactor, ROETrend
from .low_vol import Volatility60D, MaxDrawdown120D, DownsideDeviation
from .risk import DebtRatioFactor, CurrentRatioFactor, LogMarketCap, AvgTurnover

__all__ = [
    "BaseFactor", "FactorInput",
    # value
    "PEFactor", "PBFactor", "PSFactor", "DividendYieldFactor", "FCFYieldFactor", "EV_EBITDA",
    # quality
    "ROEFactor", "ROICFactor", "GrossMarginFactor", "NetMarginFactor", "PiotroskiFScore", "AccrualsRatio",
    # growth
    "RevenueGrowthFactor", "NetProfitGrowthFactor", "CashflowGrowthFactor", "ROETrend",
    # low_vol
    "Volatility60D", "MaxDrawdown120D", "DownsideDeviation",
    # risk
    "DebtRatioFactor", "CurrentRatioFactor", "LogMarketCap", "AvgTurnover",
]
