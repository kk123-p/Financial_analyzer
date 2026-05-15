"""
基础分析器 - 行情概览、价格趋势、波动性、成交量
"""
import pandas as pd
import numpy as np
from datetime import datetime

from .base import BaseAnalyzer
from .report_formatter import ReportFormatter as RF
from ..calculator.financial import FinancialCalculator as FC
from ..config import (
    SEPARATOR_HEAVY, SEPARATOR_LIGHT,
    TRADING_DAYS_PER_YEAR, MA_SHORT, MA_MEDIUM, MA_LONG,
    TREND_WINDOW, VOLUME_MA_WINDOW, VOLUME_MA_LONG, VOLATILITY_WINDOW,
)
from ..logging_config import get_logger

logger = get_logger(__name__)


class MarketAnalyzer(BaseAnalyzer):
    """行情分析器（静态分析，不主动获取数据）"""

    def __init__(self, data: dict, stock_code: str, data_adapter=None, cache_manager=None):
        super().__init__(data, stock_code, data_adapter, cache_manager)

    def analyze_market_overview(self) -> str:
        """行情概览分析"""
        df_daily = self.data.get("daily")
        df_basic = self.data.get("daily_basic")

        if df_daily is None or df_daily.empty:
            return "无行情数据"

        result = RF.header("行情概览分析报告")
        result += self._extract_basic_info(df_basic)
        result += "\n"

        # 价格统计
        result += RF.section("价格统计")
        if "close" in df_daily.columns:
            close_prices = df_daily["close"]
            result += f"  数据期间: {len(df_daily)} 个交易日\n"
            result += f"  期初价格: {close_prices.iloc[-1]:.2f}\n"
            result += f"  期末价格: {close_prices.iloc[0]:.2f}\n"
            price_change = (close_prices.iloc[0] - close_prices.iloc[-1]) / close_prices.iloc[-1] * 100
            result += f"  期间涨跌幅: {price_change:+.2f}%\n"
            result += f"  最高价格: {close_prices.max():.2f}\n"
            result += f"  最低价格: {close_prices.min():.2f}\n"
            result += f"  平均价格: {close_prices.mean():.2f}\n"
            result += f"  价格标准差: {close_prices.std():.2f}\n"

        # 成交量统计
        result += "\n" + RF.section("成交量统计")
        if "vol" in df_daily.columns:
            volumes = df_daily["vol"]
            result += f"  平均成交量: {volumes.mean():,.0f} 手\n"
            result += f"  最大成交量: {volumes.max():,.0f} 手\n"
            result += f"  最小成交量: {volumes.min():,.0f} 手\n"
            if len(volumes) >= 2:
                volume_change = (volumes.iloc[0] - volumes.iloc[-1]) / volumes.iloc[-1] * 100
                result += f"  成交量变化: {volume_change:+.2f}%\n"

        # 换手率
        if df_basic is not None and "turnover_rate" in df_basic.columns:
            result += "\n" + RF.section("换手率统计")
            tr = df_basic["turnover_rate"]
            result += f"  平均换手率: {tr.mean():.2f}%\n"
            result += f"  最大换手率: {tr.max():.2f}%\n"
            result += f"  最小换手率: {tr.min():.2f}%\n"

        result += RF.footer()
        return result

    def analyze_price_trend(self) -> str:
        """价格趋势分析"""
        df_daily = self.data.get("daily")
        if df_daily is None or df_daily.empty or "close" not in df_daily.columns:
            return "无价格数据"

        result = RF.header("价格趋势分析报告")
        close_prices = df_daily["close"]

        # 趋势分析
        result += RF.section("趋势分析")
        ma5 = close_prices.rolling(window=MA_SHORT).mean()
        ma10 = close_prices.rolling(window=MA_MEDIUM).mean()
        ma20 = close_prices.rolling(window=MA_LONG).mean()

        result += f"  5日均线: {ma5.iloc[0]:.2f}\n"
        result += f"  10日均线: {ma10.iloc[0]:.2f}\n"
        result += f"  20日均线: {ma20.iloc[0]:.2f}\n\n"

        current_price = close_prices.iloc[0]
        if current_price > ma5.iloc[0] > ma10.iloc[0] > ma20.iloc[0]:
            result += "  📈 趋势判断: 强势上涨趋势\n"
        elif current_price < ma5.iloc[0] < ma10.iloc[0] < ma20.iloc[0]:
            result += "  📉 趋势判断: 强势下跌趋势\n"
        elif ma5.iloc[0] > ma10.iloc[0] > ma20.iloc[0]:
            result += "  ↗️  趋势判断: 多头排列\n"
        elif ma5.iloc[0] < ma10.iloc[0] < ma20.iloc[0]:
            result += "  ↘️  趋势判断: 空头排列\n"
        else:
            result += "  ↔️  趋势判断: 震荡整理\n"

        # 支撑阻力
        result += "\n" + RF.section("支撑阻力分析")
        recent_high = close_prices.head(TREND_WINDOW).max()
        recent_low = close_prices.head(TREND_WINDOW).min()
        result += f"  近期高点: {recent_high:.2f}\n"
        result += f"  近期低点: {recent_low:.2f}\n"
        result += f"  当前价格: {current_price:.2f}\n\n"
        result += f"  距离近期高点: {(recent_high - current_price) / current_price * 100:.2f}%\n"
        result += f"  距离近期低点: {(current_price - recent_low) / current_price * 100:.2f}%\n"

        # 价格通道
        result += "\n" + RF.section("价格通道")
        high_prices = df_daily["high"] if "high" in df_daily.columns else close_prices
        low_prices = df_daily["low"] if "low" in df_daily.columns else close_prices
        channel_high = high_prices.head(TREND_WINDOW).max()
        channel_low = low_prices.head(TREND_WINDOW).min()
        channel_width = (channel_high - channel_low) / channel_low * 100
        result += f"  通道上轨: {channel_high:.2f}\n"
        result += f"  通道下轨: {channel_low:.2f}\n"
        result += f"  通道宽度: {channel_width:.2f}%\n"

        if current_price > channel_high * 0.95:
            result += "  ⚠️ 价格接近通道上轨，注意阻力\n"
        elif current_price < channel_low * 1.05:
            result += "  ⚠️ 价格接近通道下轨，注意支撑\n"

        result += RF.footer()
        return result

    def analyze_volatility(self) -> str:
        """波动性分析"""
        df_daily = self.data.get("daily")
        if df_daily is None or df_daily.empty or "close" not in df_daily.columns:
            return "无价格数据"

        result = RF.header("波动性分析报告")
        close_prices = df_daily["close"]
        returns = close_prices.pct_change().dropna()

        result += RF.section("波动性统计")
        if len(returns) > 0:
            result += f"  数据期间: {len(returns)} 个交易日\n"
            result += f"  平均日收益率: {returns.mean()*100:.4f}%\n"
            result += f"  日收益率标准差: {returns.std()*100:.4f}%\n"
            result += f"  年化波动率: {returns.std()*np.sqrt(TRADING_DAYS_PER_YEAR)*100:.2f}%\n"
            result += f"  最大单日涨幅: {returns.max()*100:.2f}%\n"
            result += f"  最大单日跌幅: {returns.min()*100:.2f}%\n"

            up_days = (returns > 0).sum()
            down_days = (returns < 0).sum()
            flat_days = (returns == 0).sum()
            result += f"  上涨天数: {up_days} ({up_days/len(returns)*100:.1f}%)\n"
            result += f"  下跌天数: {down_days} ({down_days/len(returns)*100:.1f}%)\n"
            result += f"  平盘天数: {flat_days} ({flat_days/len(returns)*100:.1f}%)\n"

        # 波动率特征
        if len(returns) >= 20:
            result += "\n" + RF.section("波动率特征")
            rolling_vol = returns.rolling(window=VOLATILITY_WINDOW).std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100
            current_vol = rolling_vol.iloc[0] if not rolling_vol.empty else None
            avg_vol = rolling_vol.mean()

            if current_vol is not None:
                result += f"  当前年化波动率: {current_vol:.2f}%\n"
                result += f"  平均年化波动率: {avg_vol:.2f}%\n\n"
                if current_vol > avg_vol * 1.5:
                    result += "  ⚠️ 当前波动率显著高于平均水平\n"
                elif current_vol < avg_vol * 0.7:
                    result += "  ⚠️ 当前波动率显著低于平均水平\n"
                else:
                    result += "  ↔️ 当前波动率处于正常水平\n"

        # 风险调整收益
        if len(returns) > 0:
            result += "\n" + RF.section("风险调整收益")
            annual_return = ((1 + returns.mean()) ** TRADING_DAYS_PER_YEAR - 1) * 100
            annual_vol = returns.std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100
            if annual_vol > 0:
                sharpe = annual_return / annual_vol
                result += f"  年化收益率: {annual_return:.2f}%\n"
                result += f"  年化波动率: {annual_vol:.2f}%\n"
                result += f"  夏普比率: {sharpe:.3f}\n\n"
                if sharpe > 1:
                    result += "  📈 夏普比率 > 1，风险调整后收益良好\n"
                elif sharpe > 0:
                    result += "  ↔️ 夏普比率 > 0，有正的风险调整收益\n"
                else:
                    result += "  ⚠️ 夏普比率 < 0，风险调整后收益为负\n"

        result += RF.footer()
        return result

    def analyze_volume(self) -> str:
        """成交量分析"""
        df_daily = self.data.get("daily")
        if df_daily is None or df_daily.empty or "vol" not in df_daily.columns:
            return "无成交量数据"

        result = RF.header("成交量分析报告")
        volumes = df_daily["vol"]
        close_prices = df_daily["close"] if "close" in df_daily.columns else None

        result += RF.section("成交量统计")
        result += f"  数据期间: {len(volumes)} 个交易日\n"
        result += f"  平均成交量: {volumes.mean():,.0f} 手\n"
        result += f"  最大成交量: {volumes.max():,.0f} 手\n"
        result += f"  最小成交量: {volumes.min():,.0f} 手\n"
        result += f"  成交量标准差: {volumes.std():,.0f} 手\n"

        # 成交量变化
        result += "\n" + RF.section("成交量变化")
        if len(volumes) >= 2:
            volume_change = (volumes.iloc[0] - volumes.iloc[-1]) / volumes.iloc[-1] * 100
            result += f"  期间成交量变化: {volume_change:+.2f}%\n"

        volume_ma5 = volumes.rolling(window=VOLUME_MA_WINDOW).mean()
        volume_ma10 = volumes.rolling(window=VOLUME_MA_LONG).mean()
        result += f"  5日平均成交量: {volume_ma5.iloc[0]:,.0f} 手\n"
        result += f"  10日平均成交量: {volume_ma10.iloc[0]:,.0f} 手\n\n"

        current_volume = volumes.iloc[0]
        if current_volume > volume_ma5.iloc[0] * 1.5:
            result += "  📈 成交量显著放大\n"
        elif current_volume < volume_ma5.iloc[0] * 0.7:
            result += "  📉 成交量显著萎缩\n"
        else:
            result += "  ↔️ 成交量处于正常水平\n"

        # 量价关系
        if close_prices is not None and len(volumes) >= TREND_WINDOW:
            result += "\n" + RF.section("量价关系分析")
            correlation = volumes.head(TREND_WINDOW).corr(close_prices.head(TREND_WINDOW))
            result += f"  近期量价相关系数: {correlation:.4f}\n\n"
            if correlation > 0.3:
                result += "  📈 量价齐升，上涨趋势健康\n"
            elif correlation < -0.3:
                result += "  📉 量价背离，趋势可能反转\n"
            else:
                result += "  ↔️ 量价关系不明显\n"

        result += RF.footer()
        return result

    def _extract_basic_info(self, df_basic) -> str:
        """提取基本信息"""
        if df_basic is None or df_basic.empty:
            return "无基本信息"

        info = RF.section("股票基本信息")
        latest = df_basic.iloc[0] if len(df_basic) > 0 else None
        if latest is not None:
            info += f"  股票代码: {self.stock_code}\n"
            for key, label in [
                ("name", "公司名称"), ("industry", "所属行业"),
                ("market", "市场类型"), ("trade_date", "最新交易日"),
            ]:
                if key in latest:
                    info += f"  {label}: {latest[key]}\n"
            if "close" in latest:
                info += f"  最新收盘价: {latest['close']:.2f}\n"
            if "pe" in latest:
                info += f"  市盈率(PE): {latest['pe']:.2f}\n"
            if "pb" in latest:
                info += f"  市净率(PB): {latest['pb']:.2f}\n"
            # total_mv 单位是万元（Tushare 惯例），/10000 转为亿元
            if "total_mv" in latest:
                info += f"  总市值: {latest['total_mv']/10000:.2f}亿元\n"
            if "turnover_rate" in latest:
                info += f"  换手率: {latest['turnover_rate']:.2f}%\n"
        return info
