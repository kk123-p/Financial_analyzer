"""
BaseAnalyzer 单元测试
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock

from financial_analyzer.analyzers.base import BaseAnalyzer


class TestBaseAnalyzer:
    @pytest.fixture
    def mock_adapter(self):
        adapter = MagicMock()
        adapter.active_source = "tushare"
        adapter.get_stock_data.return_value = pd.DataFrame({
            "trade_date": ["20250101"], "close": [100.0]
        })
        return adapter

    @pytest.fixture
    def analyzer(self, mock_adapter):
        return BaseAnalyzer(
            data={"daily": pd.DataFrame()},
            stock_code="600519.SH",
            data_adapter=mock_adapter,
        )

    def test_init(self, analyzer):
        assert analyzer.stock_code == "600519.SH"
        assert analyzer.data_adapter is not None

    def test_fetch_data_returns_tuple(self, analyzer):
        result = analyzer._fetch_data("daily")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_fetch_data_success(self, analyzer):
        df, error = analyzer._fetch_data("daily")
        assert df is not None
        assert error is None
        assert len(df) == 1

    def test_fetch_data_no_stock_code(self, mock_adapter):
        analyzer = BaseAnalyzer({}, "", mock_adapter)
        df, error = analyzer._fetch_data("daily")
        assert df is None
        assert "未设置" in error

    def test_fetch_data_no_adapter(self):
        analyzer = BaseAnalyzer({}, "600519.SH", None)
        df, error = analyzer._fetch_data("daily")
        assert df is None
        assert "未配置" in error

    def test_fetch_data_calls_adapter(self, analyzer, mock_adapter):
        analyzer._fetch_data("daily")
        mock_adapter.get_stock_data.assert_called_once()

    def test_fetch_data_adapter_returns_none(self, mock_adapter):
        mock_adapter.get_stock_data.return_value = None
        analyzer = BaseAnalyzer({}, "600519.SH", mock_adapter)
        df, error = analyzer._fetch_data("daily")
        assert df is None
        assert error is not None
        assert "未获取" in error

    def test_fetch_data_adapter_returns_empty(self, mock_adapter):
        mock_adapter.get_stock_data.return_value = pd.DataFrame()
        analyzer = BaseAnalyzer({}, "600519.SH", mock_adapter)
        df, error = analyzer._fetch_data("daily")
        assert df is None

    def test_fetch_data_exception(self, mock_adapter):
        mock_adapter.get_stock_data.side_effect = Exception("网络错误")
        analyzer = BaseAnalyzer({}, "600519.SH", mock_adapter)
        df, error = analyzer._fetch_data("daily")
        assert df is None
        assert "网络错误" in error

    def test_fetch_data_financial_success(self, analyzer):
        df, error = analyzer._fetch_data("financial")
        assert df is not None
        assert error is None

    def test_fetch_data_financial_failure(self, mock_adapter):
        mock_adapter.get_stock_data.return_value = None
        analyzer = BaseAnalyzer({}, "600519.SH", mock_adapter)
        df, error = analyzer._fetch_data("income")
        assert df is None
        assert error is not None

    def test_default_years(self, analyzer):
        assert BaseAnalyzer.DEFAULT_YEARS == 5

    def test_custom_years(self, analyzer, mock_adapter):
        analyzer._fetch_data("daily", years=1)
        call_args = mock_adapter.get_stock_data.call_args
        # 验证 start_date 大约是 1 年前
        start_date = call_args[0][1]
        assert start_date is not None
