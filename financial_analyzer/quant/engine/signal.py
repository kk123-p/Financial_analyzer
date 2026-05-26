"""信号生成器 — 对比当前持仓与优化结果，生成调仓信号"""
from datetime import date
from typing import Optional

from ..models import StockInfo, SignalResult, TradeList


class SignalGenerator:
    """生成买入/卖出/调仓信号"""

    def __init__(self, cash_reserve: float = 0.10):
        self.cash_reserve = cash_reserve

    def generate(self,
                 optimized_stocks: list[StockInfo],
                 scores: dict[str, float],
                 current_holdings: set[str],
                 universe: str,
                 ref_date: Optional[date] = None) -> TradeList:
        trade_list = TradeList(
            date=ref_date or date.today(),
            universe=universe,
        )

        optimized_codes = {s.code for s in optimized_stocks}

        # 卖出：当前持有但不在优化结果中的
        for code in current_holdings - optimized_codes:
            score = scores.get(code, -999)
            trade_list.signals.append(SignalResult(
                stock_code=code,
                stock_name=code,
                action="sell",
                composite_score=score,
                target_weight=0.0,
                reason=f"综合得分 {score:.2f}，排名跌出TOP{len(optimized_stocks)}",
            ))

        # 买入/持有：优化结果中的股票
        n = len(optimized_stocks)
        if n == 0:
            return trade_list

        invest_weight = (1 - self.cash_reserve) / n

        for stock in optimized_stocks:
            score = scores.get(stock.code, 0)
            # 计算排名
            sorted_codes = sorted(scores.keys(), key=lambda c: scores.get(c, -999), reverse=True)
            try:
                rank = sorted_codes.index(stock.code) + 1
            except ValueError:
                rank = n

            if stock.code in current_holdings:
                action = "hold"
                reason = f"继续持有，综合得分排名第{rank}"
            else:
                action = "buy"
                reason = f"因子综合得分排名第{rank}，纳入组合"

            trade_list.signals.append(SignalResult(
                stock_code=stock.code,
                stock_name=stock.name,
                action=action,
                composite_score=score,
                target_weight=round(invest_weight, 4),
                reason=reason,
            ))

        return trade_list
