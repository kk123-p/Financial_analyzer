"""Adapter Tushare 扩展接口测试"""
import pytest
import pandas as pd
from unittest.mock import MagicMock

from financial_analyzer.data_sources.adapter import DataSourceAdapter


class TestTushareNewHandlers:
    """测试新增的 Tushare handler 路由"""

    @pytest.fixture
    def adapter(self):
        a = DataSourceAdapter()
        a.tushare_pro = MagicMock()
        return a

    def test_moneyflow_handler_called(self, adapter):
        adapter.tushare_pro.moneyflow = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20250101", "20250110", "moneyflow")
        adapter.tushare_pro.moneyflow.assert_called_once_with(
            ts_code="000001.SZ", start_date="20250101", end_date="20250110"
        )

    def test_margin_handler_called(self, adapter):
        adapter.tushare_pro.margin = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20250101", "20250110", "margin")
        adapter.tushare_pro.margin.assert_called_once()

    def test_dividend_handler_called(self, adapter):
        adapter.tushare_pro.dividend = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20200101", "20251231", "dividend")
        adapter.tushare_pro.dividend.assert_called_once()

    def test_top10_holders_handler_called(self, adapter):
        adapter.tushare_pro.top10_holders = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20240101", "20241231", "top10_holders")
        adapter.tushare_pro.top10_holders.assert_called_once()

    def test_fina_audit_handler_called(self, adapter):
        adapter.tushare_pro.fina_audit = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20150101", "20251231", "fina_audit")
        adapter.tushare_pro.fina_audit.assert_called_once()

    def test_fina_mainbz_handler_called(self, adapter):
        adapter.tushare_pro.fina_mainbz = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20240101", "20241231", "fina_mainbz")
        adapter.tushare_pro.fina_mainbz.assert_called_once_with(
            ts_code="000001.SZ", start_date="20240101", end_date="20241231", type='P'
        )

    def test_weekly_handler_called(self, adapter):
        adapter.tushare_pro.weekly = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20240101", "20250101", "weekly")
        adapter.tushare_pro.weekly.assert_called_once()

    def test_hk_hold_handler_called(self, adapter):
        adapter.tushare_pro.hk_hold = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20240101", "20250101", "hk_hold")
        adapter.tushare_pro.hk_hold.assert_called_once()

    def test_stk_holdernumber_handler_called(self, adapter):
        adapter.tushare_pro.stk_holdernumber = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20240101", "20241231", "stk_holdernumber")
        adapter.tushare_pro.stk_holdernumber.assert_called_once()

    def test_block_trade_handler_called(self, adapter):
        adapter.tushare_pro.block_trade = MagicMock(return_value=pd.DataFrame())
        adapter._get_tushare("000001.SZ", "20240101", "20250101", "block_trade")
        adapter.tushare_pro.block_trade.assert_called_once()

    def test_unknown_type_returns_none(self, adapter):
        result = adapter._get_tushare("000001.SZ", "20240101", "20240105", "nonexistent")
        assert result is None
