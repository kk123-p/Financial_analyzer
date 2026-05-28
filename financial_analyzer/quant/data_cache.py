"""量化因子数据 SQLite 缓存

缓存策略：
- 每只股票的每种数据类型单独缓存
- 缓存键：(code, data_type, end_date)
- 财务数据（income/balance/cashflow）缓存 7 天
- 行情数据（daily/basic）缓存 1 天
- 内存 + SQLite 双层缓存
"""
import hashlib
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# 环境变量禁用缓存（测试用）
_CACHE_DISABLED = os.environ.get("QUANT_CACHE_DISABLED", "0") == "1"

_CACHE_DIR = Path.home() / ".financialanalyzer" / "cache"
_DB_PATH = _CACHE_DIR / "quant_factor_data.db"

# 缓存过期时间
_EXPIRY = {
    "daily": timedelta(hours=12),
    "basic": timedelta(hours=12),
    "income": timedelta(days=7),
    "balance": timedelta(days=7),
    "cashflow": timedelta(days=7),
    "margin": timedelta(hours=12),
    "hk_hold": timedelta(hours=12),
    "dividend": timedelta(days=30),
}
_DEFAULT_EXPIRY = timedelta(days=1)


class QuantDataCache:
    """量化因子数据缓存（内存 + SQLite）"""

    def __init__(self):
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._memory: dict[str, tuple[float, pd.DataFrame]] = {}  # key -> (ts, df)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(_DB_PATH)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quant_cache (
                    cache_key TEXT PRIMARY KEY,
                    code TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    data_blob BLOB NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_qc_code_type ON quant_cache(code, data_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_qc_expires ON quant_cache(expires_at)")
            conn.commit()

    @staticmethod
    def _make_key(code: str, data_type: str, end_date: str) -> str:
        return f"{code}_{data_type}_{end_date}"

    def get(self, code: str, data_type: str, end_date: str) -> pd.DataFrame | None:
        """获取缓存数据，返回 DataFrame 或 None"""
        if _CACHE_DISABLED:
            return None
        key = self._make_key(code, data_type, end_date)
        now = time.time()

        # 1. 内存缓存
        with self._lock:
            if key in self._memory:
                ts, df = self._memory[key]
                if now - ts < _EXPIRY.get(data_type, _DEFAULT_EXPIRY).total_seconds():
                    return df
                else:
                    del self._memory[key]

        # 2. SQLite 缓存
        try:
            with sqlite3.connect(str(_DB_PATH)) as conn:
                row = conn.execute(
                    "SELECT data_blob, created_at FROM quant_cache WHERE cache_key = ? AND expires_at > ?",
                    (key, now)
                ).fetchone()
            if row:
                blob, created_at = row
                df = pd.read_parquet(__import__("io").BytesIO(blob))
                with self._lock:
                    self._memory[key] = (created_at, df)
                return df
        except Exception:
            pass

        return None

    def put(self, code: str, data_type: str, end_date: str, df: pd.DataFrame):
        """存入缓存"""
        if _CACHE_DISABLED or df is None or df.empty:
            return

        key = self._make_key(code, data_type, end_date)
        now = time.time()
        expiry = _EXPIRY.get(data_type, _DEFAULT_EXPIRY)
        expires_at = now + expiry.total_seconds()

        # 内存
        with self._lock:
            self._memory[key] = (now, df)

        # SQLite
        try:
            buf = __import__("io").BytesIO()
            df.to_parquet(buf, index=False)
            blob = buf.getvalue()
            with sqlite3.connect(str(_DB_PATH)) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO quant_cache (cache_key, code, data_type, end_date, data_blob, created_at, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (key, code, data_type, end_date, blob, now, expires_at)
                )
                conn.commit()
        except Exception:
            pass

    def clear_expired(self):
        """清理过期缓存"""
        now = time.time()
        with self._lock:
            expired = [k for k, (ts, _) in self._memory.items()
                       if now - ts > 86400]  # 超过 1 天的内存缓存
            for k in expired:
                del self._memory[k]

        try:
            with sqlite3.connect(str(_DB_PATH)) as conn:
                conn.execute("DELETE FROM quant_cache WHERE expires_at < ?", (now,))
                conn.commit()
        except Exception:
            pass


# 全局单例
_cache_instance: QuantDataCache | None = None
_cache_lock = threading.Lock()


def get_quant_cache() -> QuantDataCache:
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = QuantDataCache()
    return _cache_instance
