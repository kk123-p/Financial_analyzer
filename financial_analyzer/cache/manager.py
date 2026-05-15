"""
数据缓存管理器 - 支持内存缓存和 SQLite 持久化缓存
"""
import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

from ..config import CACHE_DIR, DEFAULT_CACHE_EXPIRY_HOURS
from ..logging_config import get_logger

logger = get_logger(__name__)


class DataCacheManager:
    """数据缓存管理器"""

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)

        # 内存缓存（线程安全）
        self._lock = threading.Lock()
        self.memory_cache: dict = {}
        self.cache_expiry: dict = {}

        # 缓存过期时间（小时），可通过 update_expiry() 修改
        self.default_expiry_hours = DEFAULT_CACHE_EXPIRY_HOURS

        # SQLite 缓存
        self.db_path = self.cache_dir / "financial_data.db"
        self._init_database()

    @contextmanager
    def _get_conn(self):
        """获取 SQLite 连接的上下文管理器，确保连接正确关闭"""
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """初始化 SQLite 数据库"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_cache (
                    cache_key TEXT PRIMARY KEY,
                    data_type TEXT,
                    symbol TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    data_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_symbol_type ON data_cache(symbol, data_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_expires ON data_cache(expires_at)")
            conn.commit()

    def get_cache_key(self, data_type: str, symbol: str,
                      start_date: str = None, end_date: str = None) -> str:
        """生成缓存键"""
        parts = [data_type, symbol]
        if start_date:
            parts.append(start_date)
        if end_date:
            parts.append(end_date)
        return "_".join(parts)

    def get_from_cache(self, cache_key: str, max_age_hours: int = None) -> dict | None:
        """从缓存获取数据"""
        if max_age_hours is None:
            max_age_hours = self.default_expiry_hours

        # 内存缓存（加锁读取）
        with self._lock:
            if cache_key in self.memory_cache:
                expiry = self.cache_expiry.get(cache_key)
                if expiry and datetime.now() < expiry:
                    logger.debug(f"内存缓存命中: {cache_key}")
                    return self.memory_cache[cache_key]

        # 数据库缓存
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT data_json, expires_at FROM data_cache "
                    "WHERE cache_key = ? AND (expires_at IS NULL OR expires_at > ?)",
                    (cache_key, datetime.now().isoformat())
                )
                row = cursor.fetchone()

            if row:
                data_json, expires_at = row
                data = json.loads(data_json)
                with self._lock:
                    self.memory_cache[cache_key] = data
                    if expires_at:
                        self.cache_expiry[cache_key] = datetime.fromisoformat(expires_at)
                logger.debug(f"数据库缓存命中: {cache_key}")
                return data
        except Exception as e:
            logger.error(f"读取缓存失败: {e}")

        return None

    def save_to_cache(self, cache_key: str, data_type: str, symbol: str,
                      data: list, start_date: str = None, end_date: str = None,
                      expiry_hours: int = None):
        """保存数据到缓存"""
        if expiry_hours is None:
            expiry_hours = self.default_expiry_hours

        expiry = datetime.now() + timedelta(hours=expiry_hours)
        with self._lock:
            self.memory_cache[cache_key] = data
            self.cache_expiry[cache_key] = expiry

        try:
            data_json = json.dumps(data, default=str)
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO data_cache "
                    "(cache_key, data_type, symbol, start_date, end_date, data_json, expires_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (cache_key, data_type, symbol, start_date, end_date,
                     data_json, expiry.isoformat())
                )
                conn.commit()
            logger.debug(f"数据已缓存: {cache_key}")
        except Exception as e:
            logger.error(f"缓存保存失败: {e}")

    def clear_cache(self, data_type: str = None, symbol: str = None):
        """清除缓存"""
        if data_type is None and symbol is None:
            with self._lock:
                self.memory_cache.clear()
                self.cache_expiry.clear()
            try:
                with self._get_conn() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM data_cache")
                    conn.commit()
            except Exception as e:
                logger.error(f"清除数据库缓存失败: {e}")
            logger.info("所有缓存已清除")
        else:
            with self._lock:
                keys_to_delete = [
                    k for k in self.memory_cache
                    if (data_type is None or data_type in k)
                    and (symbol is None or symbol in k)
                ]
                for k in keys_to_delete:
                    del self.memory_cache[k]
                    self.cache_expiry.pop(k, None)

            try:
                with self._get_conn() as conn:
                    cursor = conn.cursor()
                    if data_type and symbol:
                        cursor.execute(
                            "DELETE FROM data_cache WHERE data_type = ? AND symbol = ?",
                            (data_type, symbol)
                        )
                    elif data_type:
                        cursor.execute(
                            "DELETE FROM data_cache WHERE data_type = ?", (data_type,)
                        )
                    elif symbol:
                        cursor.execute(
                            "DELETE FROM data_cache WHERE symbol = ?", (symbol,)
                        )
                    conn.commit()
            except Exception as e:
                logger.error(f"清除数据库缓存失败: {e}")

    def update_expiry(self, expiry_hours: int):
        """更新默认缓存过期时间"""
        self.default_expiry_hours = expiry_hours
        logger.info(f"缓存过期时间已更新为 {expiry_hours} 小时")

    def get_stats(self) -> dict:
        """获取缓存统计信息"""
        with self._lock:
            memory_count = len(self.memory_cache)
        stats = {
            "memory_count": memory_count,
            "db_count": 0,
            "total_size_mb": 0,
            "oldest_cache": "N/A",
            "newest_cache": "N/A",
        }
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM data_cache")
                stats["db_count"] = cursor.fetchone()[0]
                cursor.execute("SELECT SUM(LENGTH(data_json)) FROM data_cache")
                total_bytes = cursor.fetchone()[0] or 0
                stats["total_size_mb"] = total_bytes / (1024 * 1024)
                cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM data_cache")
                time_range = cursor.fetchone()
                if time_range and time_range[0]:
                    stats["oldest_cache"] = time_range[0][:10]
                    stats["newest_cache"] = time_range[1][:10]
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
        return stats
