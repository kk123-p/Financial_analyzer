"""质量因子"""
from typing import Optional
import numpy as np
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


def _safe_val_at(df, col, idx):
    """按行索引取值，越界返回None"""
    if df is None or col not in df.columns:
        return None
    if idx >= len(df):
        return None
    v = df[col].iloc[idx]
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


class PiotroskiFScore(BaseFactor):
    name = "piotroski_fscore"
    category = "quality"
    label = "Piotroski F-Score"
    direction = "positive"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        inc = input_data.income
        bal = input_data.balance
        cf = input_data.cashflow

        # current period (row 0) and previous period (row 1)
        np_cur = _safe_val_at(inc, "net_profit", 0)
        np_prev = _safe_val_at(inc, "net_profit", 1)
        rev_cur = _safe_val_at(inc, "revenue", 0)
        cost_cur = _safe_val_at(inc, "oper_cost", 0)
        rev_prev = _safe_val_at(inc, "revenue", 1)
        cost_prev = _safe_val_at(inc, "oper_cost", 1)

        assets_cur = _safe_val_at(bal, "total_assets", 0)
        assets_prev = _safe_val_at(bal, "total_assets", 1)
        equity_cur = _safe_val_at(bal, "total_equity", 0)
        liab_cur = _safe_val_at(bal, "total_liab", 0)
        liab_prev = _safe_val_at(bal, "total_liab", 1)

        ocf_cur = _safe_val_at(cf, "n_cashflow_act", 0)

        if np_cur is None or assets_cur is None or assets_cur <= 0:
            return None

        score = 0.0

        # 1. ROA > 0
        roa_cur = np_cur / assets_cur
        if roa_cur > 0:
            score += 1

        # 2. Operating cashflow > 0
        if ocf_cur is not None and ocf_cur > 0:
            score += 1

        # 3. ROA improving
        if np_prev is not None and assets_prev is not None and assets_prev > 0:
            roa_prev = np_prev / assets_prev
            if roa_cur > roa_prev:
                score += 1

        # 4. Cashflow > net_profit (accruals quality)
        if ocf_cur is not None and ocf_cur > np_cur:
            score += 1

        # 5. Debt ratio improving (liab/assets decreasing)
        if liab_cur is not None and liab_prev is not None and assets_prev is not None and assets_prev > 0:
            dr_cur = liab_cur / assets_cur
            dr_prev = liab_prev / assets_prev
            if dr_cur < dr_prev:
                score += 1

        # 6. Current ratio improving (assets/liab increasing)
        # Use available data; skip if previous period missing
        if liab_cur is not None and liab_prev is not None and liab_cur > 0 and liab_prev > 0 and assets_prev is not None:
            cr_cur = assets_cur / liab_cur
            cr_prev = assets_prev / liab_prev
            if cr_cur > cr_prev:
                score += 1

        # 7. No dilution - skip if data unavailable (no shares column)

        # 8. Gross margin improving
        if (rev_cur is not None and cost_cur is not None and rev_cur > 0 and
                rev_prev is not None and cost_prev is not None and rev_prev > 0):
            gm_cur = (rev_cur - cost_cur) / rev_cur
            gm_prev = (rev_prev - cost_prev) / rev_prev
            if gm_cur > gm_prev:
                score += 1

        # 9. Asset turnover improving (revenue/assets)
        if (rev_cur is not None and assets_prev is not None and assets_prev > 0 and
                rev_prev is not None and assets_cur > 0):
            at_cur = rev_cur / assets_cur
            at_prev = rev_prev / assets_prev
            if at_cur > at_prev:
                score += 1

        return self._validate_result(score / 9.0)


class AccrualsRatio(BaseFactor):
    name = "accruals_ratio"
    category = "quality"
    label = "应计比率"
    direction = "negative"

    def compute(self, input_data: FactorInput) -> Optional[float]:
        np_val = _safe_val(input_data.income, "net_profit")
        ocf = _safe_val(input_data.cashflow, "n_cashflow_act")
        assets = _safe_val(input_data.balance, "total_assets")
        if np_val is None or ocf is None or assets is None or assets <= 0:
            return None
        return self._validate_result(-((np_val - ocf) / assets))
