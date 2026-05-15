"""
技术指标分析器
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..logging_config import get_logger

logger = get_logger(__name__)


class TechnicalAnalyzer(BaseAnalyzer):
    """技术指标分析器（静态分析，不主动获取数据）"""

    def __init__(self, data: dict, stock_code: str, data_adapter=None, cache_manager=None):
        super().__init__(data, stock_code, data_adapter, cache_manager)

    def analyze_technical_indicators(self) -> str:
        """技术指标分析"""
        df_daily = self.data.get("daily")
        if df_daily is None or df_daily.empty or "close" not in df_daily.columns:
            return "无价格数据"

        df = FC.calculate_technical_indicators(df_daily)
        result = RF.header("技术指标分析报告")
        latest = df.iloc[0]

        # RSI
        result += RF.section("RSI相对强弱指标")
        if "RSI14" in latest:
            rsi = latest["RSI14"]
            result += f"  RSI(14): {rsi:.2f}\n\n"
            if rsi > 70:
                result += "  ⚠️ RSI > 70，处于超买区域\n"
            elif rsi < 30:
                result += "  ⚠️ RSI < 30，处于超卖区域\n"
            elif rsi > 50:
                result += "  ↗️ RSI > 50，多方占优\n"
            else:
                result += "  ↘️ RSI < 50，空方占优\n"

        # MACD
        result += "\n" + RF.section("MACD指标")
        if all(k in latest for k in ["MACD", "Signal", "Histogram"]):
            macd = latest["MACD"]
            signal = latest["Signal"]
            histogram = latest["Histogram"]
            result += f"  MACD: {macd:.4f}\n"
            result += f"  Signal: {signal:.4f}\n"
            result += f"  Histogram: {histogram:.4f}\n\n"
            if macd > signal and histogram > 0:
                result += "  📈 MACD金叉，上涨信号\n"
            elif macd < signal and histogram < 0:
                result += "  📉 MACD死叉，下跌信号\n"
            elif histogram > 0:
                result += "  ↗️ 柱状线为正，多头力量增强\n"
            else:
                result += "  ↘️ 柱状线为负，空头力量增强\n"

        # 布林带
        result += "\n" + RF.section("布林带指标")
        if all(k in latest for k in ["BB_Upper", "BB_Middle", "BB_Lower"]):
            bb_upper = latest["BB_Upper"]
            bb_middle = latest["BB_Middle"]
            bb_lower = latest["BB_Lower"]
            current_price = latest["close"]
            result += f"  上轨: {bb_upper:.2f}\n"
            result += f"  中轨: {bb_middle:.2f}\n"
            result += f"  下轨: {bb_lower:.2f}\n"
            result += f"  当前价格: {current_price:.2f}\n\n"
            bb_pos = (current_price - bb_lower) / (bb_upper - bb_lower) * 100
            if current_price > bb_upper:
                result += "  ⚠️ 价格突破上轨，可能回调\n"
            elif current_price < bb_lower:
                result += "  ⚠️ 价格突破下轨，可能反弹\n"
            elif bb_pos > 70:
                result += "  ↗️ 价格靠近上轨，强势\n"
            elif bb_pos < 30:
                result += "  ↘️ 价格靠近下轨，弱势\n"
            else:
                result += "  ↔️ 价格在中轨附近，震荡\n"

        # 移动平均线
        result += "\n" + RF.section("移动平均线")
        for col in df.columns:
            if col.startswith("MA") and col in latest:
                result += f"  {col}: {latest[col]:.2f}\n"

        result += RF.footer()
        return result
