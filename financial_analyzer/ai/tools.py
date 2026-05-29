"""
AI 工具定义与执行器 — 为分析师 agent 提供数据查询能力
"""
import json
import pandas as pd
from ..logging_config import get_logger

logger = get_logger(__name__)

# OpenAI 兼容的工具定义
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_financial_metric",
            "description": "查询公司具体财务指标的精确数值。用于验证分析中的数据点。返回 JSON 格式的指标值。",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "指标名称，如 roe, pe_ttm, grossprofit_margin, netprofit_margin, debt_to_assets, total_revenue, net_profit"
                    },
                    "period": {
                        "type": "string",
                        "description": "报告期，如 20241231。留空则返回最新期。"
                    }
                },
                "required": ["metric"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_trend",
            "description": "获取公司某指标的历史趋势数据（近N年）。返回 JSON 格式的时间序列。",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric": {
                        "type": "string",
                        "description": "指标名称，如 roe, net_profit, revenue, grossprofit_margin"
                    },
                    "years": {
                        "type": "integer",
                        "description": "回溯年数，默认 3"
                    }
                },
                "required": ["metric"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_anomaly_signals",
            "description": "获取已检测到的公司财务异常信号列表。返回 JSON 格式的信号列表。",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


class ToolExecutor:
    """从 session data 中执行工具调用"""

    def __init__(self, data: dict, stock_code: str):
        self._data = data
        self._stock_code = stock_code

    def execute(self, tool_name: str, arguments: dict) -> str:
        """执行工具调用，返回 JSON 字符串"""
        try:
            if tool_name == "get_financial_metric":
                return self._exec_financial_metric(arguments)
            elif tool_name == "get_historical_trend":
                return self._exec_historical_trend(arguments)
            elif tool_name == "get_anomaly_signals":
                return self._exec_anomaly_signals()
            else:
                return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"工具执行失败 {tool_name}: {e}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    def _exec_financial_metric(self, args: dict) -> str:
        metric = args.get("metric", "")
        period = args.get("period", "")

        # 搜索顺序: financial, income, balance, cashflow, daily_basic
        for data_key in ["financial", "income", "balance", "cashflow", "daily_basic"]:
            df = self._data.get(data_key)
            if df is None or df.empty or metric not in df.columns:
                continue

            if period:
                # 按报告期筛选
                date_col = None
                for dc in ["end_date", "trade_date"]:
                    if dc in df.columns:
                        date_col = dc
                        break
                if date_col:
                    row = df[df[date_col].astype(str) == period]
                    if not row.empty:
                        val = row.iloc[0][metric]
                        return json.dumps({"metric": metric, "period": period, "value": _safe_float(val), "source": data_key}, ensure_ascii=False)

            # 返回最新期
            val = df.iloc[0][metric]
            date_col = "end_date" if "end_date" in df.columns else ("trade_date" if "trade_date" in df.columns else None)
            period_val = str(df.iloc[0][date_col]) if date_col else "latest"
            return json.dumps({"metric": metric, "period": period_val, "value": _safe_float(val), "source": data_key}, ensure_ascii=False)

        return json.dumps({"metric": metric, "error": "指标未找到"}, ensure_ascii=False)

    def _exec_historical_trend(self, args: dict) -> str:
        metric = args.get("metric", "")
        years = args.get("years", 3)

        for data_key in ["financial", "income", "balance", "cashflow"]:
            df = self._data.get(data_key)
            if df is None or df.empty or metric not in df.columns:
                continue

            date_col = None
            for dc in ["end_date", "trade_date"]:
                if dc in df.columns:
                    date_col = dc
                    break

            if date_col:
                sorted_df = df.sort_values(date_col, ascending=False).head(years * 4)  # 季报
                records = []
                for _, row in sorted_df.iterrows():
                    records.append({
                        "period": str(row[date_col]),
                        "value": _safe_float(row[metric])
                    })
                return json.dumps({"metric": metric, "trend": records, "source": data_key}, ensure_ascii=False)

        return json.dumps({"metric": metric, "error": "指标未找到"}, ensure_ascii=False)

    def _exec_anomaly_signals(self) -> str:
        signals = self._data.get("anomaly_signals", [])
        if not signals:
            return json.dumps({"signals": [], "message": "未检测到异常信号"}, ensure_ascii=False)

        result = []
        for s in signals:
            result.append({
                "name": s.get("name", ""),
                "level": s.get("level", ""),
                "data": s.get("data", s.get("trigger_data", ""))
            })
        return json.dumps({"signals": result}, ensure_ascii=False)


def _safe_float(val) -> float | None:
    """安全转换为 float"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return round(float(val), 4)
    except (ValueError, TypeError):
        return None
