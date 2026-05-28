"""止盈止损规则模块"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class StopLossManager:
    """止盈止损管理器"""

    def __init__(
        self,
        stop_loss_pct: float = -10.0,
        take_profit_pct: float = 30.0,
        portfolio_stop_pct: Optional[float] = None,
    ):
        self.stop_loss_pct = stop_loss_pct / 100  # 如 -10% -> -0.1
        self.take_profit_pct = take_profit_pct / 100
        self.portfolio_stop_pct = portfolio_stop_pct / 100 if portfolio_stop_pct else None

    def check_stock_stop(self, cost_price: float, current_price: float) -> Optional[str]:
        """检查个股止盈止损

        Returns:
            'stop_loss' / 'take_profit' / None
        """
        if cost_price <= 0:
            return None
        pnl_pct = (current_price - cost_price) / cost_price
        if pnl_pct <= self.stop_loss_pct:
            logger.info(f"触发止损: 成本={cost_price:.2f}, 现价={current_price:.2f}, 亏损={pnl_pct:.1%}")
            return "stop_loss"
        if pnl_pct >= self.take_profit_pct:
            logger.info(f"触发止盈: 成本={cost_price:.2f}, 现价={current_price:.2f}, 盈利={pnl_pct:.1%}")
            return "take_profit"
        return None

    def check_portfolio_stop(self, current_drawdown_pct: float) -> bool:
        """检查组合止损"""
        if self.portfolio_stop_pct is None:
            return False
        return current_drawdown_pct / 100 >= self.portfolio_stop_pct
