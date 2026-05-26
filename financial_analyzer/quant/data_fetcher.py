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
    "daily",       # 日线行情 → 动量/低波/PS/FCFYield (≈0.3s per call)
    "basic",       # 每日指标 → PE/PB/PS/总市值 (≈0.3s)
    "income",      # 利润表 → ROE/毛利率/净利率/增长率 (≈0.5s)
    "balance",     # 资产负债表 → ROE/ROIC/负债率/流动比率 (≈0.5s)
    "cashflow",    # 现金流量表 → FCF收益率/现金流增长 (≈0.5s)
]

# 高级数据类型（需要 Tushare 更高权限，按需启用）
OPTIONAL_DATA_TYPES = [
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
                 max_workers: int = 4,
                 progress_callback=None):
        self.adapter = adapter
        self.start_date = start_date
        self.max_workers = max_workers
        self._rate_lock = threading.Lock()
        self._last_call_time = 0.0
        self._call_count = 0
        self._fetch_stats: dict[str, int] = {}
        self._progress_callback = progress_callback  # fn(stage, current, total, msg)

    def enrich_stock_info(self, stocks: list[StockInfo]) -> list[StockInfo]:
        """用 Tushare stock_basic 批量补充 StockInfo（一次性获取全部，不逐只调用）"""
        codes_to_enrich = [s for s in stocks if not s.name]
        if not codes_to_enrich:
            return stocks

        total = len(codes_to_enrich)
        logger.info(f"开始补充 {total} 只股票基本信息...")

        # 尝试用 Tushare stock_basic 批量获取（全市场一次性查询）
        try:
            if self.adapter.tushare_pro:
                df = self.adapter.tushare_pro.stock_basic(
                    exchange='', list_status='L',
                    fields='ts_code,name,industry,market,list_date'
                )
                if df is not None and not df.empty:
                    # 构建代码→信息映射
                    info_map = {}
                    for _, row in df.iterrows():
                        code = str(row.get("ts_code", ""))[:6]
                        info_map[code] = {
                            "name": str(row.get("name", "")),
                            "industry": str(row.get("industry", "")),
                            "market": str(row.get("market", "")),
                            "list_date": str(row.get("list_date", "")),
                        }

                    enriched = 0
                    for stock in codes_to_enrich:
                        info = info_map.get(stock.code)
                        if info:
                            stock.name = info["name"]
                            stock.industry = info["industry"]
                            stock.market = info["market"]
                            if "ST" in stock.name.upper():
                                stock.is_st = True
                            list_str = info["list_date"].replace("-", "")[:8]
                            try:
                                if len(list_str) == 8:
                                    stock.listed_date = date(
                                        int(list_str[:4]),
                                        int(list_str[4:6]),
                                        int(list_str[6:8]),
                                    )
                            except (ValueError, IndexError):
                                pass
                            enriched += 1

                    logger.info(f"StockInfo 补充完成: {enriched}/{total} 只")
                    if self._progress_callback:
                        self._progress_callback("enriching", enriched, total,
                                                f"补充基本信息 {enriched}/{total}")
                    return stocks
        except Exception as e:
            logger.warning(f"批量获取 stock_basic 失败，回退到逐只查询: {e}")

        # 回退：逐只获取
        code_map = {s.code: s for s in stocks}
        for i, stock in enumerate(codes_to_enrich):
            try:
                df = self._rate_limited_fetch(stock.code, "stock_basic")
                if df is not None and not df.empty:
                    row = df.iloc[0]
                    stock.name = str(row.get("name", stock.code))
                    stock.industry = str(row.get("industry", ""))
                    stock.market = str(row.get("market", ""))
                    list_date_val = row.get("list_date")
                    if pd.notna(list_date_val):
                        list_str = str(list_date_val).replace("-", "")[:8]
                        try:
                            if len(list_str) == 8:
                                stock.listed_date = date(
                                    int(list_str[:4]),
                                    int(list_str[4:6]),
                                    int(list_str[6:8]),
                                )
                        except (ValueError, IndexError):
                            pass
                    if "ST" in stock.name.upper():
                        stock.is_st = True
            except Exception as e:
                logger.debug(f"获取 {stock.code} 基本信息失败: {e}")

            if (i + 1) % 20 == 0 and self._progress_callback:
                self._progress_callback("enriching", i + 1, total,
                                        f"补充基本信息 {i + 1}/{total}")

        logger.info(f"StockInfo 补充完成: {total} 只")
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

                if completed % 100 == 0 or completed == total:
                    pct = 100 * completed / total
                    logger.info(f"数据获取进度: {completed}/{total} ({pct:.0f}%)")
                    if self._progress_callback:
                        self._progress_callback(
                            "fetching", completed, total,
                            f"获取数据 {completed}/{total} ({pct:.0f}%)"
                        )

        logger.info(f"数据获取完成: {len(result)}/{len(stocks)} 只有效数据")
        for dt, count in self._fetch_stats.items():
            logger.info(f"  {dt}: {count} 只")

        return result

    def _rate_limited_fetch(self, code: str, data_type: str) -> Optional[pd.DataFrame]:
        """带速率限制的单次数据获取（锁外sleep，支持并行）"""
        # 预留时间槽
        with self._rate_lock:
            now = time.time()
            if self._call_count == 0:
                slot = now
            else:
                slot = max(self._last_call_time + CALL_INTERVAL, now)
            self._last_call_time = slot
            self._call_count += 1

        # 在锁外等待（不阻塞其他线程）
        wait = slot - time.time()
        if wait > 0:
            time.sleep(wait)

        end_date = date.today().strftime("%Y%m%d")
        return self.adapter.get_stock_data(code, self.start_date, end_date, data_type)
