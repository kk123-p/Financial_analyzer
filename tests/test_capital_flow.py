"""CapitalFlowAnalyzer 测试"""
import pandas as pd
import pytest
from financial_analyzer.analyzers.capital_flow import CapitalFlowAnalyzer


class TestCapitalFlowAnalyzer:
    @pytest.fixture
    def stock_basic(self):
        return pd.DataFrame([{"name": "测试股票", "industry": "科技"}])

    @pytest.fixture
    def moneyflow_data(self):
        rows = []
        for i in range(1, 26):
            rows.append({
                "trade_date": f"202501{i:02d}",
                "buy_elg_amount": 1e7, "sell_elg_amount": 8e6,
                "buy_lg_amount": 5e6, "sell_lg_amount": 6e6,
                "buy_md_amount": 3e6, "sell_md_amount": 2e6,
                "buy_sm_amount": 1e6, "sell_sm_amount": 2e6,
            })
        return pd.DataFrame(rows)

    @pytest.fixture
    def margin_data(self):
        rows = []
        for i in range(1, 21):
            rows.append({
                "trade_date": f"202501{i:02d}",
                "rzye": 5e9 + i * 1e8,
                "rqye": 5e8,
            })
        return pd.DataFrame(rows)

    def test_analyze_with_data(self, stock_basic, moneyflow_data, margin_data):
        data = {
            "stock_basic": stock_basic,
            "moneyflow": moneyflow_data,
            "margin": margin_data,
        }
        analyzer = CapitalFlowAnalyzer(data, "000001.SZ")
        result = analyzer.analyze()
        assert "资金面分析" in result
        assert "测试股票" in result
        assert "主力资金流向" in result
        assert "融资融券" in result
        assert "资金面综合评分" in result

    def test_analyze_no_data(self):
        analyzer = CapitalFlowAnalyzer({}, "000001.SZ")
        result = analyzer.analyze()
        assert "资金面分析" in result
        assert "未获取到" in result
