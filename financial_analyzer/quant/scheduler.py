"""定时任务 — 月末自动触发信号生成"""
import asyncio
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)


def is_last_trading_day_of_month(ref_date: date = None) -> bool:
    """判断是否为每月最后一个交易日"""
    if ref_date is None:
        ref_date = date.today()
    tomorrow = ref_date + timedelta(days=1)
    return ref_date.month != tomorrow.month


class SignalScheduler:
    """信号生成定时调度器"""

    def __init__(self, check_interval_hours: int = 6):
        self.check_interval = check_interval_hours
        self._last_run_date: date | None = None

    async def run_if_due(self, callback) -> bool:
        """如果是月末交易日且今天还没跑过，执行回调"""
        today = date.today()

        if not is_last_trading_day_of_month(today):
            return False

        if self._last_run_date == today:
            return False

        logger.info(f"月末交易日 {today}，触发信号生成")
        try:
            await callback()
            self._last_run_date = today
            return True
        except Exception as e:
            logger.error(f"信号生成失败: {e}")
            return False

    def mark_run(self, run_date: date):
        self._last_run_date = run_date
