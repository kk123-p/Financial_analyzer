"""约束优化器 — 在TOP-N中选择满足约束的最优组合"""
from typing import Optional
from ..models import StockInfo


class ConstraintOptimizer:
    """组合约束优化"""

    def __init__(self,
                 min_stocks: int = 5,
                 max_stocks: int = 8,
                 min_industries: int = 3,
                 max_industry_weight: float = 0.40,
                 cash_reserve: float = 0.10):
        self.min_stocks = min_stocks
        self.max_stocks = max_stocks
        self.min_industries = min_industries
        self.max_industry_weight = max_industry_weight
        self.cash_reserve = cash_reserve

    def optimize(self, ranked_stocks: list[StockInfo],
                 scores: dict[str, float]) -> list[StockInfo]:
        """从排序后的TOP-N中选择满足约束的子集"""
        if not ranked_stocks:
            return []

        result: list[StockInfo] = []
        industry_counts: dict[str, int] = {}

        for stock in ranked_stocks:
            if len(result) >= self.max_stocks:
                break

            industry = stock.industry or "其他"
            current_count = industry_counts.get(industry, 0)
            max_in_industry = int(self.max_stocks * self.max_industry_weight)

            if current_count >= max_in_industry and len(result) >= self.min_stocks:
                continue

            result.append(stock)
            industry_counts[industry] = current_count + 1

        # 检查行业数约束
        if len(set(s.industry for s in result)) < self.min_industries:
            existing_industries = set(s.industry for s in result)
            for stock in ranked_stocks:
                if stock in result:
                    continue
                industry = stock.industry or "其他"
                if industry not in existing_industries and len(result) < self.max_stocks:
                    result.append(stock)
                    existing_industries.add(industry)
                    if len(existing_industries) >= self.min_industries:
                        break

        # 确保最少持仓数
        if len(result) < self.min_stocks and len(ranked_stocks) >= self.min_stocks:
            for stock in ranked_stocks:
                if stock not in result:
                    result.append(stock)
                    if len(result) >= self.min_stocks:
                        break

        return result
