"""数据获取服务 — 封装 DataSourceAdapter"""
import logging
from datetime import datetime
from typing import Any

import pandas as pd

from financial_analyzer.config import DEFAULT_START_DATE
from financial_analyzer.data_sources.adapter import DataSourceAdapter
from financial_analyzer.cache.manager import DataCacheManager

logger = logging.getLogger(__name__)


class DataService:
    """数据获取 + KPI 提取"""

    def __init__(self, adapter: DataSourceAdapter):
        self.adapter = adapter

    # 所有可获取的数据类型
    BASIC_DATA_TYPES = ["daily", "daily_basic", "basic", "stock_basic"]
    FINANCIAL_DATA_TYPES = ["income", "balance", "cashflow", "financial",
                            "fina_audit", "mainbz"]

    def fetch_stock_data(
        self,
        stock_code: str,
        start_date: str = DEFAULT_START_DATE,
        end_date: str | None = None,
        source: str | None = None,
        include_financials: bool = True,
    ) -> dict[str, pd.DataFrame]:
        """获取股票数据（多类型，含财务报表）"""
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        if source and source != self.adapter.active_source:
            self.adapter.set_active_source(source)

        effective_source = self.adapter.active_source
        data: dict[str, pd.DataFrame] = {}

        # 第一阶段：获取基本行情数据
        all_types = self.BASIC_DATA_TYPES.copy()
        if include_financials:
            all_types += self.FINANCIAL_DATA_TYPES

        for dtype in all_types:
            try:
                df = self.adapter.get_stock_data(stock_code, start_date, end_date, dtype)
                if df is not None and not df.empty:
                    data[dtype] = df
                    logger.info(f"获取 {dtype} 成功: {len(df)} 行")
            except Exception as e:
                logger.warning(f"获取 {dtype} 失败: {e}")

        # 如果没获取到任何数据，尝试回退数据源
        if not data:
            fallbacks = [s for s in self.adapter.get_available_sources()
                        if s != effective_source]
            for fb in fallbacks:
                self.adapter.set_active_source(fb)
                effective_source = fb
                for dtype in self.BASIC_DATA_TYPES:
                    try:
                        df = self.adapter.get_stock_data(stock_code, start_date, end_date, dtype)
                        if df is not None and not df.empty:
                            data[dtype] = df
                    except Exception:
                        pass
                if data:
                    break

        return data

    def fetch_financials_async(
        self,
        stock_code: str,
        start_date: str = DEFAULT_START_DATE,
        end_date: str | None = None,
    ) -> dict[str, pd.DataFrame]:
        """获取财务报表数据（独立调用，用于后台补充）"""
        if end_date is None:
            end_date = datetime.now().strftime("%Y%m%d")

        data: dict[str, pd.DataFrame] = {}
        for dtype in self.FINANCIAL_DATA_TYPES:
            try:
                df = self.adapter.get_stock_data(stock_code, start_date, end_date, dtype)
                if df is not None and not df.empty:
                    data[dtype] = df
                    logger.info(f"财务报表 {dtype} 获取成功: {len(df)} 行")
            except Exception as e:
                logger.debug(f"财务报表 {dtype} 获取失败: {e}")
        return data

    def extract_kpis(self, data: dict) -> dict[str, Any]:
        """从原始数据提取 KPI 指标"""
        kpis = {
            "stock_name": "--",
            "current_price": "--",
            "price_change": "--",
            "price_change_pct": "--",
            "price_change_up": False,
            "volume": "--",
            "pe_ratio": "--",
            "market_cap": "--",
            "source": self.adapter.active_source.upper(),
        }

        basic = data.get("basic")
        daily = data.get("daily")
        daily_basic = data.get("daily_basic")

        # 股票名称
        if basic is not None and not basic.empty:
            name = basic.iloc[0].get("name", "")
            if name and name != "--":
                kpis["stock_name"] = name

        # 价格 & 涨跌幅
        if daily is not None and not daily.empty and "close" in daily.columns:
            current = daily["close"].iloc[0]
            prev = daily["close"].iloc[1] if len(daily) > 1 else current
            change_pct = (current - prev) / prev * 100 if prev else 0
            kpis["current_price"] = f"{current:.2f}"
            kpis["price_change"] = f"{change_pct:+.2f}%"
            kpis["price_change_pct"] = f"{abs(change_pct):.2f}%"
            kpis["price_change_up"] = change_pct >= 0

            if "vol" in daily.columns:
                vol = daily["vol"].iloc[0]
                if vol >= 1e8:
                    kpis["volume"] = f"{vol / 1e8:.2f}亿"
                elif vol >= 1e4:
                    kpis["volume"] = f"{vol / 1e4:.2f}万"
                else:
                    kpis["volume"] = f"{vol:,.0f}"

        # PE
        pe = None
        if daily_basic is not None and not daily_basic.empty:
            pe = daily_basic.iloc[0].get("pe_ttm")
        if not pe and basic is not None and not basic.empty:
            pe = basic.iloc[0].get("pe") or basic.iloc[0].get("pe_ttm")
        if pe:
            try:
                kpis["pe_ratio"] = f"{float(pe):.1f}"
            except (ValueError, TypeError):
                pass

        # 市值
        total_mv = None
        if daily_basic is not None and not daily_basic.empty:
            total_mv = daily_basic.iloc[0].get("total_mv")
        if not total_mv and basic is not None and not basic.empty:
            total_mv = basic.iloc[0].get("total_mv")
        if total_mv:
            try:
                mv = float(total_mv)
                if mv >= 1e8:
                    kpis["market_cap"] = f"{mv / 1e8:.0f}亿"
                else:
                    kpis["market_cap"] = f"{mv / 1e4:.1f}万"
            except (ValueError, TypeError):
                pass

        return kpis

    def get_available_sources(self) -> list[str]:
        return self.adapter.get_available_sources()

    @property
    def active_source(self) -> str:
        return self.adapter.active_source
