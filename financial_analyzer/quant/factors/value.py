"""价值因子"""
from typing import Optional
from .base import BaseFactor, FactorInput


def _safe_get(df, col):
    """安全从DataFrame中取值"""
    if df is None or col not in df.columns:
        return None
    val = df[col].iloc[0]
    try:
        f = float(val)
        return f if f == f else None  # NaN check
    except (ValueError, TypeError):
        return None


class PEFactor(BaseFactor):
    name = "pe"
    category = "value"
    label = "市盈率"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        pe = _safe_get(input_data.basic, "pe")
        if pe is None or pe <= 0:
            return None
        return self._validate_result(-1.0 / pe)  # 取倒数，低PE得分高


class PBFactor(BaseFactor):
    name = "pb"
    category = "value"
    label = "市净率"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        pb = _safe_get(input_data.basic, "pb")
        if pb is None or pb <= 0:
            return None
        return self._validate_result(-1.0 / pb)


class PSFactor(BaseFactor):
    name = "ps"
    category = "value"
    label = "市销率"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        revenue = _safe_get(input_data.income, "revenue")
        total_mv = _safe_get(input_data.daily, "total_mv")
        if not revenue or not total_mv or revenue <= 0:
            return None
        ps = total_mv / revenue
        if ps <= 0:
            return None
        return self._validate_result(-1.0 / ps)


class DividendYieldFactor(BaseFactor):
    name = "dividend_yield"
    category = "value"
    label = "股息率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        """从dividend数据表获取股息率"""
        div = input_data.dividend
        if div is None or div.empty:
            return None
        col = next((c for c in ["dv_ratio", "div_yield"] if c in div.columns), None)
        if col is None:
            return None
        return self._validate_result(_safe_get(div, col))


class FCFYieldFactor(BaseFactor):
    name = "fcf_yield"
    category = "value"
    label = "自由现金流收益率"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        ocf = _safe_get(input_data.cashflow, "n_cashflow_act")
        total_mv = _safe_get(input_data.daily, "total_mv")
        if not ocf or not total_mv or total_mv <= 0:
            return None
        return self._validate_result(ocf / total_mv)


class EV_EBITDA(BaseFactor):
    name = "ev_ebitda"
    category = "value"
    label = "EV/EBITDA"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        total_mv = _safe_get(input_data.daily, "total_mv")
        total_liab = _safe_get(input_data.balance, "total_liab")
        monetary = _safe_get(input_data.balance, "monetary_assets")
        if monetary is None:
            monetary = _safe_get(input_data.balance, "total_assets")
        operate_profit = _safe_get(input_data.income, "operate_profit")
        if total_mv is None or total_liab is None or monetary is None:
            return None
        if operate_profit is None or operate_profit <= 0:
            return None
        ev = total_mv + total_liab - monetary
        if ev <= 0:
            return None
        ratio = ev / operate_profit
        if ratio <= 0:
            return None
        return self._validate_result(-1.0 / ratio)
