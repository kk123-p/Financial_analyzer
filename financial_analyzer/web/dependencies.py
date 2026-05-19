"""依赖注入 — FastAPI 单例管理"""
from dataclasses import dataclass, field
from threading import Lock
import pandas as pd

from financial_analyzer.cache.manager import DataCacheManager
from financial_analyzer.data_sources.adapter import DataSourceAdapter


_cache: DataCacheManager | None = None
_adapter: DataSourceAdapter | None = None
_cache_lock = Lock()
_adapter_lock = Lock()


def get_cache() -> DataCacheManager:
    global _cache
    if _cache is None:
        with _cache_lock:
            if _cache is None:
                _cache = DataCacheManager()
    return _cache


def get_adapter() -> DataSourceAdapter:
    global _adapter
    if _adapter is None:
        with _adapter_lock:
            if _adapter is None:
                import logging
                logger = logging.getLogger(__name__)
                logger.info("Initializing DataSourceAdapter (first use)...")
                cache = get_cache()
                _adapter = DataSourceAdapter(cache)
                logger.info(f"Active source: {_adapter.active_source}")
    return _adapter


@dataclass
class SessionState:
    """服务器端 session 状态 — 替代 Tkinter 的 self._current_data"""
    data: dict = field(default_factory=dict)
    stock_code: str = ""
    data_lock: Lock = field(default_factory=Lock)

    def set_data(self, data: dict, stock_code: str):
        with self.data_lock:
            self.data = data
            self.stock_code = stock_code

    def get_data(self) -> dict:
        with self.data_lock:
            return dict(self.data)

    def get_stock_code(self) -> str:
        with self.data_lock:
            return self.stock_code
