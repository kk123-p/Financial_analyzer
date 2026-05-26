"""选股池管理 — 从Tushare获取成分股并应用过滤"""
import time
from datetime import date, timedelta
from typing import Optional

from ..data_sources.adapter import DataSourceAdapter
from ..logging_config import get_logger
from .models import StockInfo

logger = get_logger(__name__)

POOL_DEFINITIONS = {
    "沪深300": {"index_code": "000300.SH"},
    "中证500": {"index_code": "000905.SH"},
    "中证800": {"index_code": "000906.SH"},
    "创业板指": {"index_code": "399006.SZ"},
    "科创50": {"index_code": "000688.SH"},
}

CACHE_TTL_SECONDS = 86400  # 24小时


class UniverseManager:
    """选股池管理器"""

    def __init__(self, adapter: Optional[DataSourceAdapter] = None,
                 cache_ttl: int = CACHE_TTL_SECONDS):
        self._adapter = adapter
        self._cache: dict[str, tuple[float, list[StockInfo]]] = {}
        self._cache_ttl = cache_ttl

    @property
    def adapter(self):
        if self._adapter is None:
            self._adapter = DataSourceAdapter()
        return self._adapter

    def pool_names(self) -> list[str]:
        return list(POOL_DEFINITIONS.keys())

    def get_universe(self, pool_name: str) -> list[StockInfo]:
        """获取选股池成分股（未过滤，由调用方在数据补充后过滤）"""
        if pool_name in self._cache:
            ts, stocks = self._cache[pool_name]
            if time.time() - ts < self._cache_ttl:
                logger.debug(f"选股池 [{pool_name}] 命中缓存, {len(stocks)} 只")
                return stocks

        stocks = self._fetch_index_members(pool_name)
        self._cache[pool_name] = (time.time(), stocks)
        logger.info(f"选股池 [{pool_name}]: {len(stocks)} 只成分股")
        return stocks

    def refresh(self, pool_name: str):
        """强制刷新指定选股池"""
        self._cache.pop(pool_name, None)
        return self.get_universe(pool_name)

    def apply_filters(self, stocks: list[StockInfo],
                      prices: Optional[dict[str, float]] = None,
                      max_price: float = 15.0,
                      today: Optional[date] = None,
                      min_months: int = 6) -> list[StockInfo]:
        """应用全部硬过滤（调用方应在 StockInfo 字段补充后调用）"""
        filtered = self._apply_hard_filters(stocks)
        filtered = self._filter_by_age(filtered, today or date.today(), min_months)
        if prices:
            filtered = self._filter_by_price(filtered, prices, max_price)
        logger.info(
            f"过滤: {len(stocks)} → {len(filtered)} "
            f"(排除 ST/停牌/次新/高价)"
        )
        return filtered

    def get_custom_universe(self, pool_names: list[str]) -> list[StockInfo]:
        """合并多个选股池，去重"""
        seen = set()
        result = []
        for name in pool_names:
            for s in self.get_universe(name):
                if s.code not in seen:
                    seen.add(s.code)
                    result.append(s)
        return result

    def _fetch_index_members(self, pool_name: str) -> list[StockInfo]:
        """从Tushare获取指数成分股"""
        definition = POOL_DEFINITIONS.get(pool_name)
        if definition is None:
            return []

        try:
            pro = self.adapter.tushare_pro
            if pro is None:
                logger.warning("Tushare未连接，无法获取成分股")
                return []

            index_code = definition["index_code"]
            trade_date = date.today().strftime("%Y%m%d")

            # 获取最近交易日成分股（Tushare index_weight 需要 trade_date）
            df = pro.index_weight(index_code=index_code, trade_date=trade_date)
            if df is None or df.empty:
                # 回退：尝试不传 trade_date（部分 Tushare 版本行为不同）
                df = pro.index_weight(index_code=index_code)

            if df is None or df.empty:
                return []

            # 确保只取当前指数、最近日期的记录
            if "trade_date" in df.columns:
                df = df[df["trade_date"] == df["trade_date"].max()]

            stocks = []
            for _, row in df.iterrows():
                code = str(row.get("con_code", ""))
                if not code:
                    continue
                stocks.append(StockInfo(code=code, name=""))
            return stocks
        except Exception as e:
            logger.error(f"获取成分股失败 [{pool_name}]: {e}")
            return []

    def _apply_hard_filters(self, stocks: list[StockInfo]) -> list[StockInfo]:
        """硬过滤：排除ST、停牌、次新股"""
        return [s for s in stocks if not s.is_st and not s.is_suspended]

    def _filter_by_price(self, stocks: list[StockInfo],
                         prices: dict[str, float],
                         max_price: float = 15.0) -> list[StockInfo]:
        """过滤股价超过阈值的股票"""
        return [s for s in stocks if prices.get(s.code, 999) <= max_price]

    def _filter_by_age(self, stocks: list[StockInfo],
                       today: date,
                       min_months: int = 6) -> list[StockInfo]:
        """过滤上市不满min_months的次新股"""
        cutoff = today - timedelta(days=min_months * 30)
        return [s for s in stocks
                if s.listed_date is None or s.listed_date <= cutoff]
