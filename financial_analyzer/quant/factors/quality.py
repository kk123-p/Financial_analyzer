"""质量因子"""
from typing import Optional
from .base import BaseFactor, FactorInput


def _safe_val(df, col):
    if df is None or col not in df.columns:
        return None
    v = df[col].iloc[0]
    try:
        f = float(v)
        return f if f == f else None
    except (ValueError, TypeError):
        return None


class ROEFactor(BaseFactor):
    name = "roe"
    category = "quality"
    label = "净资产收益率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        np_val = _safe_val(input_data.income, "net_profit")
        equity = _safe_val(input_data.balance, "total_equity")
        if np_val is None or equity is None or equity <= 0:
            return None
        return self._validate_result(np_val / equity)


class ROICFactor(BaseFactor):
    name = "roic"
    category = "quality"
    label = "资本回报率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        np_val = _safe_val(input_data.income, "net_profit")
        equity = _safe_val(input_data.balance, "total_equity")
        debt = _safe_val(input_data.balance, "total_liab")
        if np_val is None or equity is None or debt is None:
            return None
        invested = equity + debt
        if invested <= 0:
            return None
        return self._validate_result(np_val / invested)


class GrossMarginFactor(BaseFactor):
    name = "gross_margin"
    category = "quality"
    label = "毛利率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        rev = _safe_val(input_data.income, "revenue")
        cost = _safe_val(input_data.income, "oper_cost")
        if rev is None or cost is None or rev <= 0:
            return None
        return self._validate_result((rev - cost) / rev)


class NetMarginFactor(BaseFactor):
    name = "net_margin"
    category = "quality"
    label = "净利率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        rev = _safe_val(input_data.income, "revenue")
        np_val = _safe_val(input_data.income, "net_profit")
        if rev is None or np_val is None or rev <= 0 or np_val <= 0:
            return None
        return self._validate_result(np_val / rev)
