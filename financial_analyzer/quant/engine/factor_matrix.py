"""因子矩阵构建器 — 批量计算全市场股票的因子值"""
from datetime import date
from typing import Optional

import pandas as pd

from ..factors.base import BaseFactor, FactorInput
from ..models import StockInfo, FactorMatrix


class FactorMatrixBuilder:
    """构建因子矩阵（全市场 × 全因子）"""

    def __init__(self, factors: Optional[list[BaseFactor]] = None):
        self.factors = factors or []

    def register(self, factor: BaseFactor):
        self.factors.append(factor)

    def build(self, stocks: list[StockInfo],
              stock_data: dict[str, dict[str, pd.DataFrame]]) -> FactorMatrix:
        matrix = FactorMatrix(date=date.today())
        matrix.stocks = [s.code for s in stocks]
        matrix.industries = {s.code: s.industry for s in stocks}

        for stock in stocks:
            data = stock_data.get(stock.code, {})
            factor_input = FactorInput(
                stock_code=stock.code,
                daily=data.get("daily"),
                basic=data.get("basic"),
                income=data.get("income"),
                balance=data.get("balance"),
                cashflow=data.get("cashflow"),
                margin=data.get("margin"),
                hk_hold=data.get("hk_hold"),
                dividend=data.get("dividend"),
            )

            stock_scores = {}
            for factor in self.factors:
                value = factor.compute(factor_input)
                if value is not None:
                    stock_scores[factor.name] = value

            if stock_scores:
                matrix.scores[stock.code] = stock_scores

        matrix.stocks = [code for code in matrix.stocks if code in matrix.scores]
        return matrix
