"""
量价财务结合分析、股东股本分析
"""
from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..config import SEPARATOR_LIGHT, TREND_WINDOW
from ..logging_config import get_logger

logger = get_logger(__name__)


class CombinedAnalyzer(BaseAnalyzer):
    """量价财务结合分析器"""

    def __init__(self, data: dict, stock_code: str, data_adapter, cache_manager):
        super().__init__(data, stock_code, data_adapter, cache_manager)

    def analyze_price_financial_combined(self) -> str:
        """量价财务结合分析"""
        result = RF.header("量价财务结合分析报告")

        df_daily = self.data.get("daily")
        df_fin, _ = self._fetch_data("financial")

        if df_daily is None or df_daily.empty:
            return result + "❌ 无行情数据"

        close_prices = df_daily["close"]
        volumes = df_daily["vol"] if "vol" in df_daily.columns else None

        # 价格与财务指标关联
        result += RF.section("价格走势概览")
        result += f"  当前价格: {close_prices.iloc[0]:.2f}\n"
        result += f"  期间最高: {close_prices.max():.2f}\n"
        result += f"  期间最低: {close_prices.min():.2f}\n"
        result += f"  价格波动率: {close_prices.std() / close_prices.mean() * 100:.2f}%\n\n"

        # 量价分析
        if volumes is not None:
            result += RF.section("量价关系分析")
            result += f"  平均成交量: {volumes.mean():,.0f}\n"
            result += f"  成交量波动率: {volumes.std() / volumes.mean() * 100:.2f}%\n"

            # 量价相关性
            if len(close_prices) >= TREND_WINDOW:
                corr = close_prices.head(TREND_WINDOW).corr(volumes.head(TREND_WINDOW))
                result += f"  量价相关系数(近20日): {corr:.4f}\n\n"
                if corr > 0.3:
                    result += "  📈 量价齐升，上涨趋势健康\n"
                elif corr < -0.3:
                    result += "  📉 量价背离，注意趋势反转风险\n"
                else:
                    result += "  ↔️ 量价关系不明显\n"

        # 财务指标与估值
        if df_fin is not None and not df_fin.empty:
            result += "\n" + RF.section("财务指标与估值")
            latest_fin = df_fin.iloc[0]
            roe = latest_fin.get("roe")
            pe = None

            # 从 basic 数据获取 PE
            df_basic = self.data.get("daily_basic")
            if df_basic is not None and not df_basic.empty:
                pe = df_basic.iloc[0].get("pe")

            if roe:
                result += f"  ROE: {roe:.2f}%\n"
            if pe:
                result += f"  PE(TTM): {pe:.2f}\n"
                if roe and pe > 0:
                    pb = pe * roe / 100
                    result += f"  PB(估算): {pb:.2f}\n"

                    # PEG 估值
                    growth = latest_fin.get("q_profit_yoy") or latest_fin.get("or_yoy")
                    if growth and growth > 0:
                        peg = pe / growth
                        result += f"  PEG: {peg:.2f}\n"
                        if peg < 1:
                            result += "  ✓ PEG < 1，估值偏低\n"
                        elif peg < 2:
                            result += "  ○ PEG 在 1-2 之间，估值合理\n"
                        else:
                            result += "  ⚠ PEG > 2，估值偏高\n"

        result += RF.footer()
        return result

    def analyze_shareholders(self) -> str:
        """股东股本分析"""
        result = RF.header("股东股本分析报告")

        df_basic = self.data.get("daily_basic") or self.data.get("basic")

        if df_basic is None or df_basic.empty:
            return result + "❌ 未获取到股东股本数据"

        latest = df_basic.iloc[0]

        # 基本股本信息
        result += RF.section("股本信息")
        # total_mv 单位是万元（Tushare 惯例），/10000 转为亿元
        if "total_mv" in latest:
            result += f"  总市值: {latest['total_mv'] / 10000:.2f} 亿元\n"
        if "circ_mv" in latest:
            result += f"  流通市值: {latest['circ_mv'] / 10000:.2f} 亿元\n"
        if "turnover_rate" in latest:
            result += f"  换手率: {latest['turnover_rate']:.2f}%\n"
        if "volume_ratio" in latest:
            result += f"  量比: {latest['volume_ratio']:.2f}\n"

        # 估值信息
        result += "\n" + RF.section("估值信息")
        for key, label in [
            ("pe", "市盈率(PE)"), ("pe_ttm", "PE(TTM)"),
            ("pb", "市净率(PB)"), ("ps", "市销率(PS)"),
        ]:
            val = latest.get(key)
            if val:
                result += f"  {label}: {val:.2f}\n"

        # 换手率分析
        if "turnover_rate" in latest:
            tr = latest["turnover_rate"]
            result += "\n" + RF.section("换手率分析")
            if tr > 10:
                result += f"  ⚠ 换手率 {tr:.2f}% 极高，交易异常活跃\n"
            elif tr > 5:
                result += f"  📈 换手率 {tr:.2f}% 较高，市场关注度高\n"
            elif tr > 1:
                result += f"  ↔️ 换手率 {tr:.2f}% 正常\n"
            else:
                result += f"  📉 换手率 {tr:.2f}% 较低，交易不活跃\n"

        result += RF.footer()
        return result
