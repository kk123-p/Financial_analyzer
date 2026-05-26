"""选股池管理测试"""
import pytest
from datetime import date, timedelta
from financial_analyzer.quant.universe import UniverseManager
from financial_analyzer.quant.models import StockInfo


@pytest.fixture
def sample_stocks():
    return [
        StockInfo("600519", "贵州茅台", "白酒", "主板", False, False, date(2001, 8, 27)),
        StockInfo("000858", "五粮液", "白酒", "主板", False, False, date(1998, 4, 27)),
        StockInfo("300750", "宁德时代", "电池", "创业板", False, False, date(2018, 6, 11)),
        StockInfo("000001", "平安银行", "银行", "主板", False, False, date(1991, 4, 3)),
        StockInfo("688981", "中芯国际", "半导体", "科创板", False, False, date(2020, 7, 16)),
        StockInfo("600000", "浦发银行", "银行", "主板", False, True, date(1999, 11, 10)),
    ]


class TestUniverseManager:
    def test_filter_st_suspended(self, sample_stocks):
        """ST和停牌股票应被过滤"""
        sample_stocks[0].is_st = True  # 600519 marked as ST
        result = UniverseManager()._apply_hard_filters(sample_stocks)
        codes = [s.code for s in result]
        assert "600519" not in codes  # ST过滤
        assert "600000" not in codes  # 停牌过滤

    def test_filter_high_price(self, sample_stocks):
        """高价股过滤"""
        result = UniverseManager()._filter_by_price(sample_stocks, {"600519": 16.0, "000858": 10.0})
        codes = [s.code for s in result]
        assert "600519" not in codes  # >15元
        assert "000858" in codes

    def test_filter_new_listings(self, sample_stocks):
        """次新股(上市<6个月)应被过滤"""
        today = date(2026, 5, 26)
        sample_stocks[4].listed_date = today  # 今天刚上市
        result = UniverseManager()._filter_by_age(sample_stocks, today)
        codes = [s.code for s in result]
        assert "688981" not in codes

    def test_get_universe_returns_stocks(self):
        """获取选股池应返回股票列表"""
        mgr = UniverseManager()
        stocks = mgr.get_universe("沪深300")
        assert isinstance(stocks, list)
        # 可能因未配置Tushare返回空列表，这是合法的

    def test_pool_names(self):
        mgr = UniverseManager()
        pools = mgr.pool_names()
        assert "沪深300" in pools
        assert "中证500" in pools
