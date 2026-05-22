"""ShareholderAnalyzer 测试"""
import pandas as pd
import pytest
from financial_analyzer.analyzers.shareholder import ShareholderAnalyzer


class TestShareholderAnalyzer:
    @pytest.fixture
    def stock_basic(self):
        return pd.DataFrame([{
            "name": "测试银行", "industry": "银行", "market": "主板"
        }])

    @pytest.fixture
    def holder_data(self):
        return pd.DataFrame([
            {"ann_date": "20221231", "holder_num": 500000},
            {"ann_date": "20230630", "holder_num": 460000},
            {"ann_date": "20231231", "holder_num": 410000},
            {"ann_date": "20240630", "holder_num": 350000},
        ])

    @pytest.fixture
    def top10_data(self):
        return pd.DataFrame([
            {"end_date": "20240630", "holder_name": "测试集团", "hold_amount": 5e9, "hold_ratio": 30.0},
            {"end_date": "20240630", "holder_name": "社保基金组合", "hold_amount": 2e9, "hold_ratio": 12.0},
            {"end_date": "20240630", "holder_name": "香港中央结算", "hold_amount": 1.5e9, "hold_ratio": 9.0},
        ])

    def test_analyze_with_all_data(self, stock_basic, holder_data, top10_data):
        data = {
            "stock_basic": stock_basic,
            "stk_holdernumber": holder_data,
            "top10_holders": top10_data,
        }
        analyzer = ShareholderAnalyzer(data, "000001.SZ")
        result = analyzer.analyze()
        assert "股东结构分析" in result
        assert "测试银行" in result
        assert "股东人数变化趋势" in result
        assert "前十大股东" in result
        assert "股权结构综合评分" in result

    def test_analyze_no_data(self):
        analyzer = ShareholderAnalyzer({}, "000001.SZ")
        result = analyzer.analyze()
        assert "股东结构分析" in result
        assert "未获取到" in result

    def test_ownership_score_chip_concentration(self, stock_basic, holder_data):
        data = {"stock_basic": stock_basic, "stk_holdernumber": holder_data}
        analyzer = ShareholderAnalyzer(data, "000001.SZ")
        result = analyzer.analyze()
        # 股东人数从50万降到42万 -> 筹码集中
        assert "筹码集中" in result
