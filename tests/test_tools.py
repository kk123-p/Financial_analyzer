"""工具定义与执行器测试"""
import json
import pytest
import pandas as pd

from financial_analyzer.ai.tools import TOOL_DEFINITIONS, ToolExecutor, _safe_float


@pytest.fixture
def sample_data():
    financial = pd.DataFrame({
        "end_date": ["20241231", "20231231", "20221231", "20211231"],
        "roe": [15.2, 14.8, 13.5, 12.1],
        "grossprofit_margin": [35.6, 34.2, 33.0, 31.5],
        "netprofit_margin": [12.3, 11.8, 10.5, 9.8],
    })
    income = pd.DataFrame({
        "end_date": ["20241231", "20231231", "20221231", "20211231"],
        "total_revenue": [100.5, 95.2, 88.0, 80.1],
        "net_profit": [12.3, 11.2, 9.2, 7.8],
    })
    daily_basic = pd.DataFrame({
        "trade_date": ["20250101"],
        "pe_ttm": [25.3],
        "pb": [3.2],
    })
    return {
        "financial": financial,
        "income": income,
        "balance": pd.DataFrame(),
        "cashflow": pd.DataFrame(),
        "daily_basic": daily_basic,
        "anomaly_signals": [
            {"name": "应收增速>营收增速", "level": "warning", "data": "应收+30% vs 营收+15%"},
        ],
    }


@pytest.fixture
def executor(sample_data):
    return ToolExecutor(sample_data, "000001")


# ---- TOOL_DEFINITIONS format ----

class TestToolDefinitionsFormat:

    def test_is_list_of_dicts(self):
        assert isinstance(TOOL_DEFINITIONS, list)
        assert len(TOOL_DEFINITIONS) > 0
        for tool in TOOL_DEFINITIONS:
            assert isinstance(tool, dict)

    def test_each_has_type_function(self):
        for tool in TOOL_DEFINITIONS:
            assert tool.get("type") == "function"

    def test_each_has_function_name(self):
        for tool in TOOL_DEFINITIONS:
            func = tool.get("function", {})
            assert isinstance(func.get("name"), str)
            assert len(func["name"]) > 0

    def test_each_has_function_parameters(self):
        for tool in TOOL_DEFINITIONS:
            func = tool.get("function", {})
            params = func.get("parameters", {})
            assert params.get("type") == "object"
            assert "properties" in params


# ---- get_financial_metric ----

class TestGetFinancialMetric:

    def test_normal_query_returns_latest(self, executor):
        result = json.loads(executor.execute("get_financial_metric", {"metric": "roe"}))
        assert result["metric"] == "roe"
        assert result["value"] == 15.2
        assert result["period"] == "20241231"
        assert result["source"] == "financial"

    def test_specific_period(self, executor):
        result = json.loads(executor.execute("get_financial_metric", {
            "metric": "roe", "period": "20231231"
        }))
        assert result["value"] == 14.8
        assert result["period"] == "20231231"

    def test_metric_from_income(self, executor):
        result = json.loads(executor.execute("get_financial_metric", {
            "metric": "total_revenue"
        }))
        assert result["value"] == 100.5
        assert result["source"] == "income"

    def test_metric_from_daily_basic(self, executor):
        result = json.loads(executor.execute("get_financial_metric", {
            "metric": "pe_ttm"
        }))
        assert result["value"] == 25.3
        assert result["source"] == "daily_basic"

    def test_metric_not_found(self, executor):
        result = json.loads(executor.execute("get_financial_metric", {
            "metric": "nonexistent_metric"
        }))
        assert "error" in result
        assert result["metric"] == "nonexistent_metric"

    def test_period_not_found(self, executor):
        result = json.loads(executor.execute("get_financial_metric", {
            "metric": "roe", "period": "20201231"
        }))
        # Falls through to latest when period not found in any df
        assert result["value"] == 15.2


# ---- get_historical_trend ----

class TestHistoricalTrend:

    def test_normal_query(self, executor):
        result = json.loads(executor.execute("get_historical_trend", {
            "metric": "roe"
        }))
        assert result["metric"] == "roe"
        assert len(result["trend"]) == 4
        assert result["trend"][0]["period"] == "20241231"
        assert result["trend"][0]["value"] == 15.2

    def test_custom_years(self, executor):
        result = json.loads(executor.execute("get_historical_trend", {
            "metric": "roe", "years": 1
        }))
        assert result["metric"] == "roe"
        assert len(result["trend"]) == 4  # 1 year * 4 quarters available
        assert result["source"] == "financial"

    def test_metric_from_income(self, executor):
        result = json.loads(executor.execute("get_historical_trend", {
            "metric": "net_profit"
        }))
        assert result["source"] == "income"
        assert len(result["trend"]) == 4

    def test_metric_not_found(self, executor):
        result = json.loads(executor.execute("get_historical_trend", {
            "metric": "nonexistent"
        }))
        assert "error" in result


# ---- get_anomaly_signals ----

class TestAnomalySignals:

    def test_with_signals(self, executor):
        result = json.loads(executor.execute("get_anomaly_signals", {}))
        assert len(result["signals"]) == 1
        assert result["signals"][0]["name"] == "应收增速>营收增速"
        assert result["signals"][0]["level"] == "warning"

    def test_no_signals(self, sample_data):
        sample_data["anomaly_signals"] = []
        executor = ToolExecutor(sample_data, "000001")
        result = json.loads(executor.execute("get_anomaly_signals", {}))
        assert result["signals"] == []
        assert "message" in result

    def test_missing_signals_key(self, sample_data):
        del sample_data["anomaly_signals"]
        executor = ToolExecutor(sample_data, "000001")
        result = json.loads(executor.execute("get_anomaly_signals", {}))
        assert result["signals"] == []


# ---- execute dispatch ----

class TestExecuteDispatch:

    def test_unknown_tool(self, executor):
        result = json.loads(executor.execute("unknown_tool", {}))
        assert "error" in result
        assert "未知工具" in result["error"]


# ---- _safe_float ----

class TestSafeFloat:

    def test_normal_float(self):
        assert _safe_float(3.14) == 3.14

    def test_int(self):
        assert _safe_float(42) == 42.0

    def test_string_number(self):
        assert _safe_float("15.2") == 15.2

    def test_none(self):
        assert _safe_float(None) is None

    def test_nan(self):
        assert _safe_float(float("nan")) is None

    def test_pandas_nan(self):
        assert _safe_float(pd.NaT) is None

    def test_non_numeric_string(self):
        assert _safe_float("abc") is None

    def test_rounding(self):
        assert _safe_float(3.14159) == 3.1416
