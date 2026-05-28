"""约束优化器 — 在TOP-N中选择满足约束的最优组合"""
import numpy as np
from typing import Optional
from ..models import StockInfo
from .position_sizer import PositionSizer, EqualWeightSizer


class ConstraintOptimizer:
    """组合约束优化"""

    def __init__(self,
                 min_stocks: int = 5,
                 max_stocks: int = 8,
                 min_industries: int = 3,
                 max_industry_weight: float = 0.40,
                 cash_reserve: float = 0.10,
                 position_sizer: Optional[PositionSizer] = None):
        self.min_stocks = min_stocks
        self.max_stocks = max_stocks
        self.min_industries = min_industries
        self.max_industry_weight = max_industry_weight
        self.cash_reserve = cash_reserve
        self.position_sizer = position_sizer or EqualWeightSizer()

    def optimize(self, ranked_stocks: list[StockInfo],
                 scores: Optional[dict[str, float]] = None) -> list[StockInfo]:
        """从排序后的TOP-N中选择满足约束的子集"""
        if not ranked_stocks:
            return []

        result: list[StockInfo] = []
        result_codes: set[str] = set()
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
            result_codes.add(stock.code)
            industry_counts[industry] = current_count + 1

        # 检查行业数约束
        if len(set(s.industry for s in result)) < self.min_industries:
            existing_industries = set(s.industry for s in result)
            for stock in ranked_stocks:
                if stock.code in result_codes:
                    continue
                if len(result) >= self.max_stocks:
                    break
                industry = stock.industry or "其他"
                if industry not in existing_industries:
                    result.append(stock)
                    result_codes.add(stock.code)
                    existing_industries.add(industry)
                    if len(existing_industries) >= self.min_industries:
                        break

        # 确保最少持仓数
        if len(result) < self.min_stocks and len(ranked_stocks) >= self.min_stocks:
            for stock in ranked_stocks:
                if stock.code not in result_codes:
                    result.append(stock)
                    result_codes.add(stock.code)
                    if len(result) >= self.min_stocks:
                        break

        return result

    def compute_weights(
        self,
        stocks: list[StockInfo],
        scores: dict[str, float],
        cov_matrix: Optional[np.ndarray] = None,
    ) -> dict[str, float]:
        """使用 position_sizer 计算各资产权重

        Args:
            stocks: 优化后的持仓列表
            scores: 综合得分
            cov_matrix: 协方差矩阵（可选）

        Returns:
            {stock_code: weight}，权重之和为 1
        """
        if not stocks:
            return {}
        stock_scores = {s.code: scores.get(s.code, 0.0) for s in stocks}
        stock_codes = [s.code for s in stocks]
        weights = self.position_sizer.compute_weights(
            stock_scores, cov_matrix=cov_matrix, stock_codes=stock_codes
        )
        # 只返回在 stocks 中的权重
        valid_codes = set(stock_codes)
        return {c: w for c, w in weights.items() if c in valid_codes}
