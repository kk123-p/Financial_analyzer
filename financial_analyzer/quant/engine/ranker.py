"""排名与硬过滤"""
from typing import Optional
from ..models import StockInfo


class Ranker:
    """TOP-N排名 + 硬过滤"""

    def __init__(self, top_n: int = 30, max_price: float = 15.0):
        self.top_n = top_n
        self.max_price = max_price

    def rank(self, composite_scores: dict[str, float],
             stocks: list[StockInfo],
             prices: Optional[dict[str, float]] = None) -> list[StockInfo]:
        """按综合得分排名，应用硬过滤，返回TOP-N"""
        stock_map = {s.code: s for s in stocks}

        valid_codes = set()
        for s in stocks:
            if s.is_st or s.is_suspended:
                continue
            if prices and s.code in prices and prices[s.code] > self.max_price:
                continue
            if s.code in composite_scores:
                valid_codes.add(s.code)

        ranked = sorted(
            valid_codes,
            key=lambda code: composite_scores.get(code, -999),
            reverse=True,
        )

        top_codes = ranked[:self.top_n]
        return [stock_map[code] for code in top_codes if code in stock_map]
