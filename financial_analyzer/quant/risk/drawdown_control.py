"""最大回撤控制模块"""
import logging

logger = logging.getLogger(__name__)


class DrawdownController:
    """最大回撤控制器 — 回撤超阈值时按比例减仓"""

    def __init__(
        self,
        max_drawdown_pct: float = 15.0,
        step_pct: float = 5.0,
        reduce_ratio: float = 0.25,
    ):
        self.max_drawdown_pct = max_drawdown_pct
        self.step_pct = step_pct
        self.reduce_ratio = reduce_ratio

    def compute_position_scale(self, current_drawdown_pct: float) -> float:
        """根据当前回撤计算仓位比例（0~1）

        Args:
            current_drawdown_pct: 当前回撤百分比（正数，如 15 表示 -15%）

        Returns:
            仓位缩放比例，1.0 = 满仓，0.0 = 空仓
        """
        if current_drawdown_pct < self.max_drawdown_pct:
            return 1.0
        excess = current_drawdown_pct - self.max_drawdown_pct
        steps = int(excess / self.step_pct) + 1
        scale = max(0.0, 1.0 - steps * self.reduce_ratio)
        if scale < 1.0:
            logger.info(
                f"回撤控制: 当前回撤 {current_drawdown_pct:.1f}%, "
                f"仓位缩放至 {scale:.0%}"
            )
        return scale
