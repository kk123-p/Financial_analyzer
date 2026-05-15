"""
DataNormalizer 单元测试
"""
import pytest
import pandas as pd
import numpy as np

from financial_analyzer.data_sources.normalizer import DataNormalizer, StandardColumns


# ============================================================================
# normalize_daily - Tushare
# ============================================================================
class TestNormalizeDailyTushare:
    @pytest.fixture
    def tushare_df(self):
        return pd.DataFrame({
            "trade_date": ["20250103", "20250102", "20250101"],
            "open": [100.0, 99.0, 98.0],
            "high": [102.0, 101.0, 100.0],
            "low": [99.0, 98.0, 97.0],
            "close": [101.0, 100.0, 99.0],
            "vol": [50000, 45000, 40000],
            "amount": [5050000, 4500000, 3960000],
        })

    def test_columns_preserved(self, tushare_df):
        result = DataNormalizer.normalize_daily(tushare_df, "tushare")
        for col in StandardColumns.DAILY_REQUIRED:
            assert col in result.columns

    def test_date_format(self, tushare_df):
        result = DataNormalizer.normalize_daily(tushare_df, "tushare")
        # pandas 2.x 可能用 StringDtype 或 object
        assert pd.api.types.is_string_dtype(result["trade_date"])
        for d in result["trade_date"]:
            assert len(d) == 8
            assert d.isdigit()

    def test_descending_order(self, tushare_df):
        result = DataNormalizer.normalize_daily(tushare_df, "tushare")
        dates = result["trade_date"].tolist()
        assert dates == sorted(dates, reverse=True)

    def test_numeric_types(self, tushare_df):
        result = DataNormalizer.normalize_daily(tushare_df, "tushare")
        for col in ["open", "high", "low", "close", "vol"]:
            assert pd.api.types.is_numeric_dtype(result[col])


# ============================================================================
# normalize_daily - Yahoo Finance
# ============================================================================
class TestNormalizeDailyYahoo:
    @pytest.fixture
    def yahoo_df(self):
        dates = pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-03"])
        return pd.DataFrame({
            "Date": dates,
            "Open": [100.0, 101.0, 102.0],
            "High": [103.0, 104.0, 105.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [102.0, 103.0, 104.0],
            "Volume": [5000000, 6000000, 7000000],
            "Dividends": [0, 0, 0],
            "Stock Splits": [0, 0, 0],
        })

    def test_column_rename(self, yahoo_df):
        result = DataNormalizer.normalize_daily(yahoo_df, "yfinance")
        assert "close" in result.columns
        assert "open" in result.columns
        assert "vol" in result.columns
        assert "Close" not in result.columns
        assert "Volume" not in result.columns

    def test_drop_columns(self, yahoo_df):
        result = DataNormalizer.normalize_daily(yahoo_df, "yfinance")
        assert "Dividends" not in result.columns
        assert "Stock Splits" not in result.columns
        assert "Date" not in result.columns

    def test_volume_conversion(self, yahoo_df):
        """Yahoo Finance 成交量应从股数转换为手"""
        result = DataNormalizer.normalize_daily(yahoo_df, "yfinance")
        # 结果按日期降序排列，最后一行对应原始第一行
        # 原始 Volume: [5000000, 6000000, 7000000] → 转换后: [50000, 60000, 70000]
        assert result["vol"].iloc[-1] == pytest.approx(5000000 / 100)
        assert result["vol"].iloc[0] == pytest.approx(7000000 / 100)

    def test_volume_small_values_also_converted(self):
        """即使成交量数值很小，yfinance 也应转换（因为始终是股数）"""
        df = pd.DataFrame({
            "Date": pd.to_datetime(["2025-01-01"]),
            "Open": [100.0], "High": [101.0], "Low": [99.0], "Close": [100.5],
            "Volume": [500],
            "Dividends": [0], "Stock Splits": [0],
        })
        result = DataNormalizer.normalize_daily(df, "yfinance")
        assert result["vol"].iloc[0] == pytest.approx(5.0)


# ============================================================================
# normalize_daily - Akshare
# ============================================================================
class TestNormalizeDailyAkshare:
    @pytest.fixture
    def akshare_df(self):
        return pd.DataFrame({
            "日期": ["2025-01-01", "2025-01-02"],
            "开盘": [100.0, 101.0],
            "收盘": [102.0, 103.0],
            "最高": [104.0, 105.0],
            "最低": [99.0, 100.0],
            "成交量": [50000, 60000],
            "成交额": [5100000, 6180000],
            "振幅": [5.0, 5.0],
            "涨跌幅": [2.0, 0.98],
            "涨跌额": [2.0, 1.0],
            "换手率": [3.0, 3.5],
        })

    def test_column_rename(self, akshare_df):
        result = DataNormalizer.normalize_daily(akshare_df, "akshare")
        assert "close" in result.columns
        assert "open" in result.columns
        assert "vol" in result.columns
        assert "收盘" not in result.columns

    def test_drop_columns(self, akshare_df):
        result = DataNormalizer.normalize_daily(akshare_df, "akshare")
        assert "振幅" not in result.columns
        assert "涨跌额" not in result.columns


# ============================================================================
# normalize_daily - 边界情况
# ============================================================================
class TestNormalizeDailyEdgeCases:
    def test_none_df(self):
        result = DataNormalizer.normalize_daily(None, "tushare")
        assert result is None

    def test_empty_df(self):
        result = DataNormalizer.normalize_daily(pd.DataFrame(), "tushare")
        assert result.empty

    def test_unknown_source(self):
        df = pd.DataFrame({"close": [100], "open": [99], "high": [101], "low": [98], "vol": [1000]})
        result = DataNormalizer.normalize_daily(df, "unknown_source")
        # 应该不做映射，但保留数据
        assert len(result) == 1

    def test_all_standard_columns_present(self):
        """标准化后应包含所有标准列"""
        df = pd.DataFrame({
            "trade_date": ["20250101"],
            "open": [100], "high": [101], "low": [99], "close": [100.5],
            "vol": [50000], "amount": [5000000],
            "turnover_rate": [2.5], "pct_chg": [0.5],
        })
        result = DataNormalizer.normalize_daily(df, "tushare")
        for col in StandardColumns.DAILY_REQUIRED + StandardColumns.DAILY_OPTIONAL:
            assert col in result.columns


# ============================================================================
# normalize_basic
# ============================================================================
class TestNormalizeBasic:
    def test_yahoo_basic(self):
        df = pd.DataFrame([{
            "longName": "Apple Inc.",
            "industry": "Consumer Electronics",
            "trailingPE": 25.0,
            "priceToBook": 30.0,
            "marketCap": 3000000000000,
        }])
        result = DataNormalizer.normalize_basic(df, "yfinance")
        assert "name" in result.columns
        assert result.iloc[0]["name"] == "Apple Inc."
        assert "pe" in result.columns

    def test_akshare_basic(self):
        df = pd.DataFrame({
            "item": ["股票代码", "股票简称", "行业", "总市值", "流通市值"],
            "value": ["000001", "平安银行", "银行", "3000000000", "2500000000"],
        })
        result = DataNormalizer.normalize_basic(df, "akshare")
        assert "ts_code" in result.columns
        assert result.iloc[0]["ts_code"] == "000001"
        assert result.iloc[0]["name"] == "平安银行"

    def test_none(self):
        assert DataNormalizer.normalize_basic(None, "tushare") is None

    def test_empty(self):
        result = DataNormalizer.normalize_basic(pd.DataFrame(), "tushare")
        assert result.empty


# ============================================================================
# normalize_financial
# ============================================================================
class TestNormalizeFinancial:
    def test_yahoo_financial_rename(self):
        df = pd.DataFrame([{
            "Total Revenue": 100000,
            "Net Income": 20000,
            "Gross Profit": 40000,
            "Operating Income": 30000,
        }])
        result = DataNormalizer.normalize_financial(df, "yfinance")
        assert "total_revenue" in result.columns
        assert "net_profit" in result.columns
        assert "gross_profit" in result.columns
        assert "operate_profit" in result.columns

    def test_none(self):
        assert DataNormalizer.normalize_financial(None, "tushare") is None


# ============================================================================
# normalize_income / normalize_balance / normalize_cashflow - Akshare
# ============================================================================
class TestAkshareIncome:
    def test_column_rename(self):
        df = pd.DataFrame({
            "报告日": ["20241231", "20231231"],
            "营业总收入": [100e8, 90e8],
            "营业成本": [40e8, 35e8],
            "销售费用": [10e8, 9e8],
            "管理费用": [8e8, 7e8],
            "财务费用": [1e8, 1e8],
            "研发费用": [5e8, 4e8],
            "营业利润": [50e8, 45e8],
            "净利润": [40e8, 36e8],
            "归属于母公司所有者的净利润": [38e8, 34e8],
        })
        result = DataNormalizer.normalize_income(df, "akshare")
        assert "end_date" in result.columns
        assert "total_revenue" in result.columns
        assert "oper_cost" in result.columns
        assert "sell_exp" in result.columns
        assert "net_profit" in result.columns
        assert "n_income_attr_p" in result.columns
        assert "报告日" not in result.columns

    def test_date_format(self):
        df = pd.DataFrame({"报告日": ["2024-12-31", "2023-12-31"], "营业总收入": [100, 90]})
        result = DataNormalizer.normalize_income(df, "akshare")
        assert result["end_date"].iloc[0] == "20241231"

    def test_descending_order(self):
        df = pd.DataFrame({"报告日": ["20221231", "20241231", "20231231"], "营业总收入": [80, 100, 90]})
        result = DataNormalizer.normalize_income(df, "akshare")
        assert result["end_date"].iloc[0] == "20241231"

    def test_none_input(self):
        assert DataNormalizer.normalize_income(None, "akshare") is None


class TestAkshareBalance:
    def test_column_rename(self):
        df = pd.DataFrame({
            "报告日": ["20241231"],
            "流动资产合计": [500e8],
            "资产合计": [1000e8],
            "流动负债合计": [300e8],
            "负债合计": [400e8],
            "货币资金": [200e8],
            "存货": [100e8],
        })
        result = DataNormalizer.normalize_balance(df, "akshare")
        assert "total_cur_assets" in result.columns
        assert "total_assets" in result.columns
        assert "total_cur_liab" in result.columns
        assert "total_liab" in result.columns
        assert "money_cap" in result.columns
        assert "inventories" in result.columns

    def test_none_input(self):
        assert DataNormalizer.normalize_balance(None, "akshare") is None


class TestAkshareCashflow:
    def test_column_rename(self):
        df = pd.DataFrame({
            "报告日": ["20241231"],
            "经营活动产生的现金流量净额": [50e8],
            "投资活动产生的现金流量净额": [-20e8],
            "筹资活动产生的现金流量净额": [-10e8],
            "购建固定资产、无形资产和其他长期资产支付的现金": [15e8],
        })
        result = DataNormalizer.normalize_cashflow(df, "akshare")
        assert "n_cashflow_act" in result.columns
        assert "n_cashflow_inv_act" in result.columns
        assert "n_cash_finance_act" in result.columns
        assert "c_pay_acq_const_fiamt" in result.columns

    def test_numeric_conversion(self):
        df = pd.DataFrame({
            "报告日": ["20241231"],
            "经营活动产生的现金流量净额": ["5000000000"],  # 字符串
        })
        result = DataNormalizer.normalize_cashflow(df, "akshare")
        assert pd.api.types.is_numeric_dtype(result["n_cashflow_act"])

    def test_none_input(self):
        assert DataNormalizer.normalize_cashflow(None, "akshare") is None
