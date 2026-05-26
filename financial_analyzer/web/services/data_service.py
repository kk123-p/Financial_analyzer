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
    MARKET_DATA_TYPES = ["moneyflow", "margin", "margin_detail", "hk_hold",
                         "block_trade", "weekly", "monthly", "stk_holdernumber"]
    FINANCIAL_DATA_TYPES = ["income", "balance", "cashflow", "financial",
                            "dividend", "top10_holders", "top10_floatholders",
                            "fina_audit", "fina_mainbz"]

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
            all_types += self.MARKET_DATA_TYPES + self.FINANCIAL_DATA_TYPES

        for dtype in all_types:
            try:
                df = self.adapter.get_stock_data(stock_code, start_date, end_date, dtype)
                if df is not None and not df.empty:
                    data[dtype] = df
                    logger.info(f"获取 {dtype} 成功: {len(df)} 行")
            except Exception as e:
                logger.warning(f"获取 {dtype} 失败: {e}")

        # 如果没获取到任何数据，尝试回退数据源
        # 优先国内数据源（yfinance 在国内不可靠，跳过）
        if not data:
            all_sources = self.adapter.get_available_sources()
            # Reorder: domestic sources (akshare, sina) before foreign (yfinance)
            domestic = [s for s in all_sources if s in ('akshare', 'sina') and s != effective_source]
            foreign = [s for s in all_sources if s == 'yfinance' and s != effective_source]
            fallbacks = domestic + foreign
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

        # 股票名称 — 从多个来源回退
        name = None
        # 1) basic 表
        if basic is not None and not basic.empty:
            name = basic.iloc[0].get("name", "")
        # 2) stock_basic 表
        if (not name or name == "--") and "stock_basic" in data:
            sb = data.get("stock_basic")
            if sb is not None and not sb.empty:
                name = sb.iloc[0].get("name", "") or sb.iloc[0].get("NAME", "")
        # 3) Sina 格式: basic 的 ts_code 中提取
        if not name or name == "--":
            if basic is not None and not basic.empty:
                ts = basic.iloc[0].get("ts_code", "")
                if ts and "." in str(ts):
                    name = str(ts).split(".")[1] if "." in str(ts) else str(ts)
        if name and str(name).strip() and str(name) != "--":
            kpis["stock_name"] = str(name).strip()

        # 价格 & 涨跌幅
        if daily is not None and not daily.empty and "close" in daily.columns:
            current = daily["close"].iloc[0]
            prev = daily["close"].iloc[1] if len(daily) > 1 else current
            change_pct = (current - prev) / prev * 100 if prev else 0
            kpis["current_price"] = f"{current:.2f}"
            kpis["price_change"] = f"{change_pct:+.2f}%"
            kpis["price_change_pct"] = f"{abs(change_pct):.2f}%"
            kpis["price_change_up"] = bool(change_pct >= 0)

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
                mv = float(total_mv)  # Tushare 单位：万元
                if mv >= 1e4:  # >= 1亿元 = 10000万元
                    kpis["market_cap"] = f"{mv / 1e4:.0f}亿"
                else:
                    kpis["market_cap"] = f"{mv:.0f}万元"
            except (ValueError, TypeError):
                pass

        # ===== 新增 KPI（Phase 1 扩展数据）=====

        # 主力资金净流入
        moneyflow = data.get("moneyflow")
        if moneyflow is not None and not moneyflow.empty:
            net_mf = moneyflow.iloc[0].get("net_mf_amount")
            if net_mf:
                try:
                    net_mf_val = float(net_mf)
                    if abs(net_mf_val) >= 1e8:
                        kpis["net_mf_amount"] = f"{net_mf_val / 1e8:+.2f}亿"
                    elif abs(net_mf_val) >= 1e4:
                        kpis["net_mf_amount"] = f"{net_mf_val / 1e4:+.2f}万"
                    else:
                        kpis["net_mf_amount"] = f"{net_mf_val:+,.0f}"
                    kpis["net_mf_positive"] = net_mf_val >= 0
                except (ValueError, TypeError):
                    kpis["net_mf_amount"] = "--"

        # 融资余额
        margin = data.get("margin")
        if margin is not None and not margin.empty:
            rzye = margin.iloc[0].get("rzye")
            if rzye:
                try:
                    kpis["margin_balance"] = f"{float(rzye) / 1e8:.2f}亿"
                except (ValueError, TypeError):
                    kpis["margin_balance"] = "--"

        # 北向持股占比
        hk_hold = data.get("hk_hold")
        if hk_hold is not None and not hk_hold.empty:
            ratio = hk_hold.iloc[0].get("ratio")
            if ratio:
                try:
                    kpis["hk_hold_ratio"] = f"{float(ratio):.2f}%"
                except (ValueError, TypeError):
                    kpis["hk_hold_ratio"] = "--"

        # 股东人数
        stk_holdernumber = data.get("stk_holdernumber")
        if stk_holdernumber is not None and not stk_holdernumber.empty:
            holder_num = stk_holdernumber.iloc[0].get("holder_num")
            if holder_num:
                try:
                    hn = float(holder_num)
                    if hn >= 1e4:
                        kpis["holder_num"] = f"{hn / 1e4:.2f}万"
                    else:
                        kpis["holder_num"] = f"{hn:,.0f}"
                except (ValueError, TypeError):
                    kpis["holder_num"] = "--"

        # 股息率（需要 current_price）
        dividend = data.get("dividend")
        cash_div = None
        if dividend is not None and not dividend.empty:
            cash_div = dividend.iloc[0].get("cash_div")
            if cash_div:
                try:
                    kpis["cash_div"] = f"{float(cash_div):.2f}元"
                except (ValueError, TypeError):
                    kpis["cash_div"] = "--"

        if kpis.get("cash_div", "--") != "--" and kpis.get("current_price", "--") != "--":
            try:
                cd_val = float(str(kpis["cash_div"]).replace("元", ""))
                price_val = float(kpis["current_price"])
                if price_val > 0:
                    kpis["div_yield"] = f"{cd_val / price_val * 100:.2f}%"
            except (ValueError, TypeError):
                kpis["div_yield"] = "--"

        return kpis

    def get_available_sources(self) -> list[str]:
        return self.adapter.get_available_sources()

    @property
    def active_source(self) -> str:
        return self.adapter.active_source
