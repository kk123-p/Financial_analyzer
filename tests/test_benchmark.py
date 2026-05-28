"""基准对比模块测试"""
import numpy as np
import pandas as pd
import pytest
from financial_analyzer.quant.backtest.benchmark import BenchmarkComparator


class TestComputeExcessReturns:
    def test_basic(self):
        comp = BenchmarkComparator("000300.SH")
        port = pd.Series([0.05, -0.02, 0.03, 0.01])
        bench = pd.Series([0.03, -0.01, 0.02, 0.005])
        excess = comp.compute_excess_returns(port, bench)
        assert len(excess) == 4
        assert abs(excess.iloc[0] - 0.02) < 1e-10
        assert abs(excess.iloc[1] - (-0.01)) < 1e-10

    def test_aligned_different_length(self):
        comp = BenchmarkComparator()
        idx1 = pd.Index([0, 1, 2])
        idx2 = pd.Index([1, 2, 3])
        port = pd.Series([0.05, -0.02, 0.03], index=idx1)
        bench = pd.Series([0.03, -0.01, 0.02], index=idx2)
        excess = comp.compute_excess_returns(port, bench)
        assert len(excess) == 2  # only indices 1, 2 overlap


class TestComputeInformationRatio:
    def test_positive_ir(self):
        comp = BenchmarkComparator()
        excess = pd.Series([0.02, 0.01, -0.005, 0.03, 0.015, 0.01])
        ir = comp.compute_information_ratio(excess)
        assert ir > 0  # positive excess -> positive IR

    def test_single_value(self):
        comp = BenchmarkComparator()
        excess = pd.Series([0.02])
        assert comp.compute_information_ratio(excess) == 0.0

    def test_zero_tracking_error(self):
        comp = BenchmarkComparator()
        excess = pd.Series([0.01, 0.01, 0.01, 0.01])
        assert comp.compute_information_ratio(excess) == 0.0  # zero std


class TestComputeTrackingError:
    def test_basic(self):
        comp = BenchmarkComparator()
        excess = pd.Series([0.02, -0.01, 0.03, -0.005, 0.01])
        te = comp.compute_tracking_error(excess)
        assert te > 0
        expected = float(pd.Series(excess).std() * np.sqrt(12))
        assert abs(te - expected) < 1e-10

    def test_single_value(self):
        comp = BenchmarkComparator()
        assert comp.compute_tracking_error(pd.Series([0.02])) == 0.0


class TestComputeFullComparison:
    def test_basic(self):
        comp = BenchmarkComparator("000300.SH")
        port = pd.Series([0.05, -0.02, 0.03, 0.01])
        bench = pd.Series([0.03, -0.01, 0.02, 0.005])
        result = comp.compute_full_comparison(port, bench)
        assert result["benchmark_code"] == "000300.SH"
        assert "excess_returns" in result
        assert "information_ratio" in result
        assert "tracking_error" in result
        assert len(result["excess_returns"]) == 4
