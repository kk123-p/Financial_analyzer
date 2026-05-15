"""
DataCacheManager 单元测试
"""
import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from financial_analyzer.cache.manager import DataCacheManager


class TestCacheManager:
    @pytest.fixture
    def cache(self, tmp_path):
        """使用临时目录创建缓存管理器"""
        return DataCacheManager(cache_dir=tmp_path)

    def test_init_creates_db(self, cache):
        assert cache.db_path.exists()

    def test_get_cache_key(self, cache):
        key = cache.get_cache_key("daily", "600519.SH", "20240101", "20240105")
        assert key == "daily_600519.SH_20240101_20240105"

    def test_get_cache_key_no_dates(self, cache):
        key = cache.get_cache_key("daily", "600519.SH")
        assert key == "daily_600519.SH"

    def test_save_and_get(self, cache):
        data = [{"trade_date": "20240101", "close": 100.0}]
        cache.save_to_cache("test_key", "daily", "600519.SH", data)
        result = cache.get_from_cache("test_key")
        assert result is not None
        assert len(result) == 1
        assert result[0]["close"] == 100.0

    def test_cache_miss(self, cache):
        result = cache.get_from_cache("nonexistent_key")
        assert result is None

    def test_memory_cache_hit(self, cache):
        data = [{"close": 100}]
        cache.save_to_cache("key1", "daily", "600519.SH", data)
        # 第一次从 DB 读，第二次从内存
        cache.get_from_cache("key1")
        result = cache.get_from_cache("key1")
        assert result is not None

    def test_cache_expiry(self, cache):
        data = [{"close": 100}]
        cache.save_to_cache("key1", "daily", "600519.SH", data, expiry_hours=0)
        # 立即过期
        import time
        time.sleep(0.01)
        result = cache.get_from_cache("key1", max_age_hours=0)
        assert result is None

    def test_clear_all_cache(self, cache):
        cache.save_to_cache("key1", "daily", "A", [{"a": 1}])
        cache.save_to_cache("key2", "income", "B", [{"b": 2}])
        cache.clear_cache()
        assert cache.get_from_cache("key1") is None
        assert cache.get_from_cache("key2") is None
        assert len(cache.memory_cache) == 0

    def test_clear_by_data_type(self, cache):
        cache.save_to_cache("daily_A", "daily", "A", [{"a": 1}])
        cache.save_to_cache("income_A", "income", "A", [{"b": 2}])
        cache.clear_cache(data_type="daily")
        assert cache.get_from_cache("daily_A") is None
        assert cache.get_from_cache("income_A") is not None

    def test_clear_by_symbol(self, cache):
        cache.save_to_cache("daily_A", "daily", "A", [{"a": 1}])
        cache.save_to_cache("daily_B", "daily", "B", [{"b": 2}])
        cache.clear_cache(symbol="A")
        assert cache.get_from_cache("daily_A") is None
        assert cache.get_from_cache("daily_B") is not None

    def test_update_expiry(self, cache):
        cache.update_expiry(48)
        assert cache.default_expiry_hours == 48

    def test_get_stats(self, cache):
        cache.save_to_cache("key1", "daily", "A", [{"a": 1}])
        stats = cache.get_stats()
        assert stats["memory_count"] == 1
        assert stats["db_count"] == 1
        assert stats["total_size_mb"] >= 0

    def test_stats_empty_cache(self, cache):
        stats = cache.get_stats()
        assert stats["memory_count"] == 0
        assert stats["db_count"] == 0

    def test_save_large_data(self, cache):
        """测试大量数据的缓存"""
        data = [{"i": i, "value": f"data_{i}"} for i in range(1000)]
        cache.save_to_cache("large_key", "daily", "TEST", data)
        result = cache.get_from_cache("large_key")
        assert result is not None
        assert len(result) == 1000

    def test_overwrite_cache(self, cache):
        """测试覆盖写入"""
        cache.save_to_cache("key1", "daily", "A", [{"v": 1}])
        cache.save_to_cache("key1", "daily", "A", [{"v": 2}])
        result = cache.get_from_cache("key1")
        assert result[0]["v"] == 2

    def test_thread_safety(self, cache):
        """测试多线程并发访问"""
        import threading

        errors = []

        def writer(n):
            try:
                for i in range(50):
                    cache.save_to_cache(f"key_{n}_{i}", "daily", f"S{n}",
                                        [{"val": i}])
            except Exception as e:
                errors.append(e)

        def reader(n):
            try:
                for i in range(50):
                    cache.get_from_cache(f"key_{n}_{i}")
            except Exception as e:
                errors.append(e)

        threads = []
        for n in range(4):
            threads.append(threading.Thread(target=writer, args=(n,)))
            threads.append(threading.Thread(target=reader, args=(n,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestCacheManagerEdgeCases:
    def test_custom_cache_dir(self, tmp_path):
        custom_dir = tmp_path / "custom_cache"
        cache = DataCacheManager(cache_dir=custom_dir)
        assert cache.cache_dir == custom_dir
        assert custom_dir.exists()

    def test_default_cache_dir(self):
        """默认缓存目录应存在"""
        cache = DataCacheManager()
        assert cache.cache_dir.exists()

    def test_save_with_custom_expiry(self, tmp_path):
        cache = DataCacheManager(cache_dir=tmp_path)
        data = [{"test": True}]
        cache.save_to_cache("key", "daily", "S", data, expiry_hours=1)
        result = cache.get_from_cache("key", max_age_hours=2)
        assert result is not None  # 1小时未过期
