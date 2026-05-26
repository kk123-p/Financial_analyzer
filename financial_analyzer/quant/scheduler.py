"""定时任务 — 月末自动触发信号生成"""
import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from ..data_sources.adapter import DataSourceAdapter

logger = logging.getLogger(__name__)


class SignalScheduler:
    """信号生成定时调度器 — 使用 Tushare 交易日历"""

    def __init__(self,
                 adapter: Optional[DataSourceAdapter] = None,
                 check_interval_hours: int = 6):
        self.adapter = adapter
        self.check_interval = check_interval_hours
        self._last_run_date: date | None = None
        self._trading_calendar: set[str] | None = None

    def _load_trading_calendar(self, year: int) -> set[str]:
        """从 Tushare 加载交易日历"""
        if self.adapter is None or self.adapter.tushare_pro is None:
            # 回退：用简单的月份检查
            return set()

        try:
            df = self.adapter.tushare_pro.trade_cal(
                exchange='SSE',
                start_date=f'{year}0101',
                end_date=f'{year}1231',
            )
            if df is None or df.empty:
                return set()

            trading_days = df[df['is_open'] == 1]['cal_date'].astype(str)
            return set(trading_days.values)
        except Exception as e:
            logger.warning(f"加载交易日历失败: {e}")
            return set()

    def is_trading_day(self, ref_date: Optional[date] = None) -> bool:
        """判断是否为交易日"""
        if ref_date is None:
            ref_date = date.today()
        date_str = ref_date.strftime("%Y%m%d")

        # 优先 Tushare 交易日历
        year = ref_date.year
        if self._trading_calendar is None:
            self._trading_calendar = self._load_trading_calendar(year)

        if self._trading_calendar:
            return date_str in self._trading_calendar

        # 回退：排除周末
        return ref_date.weekday() < 5

    def is_last_trading_day_of_month(self, ref_date: Optional[date] = None) -> bool:
        """判断是否为每月最后一个交易日"""
        if ref_date is None:
            ref_date = date.today()

        if not self.is_trading_day(ref_date):
            return False

        # 检查本月剩余天数中是否还有交易日
        next_day = ref_date + timedelta(days=1)
        while next_day.month == ref_date.month:
            if self.is_trading_day(next_day):
                return False
            next_day += timedelta(days=1)

        return True

    async def run_if_due(self, callback) -> bool:
        """如果是月末交易日且今天还没跑过，执行回调"""
        today = date.today()

        if not self.is_last_trading_day_of_month(today):
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
