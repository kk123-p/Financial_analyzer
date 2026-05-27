"""模拟持仓管理"""
import logging
import os
from dataclasses import dataclass
from typing import Optional

from ..models import TradeList
from .ledger import TradeLedger, TradeRecord
from .pnl import PnLTracker

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.expanduser("~"), ".financialanalyzer", "paper_trading")


@dataclass
class HoldingInfo:
    code: str
    name: str
    shares: int
    avg_cost: float
    last_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.shares * self.last_price

    @property
    def unrealized_pnl(self) -> float:
        return self.shares * (self.last_price - self.avg_cost)


class PortfolioManager:
    """模拟持仓管理"""

    def __init__(self, initial_capital: float = 5000.0,
                 commission_rate: float = 0.001):
        self.cash = initial_capital
        self.holdings: dict[str, HoldingInfo] = {}
        self.commission_rate = commission_rate
        self.ledger = TradeLedger()
        self.pnl_tracker = PnLTracker(initial_capital)

    def execute_signals(self, trade_list: TradeList,
                        prices: dict[str, float]) -> list[TradeRecord]:
        """Execute buy/sell signals with real price simulation.

        Sells are executed first to free up cash, then buys.
        Enforces 100-share lot sizing (A-share market standard).
        """
        executed: list[TradeRecord] = []
        date_str = trade_list.date.strftime("%Y%m%d") if hasattr(trade_list.date, "strftime") else str(trade_list.date)

        # 1. Execute sells first
        for signal in trade_list.sells:
            code = signal.stock_code
            if code not in self.holdings:
                continue

            holding = self.holdings[code]
            price = prices.get(code, 0)
            if price <= 0:
                continue

            shares = holding.shares
            proceeds = shares * price
            commission = proceeds * self.commission_rate
            net_proceeds = proceeds - commission

            # Realized P&L = (sell_price - avg_cost) * shares - commission
            realized = (price - holding.avg_cost) * shares - commission
            self.pnl_tracker.add_realized_pnl(realized)

            self.cash += net_proceeds
            del self.holdings[code]

            trade = TradeRecord(
                date=date_str,
                stock_code=code,
                stock_name=signal.stock_name,
                action="sell",
                price=price,
                shares=shares,
                commission=round(commission, 2),
                total_cost=round(net_proceeds, 2),
            )
            self.ledger.record(trade)
            executed.append(trade)
            logger.info(f"  卖出 {code}: {shares}股 x {price}, 佣金 {commission:.2f}, 实现盈亏 {realized:.2f}")

        # 2. Execute buys
        buys = [s for s in trade_list.buys if s.action == "buy"]
        if not buys:
            return executed

        available_cash = self.cash
        per_stock_budget = available_cash / len(buys) if buys else 0

        for signal in buys:
            code = signal.stock_code
            price = prices.get(code, 0)
            if price <= 0:
                continue

            # 100-share lot sizing
            shares = int(per_stock_budget / price / 100) * 100
            if shares <= 0:
                continue

            cost = shares * price
            commission = cost * self.commission_rate
            total_cost = cost + commission

            # Check cash availability
            if total_cost > self.cash:
                shares = int((self.cash * 0.99) / price / 100) * 100
                if shares <= 0:
                    continue
                cost = shares * price
                commission = cost * self.commission_rate
                total_cost = cost + commission

            # Update holdings
            if code in self.holdings:
                existing = self.holdings[code]
                total_shares = existing.shares + shares
                avg_cost = (existing.avg_cost * existing.shares + price * shares) / total_shares
                existing.shares = total_shares
                existing.avg_cost = avg_cost
                existing.last_price = price
            else:
                self.holdings[code] = HoldingInfo(
                    code=code,
                    name=signal.stock_name,
                    shares=shares,
                    avg_cost=price,
                    last_price=price,
                )

            self.cash -= total_cost

            trade = TradeRecord(
                date=date_str,
                stock_code=code,
                stock_name=signal.stock_name,
                action="buy",
                price=price,
                shares=shares,
                commission=round(commission, 2),
                total_cost=round(total_cost, 2),
            )
            self.ledger.record(trade)
            executed.append(trade)
            logger.info(f"  买入 {code}: {shares}股 x {price}, 佣金 {commission:.2f}")

        return executed

    def get_portfolio_value(self, prices: dict[str, float]) -> float:
        holdings_value = 0.0
        for code, holding in self.holdings.items():
            price = prices.get(code, holding.last_price)
            holding.last_price = price
            holdings_value += holding.shares * price
        return self.cash + holdings_value

    def get_holdings_summary(self) -> list[dict]:
        return [
            {
                "code": h.code,
                "name": h.name,
                "shares": h.shares,
                "avg_cost": round(h.avg_cost, 3),
                "last_price": h.last_price,
                "market_value": round(h.market_value, 2),
                "unrealized_pnl": round(h.unrealized_pnl, 2),
            }
            for h in self.holdings.values()
        ]

    def get_position_weights(self, prices: dict[str, float]) -> dict[str, float]:
        total_value = self.get_portfolio_value(prices)
        if total_value <= 0:
            return {}
        weights: dict[str, float] = {}
        for code, holding in self.holdings.items():
            price = prices.get(code, holding.last_price)
            w = (holding.shares * price) / total_value
            if w > 0:
                weights[code] = round(w, 4)
        weights["_cash"] = round(self.cash / total_value, 4)
        return weights

    def record_daily_snapshot(self, date_str: str, prices: dict[str, float]):
        holdings_value = sum(
            h.shares * prices.get(h.code, h.last_price)
            for h in self.holdings.values()
        )
        portfolio_value = self.cash + holdings_value
        self.pnl_tracker.record_snapshot(date_str, portfolio_value, self.cash, holdings_value)

    def save(self, name: str = "default"):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.ledger.save_to_file(os.path.join(DATA_DIR, f"{name}_ledger.json"))
        self.pnl_tracker.save_to_file(os.path.join(DATA_DIR, f"{name}_pnl.json"))

    def load(self, name: str = "default"):
        self.ledger.load_from_file(os.path.join(DATA_DIR, f"{name}_ledger.json"))
        self.pnl_tracker.load_from_file(os.path.join(DATA_DIR, f"{name}_pnl.json"))
