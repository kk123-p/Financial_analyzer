"""
财务分析计算工具类
"""
import pandas as pd
import numpy as np

from ..config import (
    MA_SHORT, MA_MEDIUM, MA_LONG, MA_VERY_LONG,
    RSI_PERIOD, BB_PERIOD, BB_STD_MULTIPLIER,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
)
from ..logging_config import get_logger

logger = get_logger(__name__)


class FinancialCalculator:
    """财务分析计算工具类"""

    @staticmethod
    def calc_yoy_growth(current, previous):
        """计算同比增长率"""
        if previous is None or previous == 0 or pd.isna(previous) or pd.isna(current):
            return None
        return (current - previous) / abs(previous) * 100

    @staticmethod
    def calc_qoq_growth(current, previous):
        """计算环比增长率"""
        return FinancialCalculator.calc_yoy_growth(current, previous)

    @staticmethod
    def calc_structure_ratio(part, total):
        """计算结构占比"""
        if total is None or total == 0 or pd.isna(total) or pd.isna(part):
            return None
        return part / total * 100

    @staticmethod
    def calc_cagr(values, years):
        """计算复合增长率 (CAGR)"""
        if len(values) < 2 or years <= 0:
            return None
        start = values[-1]  # 最早的值
        end = values[0]     # 最新的值
        if start is None or start <= 0 or end is None or end <= 0:
            return None
        return ((end / start) ** (1 / years) - 1) * 100

    @staticmethod
    def safe_divide(numerator, denominator):
        """安全除法，避免除零错误"""
        if denominator is None or denominator == 0 or pd.isna(denominator):
            return None
        if numerator is None or pd.isna(numerator):
            return None
        return numerator / denominator

    @staticmethod
    def format_value(value, decimal=2, unit="", default="N/A"):
        """格式化数值显示"""
        if value is None or pd.isna(value):
            return default
        try:
            return f"{float(value):,.{decimal}f}{unit}"
        except Exception:
            return default

    @staticmethod
    def format_percentage(value, decimal=2, default="N/A"):
        """格式化百分比显示"""
        if value is None or pd.isna(value):
            return default
        try:
            return f"{float(value):.{decimal}f}%"
        except Exception:
            return default

    @staticmethod
    def format_change(value, decimal=2, default="N/A"):
        """格式化变化值（带正负号）"""
        if value is None or pd.isna(value):
            return default
        try:
            return f"{float(value):+.{decimal}f}%"
        except Exception:
            return default

    @staticmethod
    def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """计算技术指标"""
        if df.empty or "close" not in df.columns:
            return df

        df = df.copy()

        # 移动平均线
        df["MA5"] = df["close"].rolling(window=MA_SHORT).mean()
        df["MA10"] = df["close"].rolling(window=MA_MEDIUM).mean()
        df["MA20"] = df["close"].rolling(window=MA_LONG).mean()
        df["MA60"] = df["close"].rolling(window=MA_VERY_LONG).mean()

        # RSI
        delta = df["close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        rs = gain / loss
        df["RSI14"] = 100 - (100 / (1 + rs))

        # MACD（使用 adjust=False 以匹配常见金融软件实现）
        exp1 = df["close"].ewm(span=MACD_FAST, adjust=False).mean()
        exp2 = df["close"].ewm(span=MACD_SLOW, adjust=False).mean()
        df["MACD"] = exp1 - exp2
        df["Signal"] = df["MACD"].ewm(span=MACD_SIGNAL, adjust=False).mean()
        df["Histogram"] = df["MACD"] - df["Signal"]

        # 布林带
        df["BB_Middle"] = df["close"].rolling(window=BB_PERIOD).mean()
        df["BB_Std"] = df["close"].rolling(window=BB_PERIOD).std()
        df["BB_Upper"] = df["BB_Middle"] + BB_STD_MULTIPLIER * df["BB_Std"]
        df["BB_Lower"] = df["BB_Middle"] - BB_STD_MULTIPLIER * df["BB_Std"]

        return df

    @staticmethod
    def calculate_financial_ratios(balance_df, income_df, cashflow_df) -> dict:
        """计算财务比率"""
        ratios = {}

        if balance_df is not None and not balance_df.empty:
            latest = balance_df.iloc[0]
            current_assets = latest.get("total_cur_assets")
            current_liab = latest.get("total_cur_liab")
            inventory = latest.get("inventories")
            total_assets = latest.get("total_assets")
            total_liab = latest.get("total_liab")
            equity = latest.get("total_hldr_eqy_exc_min_int") or latest.get("total_equity")

            ratios["current_ratio"] = FinancialCalculator.safe_divide(current_assets, current_liab)
            quick_assets = (current_assets - inventory) if current_assets and inventory else current_assets
            ratios["quick_ratio"] = FinancialCalculator.safe_divide(quick_assets, current_liab)
            ratios["debt_ratio"] = FinancialCalculator.safe_divide(total_liab, total_assets)
            ratios["debt_to_equity"] = FinancialCalculator.safe_divide(total_liab, equity)

        if income_df is not None and not income_df.empty:
            latest = income_df.iloc[0]
            revenue = latest.get("total_revenue") or latest.get("revenue")
            net_profit = latest.get("net_profit")
            op_cost = latest.get("oper_cost") or latest.get("营业支出")
            if revenue and revenue > 0:
                if op_cost:
                    ratios["gross_margin"] = (revenue - op_cost) / revenue * 100
                if net_profit:
                    ratios["net_margin"] = net_profit / revenue * 100

        return ratios
