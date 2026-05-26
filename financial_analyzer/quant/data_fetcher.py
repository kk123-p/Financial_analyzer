"""批量数据获取器 — 为量化管道提供全市场数据"""
import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Optional

import pandas as pd

from ..data_sources.adapter import DataSourceAdapter
from .models import StockInfo

logger = logging.getLogger(__name__)

# 因子计算需要的数据类型
FACTOR_DATA_TYPES = [
    "daily",       # 日线行情 → 动量/低波/PS/FCFYield
    "basic",       # 每日指标 → PE/PB/PS/总市值
    "income",      # 利润表 → ROE/毛利率/净利率/增长率
    "balance",     # 资产负债表 → ROE/ROIC/负债率/流动比率
    "cashflow",    # 现金流量表 → FCF收益率/现金流增长
    "margin",      # 融资融券 → 融资变化
    "hk_hold",     # 北向资金 → 北向流入
    "dividend",    # 分红 → 股息率
]

# Tushare 免费用户速率限制
MAX_CALLS_PER_MINUTE = 150
CALL_INTERVAL = 60.0 / MAX_CALLS_PER_MINUTE  # 0.4 秒


class QuantDataFetcher:
    """批量获取全市场股票的因子所需数据"""

    def __init__(self, adapter: DataSourceAdapter,
                 start_date: str = "20240101",
                 max_workers: int = 4):
        self.adapter = adapter
        self.start_date = start_date
        self.max_workers = max_workers
        self._rate_lock = threading.Lock()
        self._last_call_time = 0.0
        self._call_count = 0
        self._fetch_stats: dict[str, int] = {}

    def enrich_stock_info(self, stocks: list[StockInfo]) -> list[StockInfo]:
        """用 Tushare stock_basic 数据补充 StockInfo 的 name/industry/market/listed_date"""
        codes = [s.code for s in stocks if not s.name]
        if not codes:
            return stocks

        code_map = {s.code: s for s in stocks}

        for code in codes:
            try:
                df = self._rate_limited_fetch(code, "stock_basic")
                if df is not None and not df.empty:
                    row = df.iloc[0]
                    stock = code_map[code]
                    stock.name = str(row.get("name", code))
                    stock.industry = str(row.get("industry", ""))
                    stock.market = str(row.get("market", ""))
                    list_date = row.get("list_date")
                    if pd.notna(list_date):
                        list_str = str(list_date).replace("-", "")[:8]
                        try:
                            stock.listed_date = date(
                                int(list_str[:4]),
                                int(list_str[4:6]),
                                int(list_str[6:8]),
                            )
                        except (ValueError, IndexError):
                            pass
                    # ST / 停牌 从 name 推断（Tushare stock_basic 不直接提供）
                    if "ST" in stock.name.upper():
                        stock.is_st = True
            except Exception as e:
                logger.warning(f"获取 {code} 基本信息失败: {e}")

        logger.info(f"StockInfo 补充完成: {len(codes)} 只，成功 {sum(1 for s in stocks if s.name)}")
        return stocks

    def fetch_all(self, stocks: list[StockInfo]) -> dict[str, dict[str, pd.DataFrame]]:
        """批量获取所有股票的因子数据（并行，遵守速率限制）

        Returns:
            {stock_code: {data_type: DataFrame}}
        """
        result: dict[str, dict[str, pd.DataFrame]] = {}
        self._fetch_stats = {}
        total = len(stocks) * len(FACTOR_DATA_TYPES)

        logger.info(f"开始批量获取 {len(stocks)} 只股票 × {len(FACTOR_DATA_TYPES)} 种数据")
        logger.info(f"预估耗时: {total * CALL_INTERVAL / self.max_workers:.0f} 秒")

        # 并行获取，共享速率锁
        from concurrent.futures import ThreadPoolExecutor, as_completed

        tasks = [
            (stock.code, data_type)
            for stock in stocks
            for data_type in FACTOR_DATA_TYPES
        ]

        completed = 0

        def fetch_one(code, data_type):
            try:
                return code, data_type, self._rate_limited_fetch(code, data_type)
            except Exception as e:
                logger.debug(f"获取 {code} {data_type} 失败: {e}")
                return code, data_type, None

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(fetch_one, c, d): (c, d) for c, d in tasks}

            for future in as_completed(futures):
                code, data_type, df = future.result()
                completed += 1

                if df is not None and not df.empty:
                    if code not in result:
                        result[code] = {}
                    result[code][data_type] = df
                    self._fetch_stats[data_type] = self._fetch_stats.get(data_type, 0) + 1

                if completed % 500 == 0:
                    logger.info(f"数据获取进度: {completed}/{total} ({100*completed/total:.0f}%)")

        logger.info(f"数据获取完成: {len(result)}/{len(stocks)} 只有效数据")
        for dt, count in self._fetch_stats.items():
            logger.info(f"  {dt}: {count} 只")

        return result

    def _rate_limited_fetch(self, code: str, data_type: str) -> Optional[pd.DataFrame]:
        """带速率限制的单次数据获取"""
        with self._rate_lock:
            now = time.time()
            elapsed = now - self._last_call_time
            if elapsed < CALL_INTERVAL and self._call_count > 0:
                time.sleep(CALL_INTERVAL - elapsed)
            self._last_call_time = time.time()
            self._call_count += 1

        end_date = date.today().strftime("%Y%m%d")
        return self.adapter.get_stock_data(code, self.start_date, end_date, data_type)
