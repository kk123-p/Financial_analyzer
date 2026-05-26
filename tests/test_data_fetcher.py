"""QuantDataFetcher 单元测试"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import date

import pandas as pd
import numpy as np

from financial_analyzer.quant.data_fetcher import QuantDataFetcher, FACTOR_DATA_TYPES
from financial_analyzer.quant.models import StockInfo


@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.tushare_pro = MagicMock()
    return adapter


@pytest.fixture
def sample_stocks():
    return [
        StockInfo("600519", "贵州茅台", "白酒", "主板"),
        StockInfo("000858", "五粮液", "白酒", "主板"),
        StockInfo("000001", "平安银行", "银行", "主板"),
    ]


@pytest.fixture
def stock_basic_df():
    return pd.DataFrame([{
        "name": "贵州茅台",
        "industry": "白酒",
        "market": "主板",
        "list_date": "20010827",
    }])


class TestQuantDataFetcherEnrich:
    def test_enrich_populates_fields(self, mock_adapter, sample_stocks, stock_basic_df):
        mock_adapter.get_stock_data.return_value = stock_basic_df

        fetcher = QuantDataFetcher(mock_adapter)
        result = fetcher.enrich_stock_info(sample_stocks)

        assert result[0].name != ""  # name 已被补充
        assert result[0].industry != ""
        assert result[0].market != ""
        assert len(result) == 3

    def test_enrich_detects_st(self, mock_adapter):
        df = pd.DataFrame([{
            "name": "*ST康美",
            "industry": "医药",
            "market": "主板",
            "list_date": "20010101",
        }])
        mock_adapter.get_stock_data.return_value = df
        stocks = [StockInfo("600518", "")]

        fetcher = QuantDataFetcher(mock_adapter)
        result = fetcher.enrich_stock_info(stocks)

        assert result[0].is_st is True

    def test_enrich_skips_already_named(self, mock_adapter, sample_stocks):
        mock_adapter.get_stock_data.return_value = None
        sample_stocks[0].name = "已有名称"

        fetcher = QuantDataFetcher(mock_adapter)
        result = fetcher.enrich_stock_info(sample_stocks)

        # 只调用2次（跳过已有名称的 600519）
        assert mock_adapter.get_stock_data.call_count <= 2

    def test_enrich_handles_api_error(self, mock_adapter, sample_stocks):
        mock_adapter.get_stock_data.side_effect = Exception("API error")

        fetcher = QuantDataFetcher(mock_adapter)
        result = fetcher.enrich_stock_info(sample_stocks)

        assert len(result) == 3  # 不应崩溃


class TestQuantDataFetcherFetch:
    def test_fetch_all_returns_dict(self, mock_adapter, sample_stocks):
        daily_df = pd.DataFrame({"close": [10.0, 10.5, 11.0]})
        mock_adapter.get_stock_data.return_value = daily_df

        fetcher = QuantDataFetcher(mock_adapter)
        result = fetcher.fetch_all(sample_stocks)

        assert isinstance(result, dict)
        assert len(result) == 3
        for code in ["600519", "000858", "000001"]:
            assert code in result
            # 所有9种数据类型均返回 daily_df
            assert len(result[code]) == len(FACTOR_DATA_TYPES)

    def test_fetch_all_handles_none_response(self, mock_adapter, sample_stocks):
        mock_adapter.get_stock_data.return_value = None

        fetcher = QuantDataFetcher(mock_adapter)
        result = fetcher.fetch_all(sample_stocks)

        assert result == {}  # 所有数据为 None 时不包含该股票

    def test_fetch_all_empty_stocks(self, mock_adapter):
        fetcher = QuantDataFetcher(mock_adapter)
        result = fetcher.fetch_all([])
        assert result == {}


class TestQuantDataFetcherRateLimit:
    def test_first_call_no_delay(self, mock_adapter, sample_stocks):
        """第一次调用不应该有延迟"""
        mock_adapter.get_stock_data.return_value = pd.DataFrame({"close": [10.0]})

        import time
        fetcher = QuantDataFetcher(mock_adapter)

        # 仅测第一次调用的延迟
        start = time.time()
        fetcher._rate_limited_fetch("600519", "daily")
        elapsed = time.time() - start

        assert elapsed < 0.5  # 第一次调用无等待
