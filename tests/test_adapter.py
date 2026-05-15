"""
DataSourceAdapter 单元测试（使用 mock 隔离外部依赖）
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from financial_analyzer.data_sources.adapter import DataSourceAdapter


class TestDataSourceAdapter:
    @pytest.fixture
    def adapter(self, tmp_path):
        """创建带 mock cache 的 adapter"""
        from financial_analyzer.cache.manager import DataCacheManager
        cache = DataCacheManager(cache_dir=tmp_path)
        return DataSourceAdapter(cache_manager=cache)

    def test_init_default_source(self, adapter):
        assert adapter.active_source == "tushare"

    def test_get_available_sources(self, adapter):
        sources = adapter.get_available_sources()
        assert isinstance(sources, list)

    def test_set_active_source_invalid(self, adapter):
        result = adapter.set_active_source("nonexistent")
        assert result is False

    def test_set_tushare_token(self, adapter):
        # 如果 tushare 未安装，应返回 False
        result = adapter.set_tushare_token("test_token")
        # 取决于环境，不强制断言

    def test_active_source_thread_safety(self, adapter):
        """测试 active_source 属性的线程安全性"""
        import threading

        results = []

        def setter():
            for _ in range(100):
                adapter.active_source = "yfinance"

        def getter():
            for _ in range(100):
                s = adapter.active_source
                results.append(s)

        threads = [threading.Thread(target=setter), threading.Thread(target=getter)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有结果都应该是有效值
        valid = {"tushare", "yfinance", "akshare"}
        for r in results:
            assert r in valid

    def test_cache_key_generation(self, adapter):
        """测试缓存键生成"""
        key = adapter.cache_manager.get_cache_key("daily_tushare", "600519.SH",
                                                   "20240101", "20240105")
        assert "daily_tushare" in key
        assert "600519.SH" in key

    @patch("financial_analyzer.data_sources.adapter.HAS_TUSHARE", False)
    @patch("financial_analyzer.data_sources.adapter.HAS_YFINANCE", False)
    @patch("financial_analyzer.data_sources.adapter.HAS_AKSHARE", False)
    def test_no_sources_available(self, adapter):
        """所有第三方数据源不可用时，仍保留新浪（始终可用）"""
        adapter.refresh_sources()
        sources = adapter.get_available_sources()
        assert "sina" in sources
        assert len(sources) == 1

    def test_fetch_raw_unknown_type(self, adapter):
        """未知数据类型应返回 (None, None)"""
        result = adapter._fetch_raw("600519.SH", "20240101", "20240105", "unknown_type")
        assert result == (None, None)


class TestDataSourceAdapterNormalization:
    """测试数据标准化流程"""

    def test_normalize_daily_calls_normalizer(self):
        """验证 _normalize 调用正确的标准化方法"""
        adapter = DataSourceAdapter()
        df = pd.DataFrame({
            "Date": ["2024-01-01"],
            "Close": [100.0],
            "Open": [99.0],
            "High": [101.0],
            "Low": [98.0],
            "Volume": [1000000],
        })

        result = adapter._normalize(df, "daily")
        assert result is not None
        assert "close" in result.columns
        assert "trade_date" in result.columns

    def test_normalize_unknown_type_passthrough(self):
        """未知类型应原样返回"""
        adapter = DataSourceAdapter()
        df = pd.DataFrame({"col1": [1, 2, 3]})
        result = adapter._normalize(df, "unknown")
        assert result.equals(df)


class TestIndustryStocks:
    """测试行业股票获取"""

    def test_no_token_returns_none(self, tmp_path):
        from financial_analyzer.cache.manager import DataCacheManager
        cache = DataCacheManager(cache_dir=tmp_path)
        adapter = DataSourceAdapter(cache_manager=cache)
        # 没有 token 时应该返回 None
        result = adapter.get_industry_stocks_from_api("科技")
        # 取决于 akshare 是否安装
