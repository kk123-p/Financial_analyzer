"""交易流水记录"""
import json
import os
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class TradeRecord:
    date: str
    stock_code: str
    stock_name: str
    action: str  # buy / sell
    price: float
    shares: int
    commission: float
    total_cost: float


class TradeLedger:
    """交易流水记录"""

    def __init__(self):
        self.trades: list[TradeRecord] = []

    def record(self, trade: TradeRecord):
        self.trades.append(trade)

    def get_trades(self, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> list[TradeRecord]:
        result = self.trades
        if start_date:
            result = [t for t in result if t.date >= start_date]
        if end_date:
            result = [t for t in result if t.date <= end_date]
        return result

    def get_trades_by_stock(self, stock_code: str) -> list[TradeRecord]:
        return [t for t in self.trades if t.stock_code == stock_code]

    def total_commission(self) -> float:
        return sum(t.commission for t in self.trades)

    def save_to_file(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = [asdict(t) for t in self.trades]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_file(self, path: str):
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.trades = [TradeRecord(**item) for item in data]
