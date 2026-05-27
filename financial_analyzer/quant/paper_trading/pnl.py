"""虚拟盈亏跟踪"""
import json
import os
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class PnLSnapshot:
    date: str
    total_value: float
    cash: float
    holdings_value: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    return_pct: float


class PnLTracker:
    """虚拟盈亏跟踪"""

    def __init__(self, initial_capital: float):
        self.initial_capital = initial_capital
        self.snapshots: list[PnLSnapshot] = []
        self.realized_pnl: float = 0.0

    def record_snapshot(self, date: str, portfolio_value: float,
                        cash: float, holdings_value: float):
        unrealized_pnl = portfolio_value - self.initial_capital - self.realized_pnl
        total_pnl = portfolio_value - self.initial_capital
        return_pct = total_pnl / self.initial_capital if self.initial_capital else 0.0

        snapshot = PnLSnapshot(
            date=date,
            total_value=round(portfolio_value, 2),
            cash=round(cash, 2),
            holdings_value=round(holdings_value, 2),
            unrealized_pnl=round(unrealized_pnl, 2),
            realized_pnl=round(self.realized_pnl, 2),
            total_pnl=round(total_pnl, 2),
            return_pct=round(return_pct, 4),
        )
        self.snapshots.append(snapshot)

    def add_realized_pnl(self, pnl: float):
        self.realized_pnl += pnl

    def get_return_series(self) -> list[float]:
        return [s.return_pct for s in self.snapshots]

    def get_latest_snapshot(self) -> Optional[PnLSnapshot]:
        return self.snapshots[-1] if self.snapshots else None

    def save_to_file(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "initial_capital": self.initial_capital,
            "realized_pnl": self.realized_pnl,
            "snapshots": [asdict(s) for s in self.snapshots],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_file(self, path: str):
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.initial_capital = data["initial_capital"]
        self.realized_pnl = data.get("realized_pnl", 0.0)
        self.snapshots = [PnLSnapshot(**s) for s in data.get("snapshots", [])]
