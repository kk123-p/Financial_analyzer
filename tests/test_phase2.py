"""Phase 2 Calculator 单元测试"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from financial_analyzer.calculator.phase2_analysis import Phase2Calculator as P2


class TestPeerComparison:
    def test_basic_comparison(self):
        company = {"roe": 25, "gross_margin": 50, "pe": 30}
        peers = [
            {"roe": 15, "gross_margin": 40, "pe": 20},
            {"roe": 20, "gross_margin": 45, "pe": 25},
            {"roe": 10, "gross_margin": 30, "pe": 15},
        ]
        r = P2.compare_with_peers(company, peers)
        assert r["rankings"]["roe"]["rank"] == 1
        assert r["rankings"]["pe"]["rank"] == 4  # PE 越低越好，30是最高的

    def test_empty_peers(self):
        r = P2.compare_with_peers({"roe": 20}, [])
        assert r["rankings"] == {}


class TestPEPercentile:
    def test_low_percentile(self):
        r = P2.pe_percentile([10, 15, 20, 25, 30], 12)
        assert r["percentile"] == pytest.approx(20.0)  # only 10 <= 12

    def test_high_percentile(self):
        r = P2.pe_percentile([10, 15, 20, 25, 30], 28)
        assert r["percentile"] == pytest.approx(80.0)

    def test_empty(self):
        r = P2.pe_percentile([], 20)
        assert r["percentile"] is None

    def test_none_current(self):
        r = P2.pe_percentile([10, 20], None)
        assert r["percentile"] is None


class TestPBRoeModel:
    def test_basic(self):
        r = P2.pb_roe_model(20, 10)
        assert r["fair_pb"] == pytest.approx(2.0)

    def test_high_roe(self):
        r = P2.pb_roe_model(30, 10)
        assert r["fair_pb"] == pytest.approx(3.0)

    def test_negative_roe(self):
        r = P2.pb_roe_model(-5, 10)
        assert r["fair_pb"] is None


class TestEVEBITDA:
    def test_basic(self):
        r = P2.ev_ebitda(ebitda=1000, market_cap=5000, total_liab=2000, cash=500)
        assert r["ev"] == 6500
        assert r["ev_ebitda"] == pytest.approx(6.5)

    def test_no_ebitda(self):
        r = P2.ev_ebitda(ebitda=0, market_cap=5000, total_liab=2000, cash=500)
        assert r["ev_ebitda"] is None


class TestShareholderReturns:
    def test_basic(self):
        r = P2.shareholder_returns(
            dividends=[100, 80, 60],
            net_profits=[500, 400, 300],
            current_price=100, shares=1000
        )
        assert r["avg_payout_ratio"] is not None
        assert r["dividend_yield"] is not None

    def test_empty(self):
        r = P2.shareholder_returns([], [], 100, 1000)
        assert r["avg_payout_ratio"] is None


class TestFinancialQuality:
    def test_good_quality(self):
        periods = []
        for i in range(3):
            periods.append({
                "revenue": 1000, "accounts_receivable": 50 - i * 5,
                "inventories": 100 - i * 5, "op_cost": 600,
                "op_cashflow": 300 + i * 10, "net_profit": 200,
                "total_assets": 3000, "goodwill": 50,
            })
        r = P2.financial_quality(periods)
        assert r["quality_score"] > 50

    def test_poor_quality(self):
        periods = []
        for i in range(3):
            periods.append({
                "revenue": 1000, "accounts_receivable": 300 + i * 50,
                "inventories": 400 + i * 50, "op_cost": 800,
                "op_cashflow": 20, "net_profit": 200,
                "total_assets": 3000, "goodwill": 1200,
            })
        r = P2.financial_quality(periods)
        assert r["quality_score"] < 60

    def test_insufficient_data(self):
        r = P2.financial_quality([{"end_date": "20241231"}])
        assert r["quality_level"] == "数据不足"
