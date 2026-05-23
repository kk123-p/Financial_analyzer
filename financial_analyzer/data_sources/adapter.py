"""
统一数据适配器接口 - 支持多数据源切换、回退、数据标准化
"""
import threading

import pandas as pd
from datetime import datetime

from ..cache.manager import DataCacheManager
from ..config import YFINANCE_MAX_RETRIES, YFINANCE_RETRY_BASE_WAIT
from ..logging_config import get_logger
from .normalizer import DataNormalizer

logger = get_logger(__name__)

# 条件导入
try:
    import tushare as ts
    HAS_TUSHARE = True
except ImportError:
    HAS_TUSHARE = False

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    import akshare as ak
    HAS_AKSHARE = True
except ImportError:
    HAS_AKSHARE = False

import requests as _requests
import json as _json
import urllib3 as _urllib3
_urllib3.disable_warnings(_urllib3.exceptions.InsecureRequestWarning)
from . import sina_source


class DataSourceAdapter:
    """统一数据适配器 - 自动标准化不同数据源的返回数据"""

    def __init__(self, cache_manager: DataCacheManager = None):
        self._lock = threading.Lock()
        self.cache_manager = cache_manager or DataCacheManager()
        self.data_sources = {
            "tushare": HAS_TUSHARE,
            "yfinance": HAS_YFINANCE,
            "akshare": HAS_AKSHARE,
            "sina": True,  # 新浪财经始终可用
        }
        self._active_source = "tushare"
        self.tushare_pro = None

    @property
    def active_source(self) -> str:
        with self._lock:
            return self._active_source

    @active_source.setter
    def active_source(self, value: str):
        with self._lock:
            self._active_source = value

    def set_tushare_token(self, token: str) -> bool:
        if HAS_TUSHARE:
            with self._lock:
                self.tushare_pro = ts.pro_api(token)
            return True
        return False

    def get_available_sources(self) -> list[str]:
        with self._lock:
            return [s for s, available in self.data_sources.items() if available]

    def set_active_source(self, source: str) -> bool:
        with self._lock:
            if source in self.data_sources and self.data_sources[source]:
                self._active_source = source
                return True
        return False

    def refresh_sources(self):
        with self._lock:
            self.data_sources["tushare"] = HAS_TUSHARE
            self.data_sources["yfinance"] = HAS_YFINANCE
            self.data_sources["akshare"] = HAS_AKSHARE

    def get_stock_data(self, symbol: str, start_date: str, end_date: str,
                       data_type: str = "daily") -> pd.DataFrame | None:
        """
        获取股票数据（统一接口，自动标准化）

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            data_type: 数据类型 (daily/basic/financial/income/balance/cashflow)

        Returns:
            标准化后的 DataFrame，或 None
        """
        cache_key = self.cache_manager.get_cache_key(
            f"{data_type}_{self.active_source}", symbol, start_date, end_date
        )

        # 检查缓存
        cached_data = self.cache_manager.get_from_cache(cache_key)
        if cached_data:
            return pd.DataFrame(cached_data)

        # 从数据源获取原始数据
        raw_df, actual_source = self._fetch_raw(symbol, start_date, end_date, data_type)

        if raw_df is None or raw_df.empty:
            return None

        # 标准化（使用实际数据来源的标准化规则）
        df = self._normalize(raw_df, data_type, source=actual_source)

        if df is not None and not df.empty:
            self.cache_manager.save_to_cache(
                cache_key, data_type, symbol,
                df.to_dict("records"), start_date, end_date
            )

        return df

    def _fetch_raw(self, symbol, start_date, end_date, data_type) -> tuple:
        """从数据源获取原始数据（不做标准化），带自动回退
        Returns: (DataFrame, source_name) 或 (None, None)
        """
        df = None
        source = None

        # 线程安全地读取活跃数据源和 tushare 实例
        with self._lock:
            active = self._active_source
            tushare = self.tushare_pro
            sources = dict(self.data_sources)

        if active == "tushare" and sources.get("tushare") and tushare:
            df = self._get_tushare(symbol, start_date, end_date, data_type)
            source = "tushare"
            if df is None and HAS_AKSHARE:
                logger.info(f"Tushare 获取 {data_type} 失败，尝试 Akshare 回退")
                df = self._get_akshare(symbol, start_date, end_date, data_type)
                source = "akshare"
        elif active == "yfinance" and sources.get("yfinance"):
            df = self._get_yfinance(symbol, start_date, end_date, data_type)
            source = "yfinance"
            _cn_suffixes = (".SH", ".SZ", ".SS", ".BJ", ".HK")
            if df is None and sources.get("akshare") and not symbol.endswith(_cn_suffixes):
                logger.info(f"Yahoo Finance 失败，尝试 Akshare 回退获取 {symbol}")
                df = self._get_akshare_us(symbol, start_date, end_date, data_type)
                source = "akshare"
        elif active == "akshare" and sources.get("akshare"):
            df = self._get_akshare(symbol, start_date, end_date, data_type)
            source = "akshare"
            if df is None:
                logger.info(f"Akshare 获取 {data_type} 失败，回退到新浪财经")
                if data_type == "daily":
                    df = sina_source.get_daily(symbol, start_date, end_date)
                elif data_type == "basic":
                    df = sina_source.get_basic(symbol)
                elif data_type in ("income", "balance", "cashflow"):
                    df = self._get_em_datacenter(symbol, data_type)
                if df is not None:
                    source = "sina" if data_type in ("daily", "basic") else "em_datacenter"
        elif active == "sina":
            if data_type == "daily":
                df = sina_source.get_daily(symbol, start_date, end_date)
            elif data_type == "basic":
                df = sina_source.get_basic(symbol)
            elif data_type in ("income", "balance", "cashflow"):
                df = self._get_em_datacenter(symbol, data_type)
            source = "sina"

        return df, source

    def _normalize(self, df: pd.DataFrame, data_type: str, source: str = None) -> pd.DataFrame:
        """根据数据类型调用对应的标准化方法，并统一按日期降序排列"""
        if source is None:
            source = self.active_source

        if data_type == "daily":
            df = DataNormalizer.normalize_daily(df, source)
        elif data_type == "basic":
            df = DataNormalizer.normalize_basic(df, source)
        elif data_type == "financial":
            df = DataNormalizer.normalize_financial(df, source)
        elif data_type == "income":
            df = DataNormalizer.normalize_income(df, source)
        elif data_type == "balance":
            df = DataNormalizer.normalize_balance(df, source)
        elif data_type == "cashflow":
            df = DataNormalizer.normalize_cashflow(df, source)
        elif data_type in ("moneyflow", "margin", "margin_detail", "hk_hold",
                           "block_trade", "weekly", "monthly", "stk_holdernumber",
                           "dividend", "top10_holders", "top10_floatholders",
                           "fina_audit", "fina_mainbz"):
            df = DataNormalizer.normalize_market(df, data_type)

        # 统一排序：财务报表类按 end_date 降序，行情类已在 normalizer 中排序
        if df is not None and not df.empty:
            if data_type in ("income", "balance", "cashflow", "financial"):
                date_col = "end_date" if "end_date" in df.columns else (
                    "f_ann_date" if "f_ann_date" in df.columns else None)
                if date_col:
                    df = df.sort_values(date_col, ascending=False).reset_index(drop=True)

        return df

    # ======================== Tushare ========================
    def _get_tushare(self, symbol, start_date, end_date, data_type):
        try:
            if data_type == "daily":
                return self.tushare_pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "basic":
                return self.tushare_pro.daily_basic(
                    ts_code=symbol, start_date=start_date, end_date=end_date,
                    fields="ts_code,trade_date,close,turnover_rate,volume_ratio,pe,pe_ttm,pb,ps,total_mv,circ_mv,total_share,float_share"
                )
            elif data_type == "stock_basic":
                return self.tushare_pro.stock_basic(
                    ts_code=symbol,
                    fields='ts_code,name,industry,market,list_date'
                )
            elif data_type == "financial":
                return self.tushare_pro.fina_indicator(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "income":
                return self.tushare_pro.income(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "balance":
                return self.tushare_pro.balancesheet(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "cashflow":
                return self.tushare_pro.cashflow(ts_code=symbol, start_date=start_date, end_date=end_date)
            # ---- NEW: Market data (Phase 1) ----
            elif data_type == "moneyflow":
                return self.tushare_pro.moneyflow(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "margin":
                return self.tushare_pro.margin(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "margin_detail":
                return self.tushare_pro.margin_detail(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "hk_hold":
                return self.tushare_pro.hk_hold(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "block_trade":
                return self.tushare_pro.block_trade(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "weekly":
                return self.tushare_pro.weekly(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "monthly":
                return self.tushare_pro.monthly(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "stk_holdernumber":
                return self.tushare_pro.stk_holdernumber(ts_code=symbol, start_date=start_date, end_date=end_date)
            # ---- NEW: Financial data ----
            elif data_type == "dividend":
                return self.tushare_pro.dividend(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "top10_holders":
                return self.tushare_pro.top10_holders(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "top10_floatholders":
                return self.tushare_pro.top10_floatholders(ts_code=symbol, start_date=start_date, end_date=end_date)
            # ---- FIX: pre-existing types missing Tushare handler ----
            elif data_type == "fina_audit":
                return self.tushare_pro.fina_audit(ts_code=symbol, start_date=start_date, end_date=end_date)
            elif data_type == "fina_mainbz":
                return self.tushare_pro.fina_mainbz(ts_code=symbol, start_date=start_date, end_date=end_date, type='P')
            return None
        except Exception as e:
            logger.error(f"Tushare 数据获取失败: {e}")
            return None

    # ======================== Yahoo Finance ========================
    def _get_yfinance(self, symbol, start_date, end_date, data_type):
        import time
        try:
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")

            # 重试机制（应对限流）
            for attempt in range(YFINANCE_MAX_RETRIES):
                try:
                    ticker = yf.Ticker(symbol)

                    if data_type == "daily":
                        df = ticker.history(start=start_dt, end=end_dt)
                        if df.empty:
                            return None
                        df = df.reset_index()
                        df["ts_code"] = symbol
                        return df

                    elif data_type == "basic":
                        info = ticker.info
                        return pd.DataFrame([info])

                    elif data_type in ("financial", "income"):
                        df = ticker.financials
                        if df is not None and not df.empty:
                            df = df.T.reset_index()
                            df["ts_code"] = symbol
                            return df
                        return None

                    elif data_type == "balance":
                        df = ticker.balance_sheet
                        if df is not None and not df.empty:
                            df = df.T.reset_index()
                            df["ts_code"] = symbol
                            return df
                        return None

                    elif data_type == "cashflow":
                        df = ticker.cashflow
                        if df is not None and not df.empty:
                            df = df.T.reset_index()
                            df["ts_code"] = symbol
                            return df
                        return None

                    return None

                except Exception as e:
                    err_str = str(e).lower()
                    if "rate" in err_str or "limit" in err_str or "429" in err_str:
                        wait = (attempt + 1) * YFINANCE_RETRY_BASE_WAIT
                        logger.warning(f"Yahoo Finance 限流，{wait}秒后重试（{attempt+1}/{YFINANCE_MAX_RETRIES}）")
                        time.sleep(wait)
                        continue
                    if "connection" in err_str or "remote" in err_str or "timeout" in err_str:
                        if attempt < YFINANCE_MAX_RETRIES - 1:
                            wait = (attempt + 1) * 3
                            logger.warning(f"Yahoo Finance 连接异常，{wait}秒后重试（{attempt+1}/{YFINANCE_MAX_RETRIES}）")
                            time.sleep(wait)
                            continue
                    raise

            logger.error(f"Yahoo Finance 重试 {YFINANCE_MAX_RETRIES} 次后仍被限流")
            return None

        except Exception as e:
            logger.error(f"Yahoo Finance 数据获取失败: {e}")
            return None

    # ======================== Akshare ========================
    def _get_akshare(self, symbol, start_date, end_date, data_type):
        import time
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return self._get_akshare_inner(symbol, start_date, end_date, data_type)
            except Exception as e:
                err_str = str(e).lower()
                if "connection" in err_str or "remote" in err_str or "timeout" in err_str:
                    if attempt < max_retries - 1:
                        wait = (attempt + 1) * 2
                        logger.warning(f"Akshare 连接异常，{wait}秒后重试（{attempt+1}/{max_retries}）")
                        time.sleep(wait)
                        continue
                logger.error(f"Akshare 数据获取失败: {e}")
                return None
        return None

    def _get_akshare_inner(self, symbol, start_date, end_date, data_type):
        try:
            if data_type == "daily":
                code = symbol.replace(".SH", "").replace(".SZ", "")
                df = ak.stock_zh_a_hist(
                    symbol=code, period="daily",
                    start_date=start_date, end_date=end_date, adjust="qfq"
                )
                if df.empty:
                    return None
                df["ts_code"] = symbol
                return df

            elif data_type == "basic":
                code = symbol.replace(".SH", "").replace(".SZ", "")
                df = ak.stock_individual_info_em(symbol=code)
                if df.empty:
                    return None
                return df

            elif data_type == "financial":
                code = symbol.replace(".SH", "").replace(".SZ", "")
                try:
                    df = ak.stock_financial_analysis_indicator(symbol=code, start_year="2020")
                    if df is not None and not df.empty:
                        df["ts_code"] = symbol
                        return df
                except Exception as e:
                    logger.debug(f"stock_financial_analysis_indicator 失败: {e}")
                return None

            elif data_type in ("income", "balance", "cashflow"):
                code = symbol.replace(".SH", "").replace(".SZ", "")
                table_map = {"income": "利润表", "balance": "资产负债表", "cashflow": "现金流量表"}
                try:
                    df = ak.stock_financial_report_sina(stock=code, symbol=table_map[data_type])
                    if df is not None and not df.empty:
                        df["ts_code"] = symbol
                        return df
                except Exception as e:
                    logger.debug(f"stock_financial_report_sina {data_type} 失败: {e}")
                return None

            return None
        except Exception as e:
            logger.error(f"Akshare 数据获取失败: {e}")
            return None

    def _get_akshare_us(self, symbol, start_date, end_date, data_type):
        """用 Akshare 获取美股数据（Yahoo Finance 的回退方案）"""
        try:
            if data_type != "daily":
                return None
            # Akshare 美股接口 - 提取纯代码
            code = symbol.split(".")[0] if "." in symbol else symbol
            code = code.replace(".N", "").replace(".O", "")
            try:
                df = ak.stock_us_daily(symbol=code, adjust="qfq")
            except IndexError:
                # Akshare 返回空数据时可能抛出 IndexError
                logger.warning(f"Akshare 美股接口返回空数据: {code}")
                return None
            if df is None or df.empty:
                return None
            # 筛选日期范围
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
                start_dt = datetime.strptime(start_date, "%Y%m%d")
                end_dt = datetime.strptime(end_date, "%Y%m%d")
                df = df[(df["date"] >= start_dt) & (df["date"] <= end_dt)]
            df["ts_code"] = symbol
            return df
        except Exception as e:
            logger.error(f"Akshare 美股数据获取失败: {e}")
            return None

    # ======================== 东方财富 datacenter-web (财务报表) ========================
    _EM_DC_REPORTS = {
        "income": "RPT_F10_FINANCE_GINCOME",
        "balance": "RPT_F10_FINANCE_GBALANCE",
        "cashflow": "RPT_F10_FINANCE_GCASHFLOW",
    }

    def _get_em_datacenter(self, symbol: str, data_type: str) -> pd.DataFrame | None:
        """通过 datacenter-web.eastmoney.com 获取财务报表（不受 push2his 封锁影响）"""
        report = self._EM_DC_REPORTS.get(data_type)
        if not report:
            return None
        try:
            code = symbol.split(".")[0] if "." in symbol else symbol
            resp = _requests.get(
                "https://datacenter-web.eastmoney.com/api/data/v1/get",
                params={
                    "reportName": report,
                    "columns": "ALL",
                    "filter": f'(SECURITY_CODE="{code}")',
                    "pageSize": "50",
                    "sortTypes": "-1",
                    "sortColumns": "REPORT_DATE",
                },
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                timeout=15,
            )
            data = resp.json()
            if not data.get("success"):
                return None
            rows = data.get("result", {}).get("data", [])
            if not rows:
                return None
            df = pd.DataFrame(rows)
            df["ts_code"] = symbol
            logger.info(f"datacenter-web 获取 {symbol} {data_type} 成功: {len(df)} 行")
            return df
        except Exception as e:
            logger.error(f"datacenter-web 获取 {data_type} 失败: {e}")
            return None

    # ======================== 行业数据 ========================
    def get_industry_stocks_from_api(self, industry: str) -> list[list] | None:
        """从 API 获取行业股票列表"""
        try:
            if HAS_TUSHARE and self.tushare_pro:
                df = self.tushare_pro.stock_basic(
                    exchange="", list_status="L",
                    fields="ts_code,name,industry,market"
                )
                if df is not None and not df.empty:
                    industry_df = df[df["industry"] == industry]
                    if not industry_df.empty:
                        return [
                            [row.get("ts_code", ""), row.get("name", ""),
                             row.get("market", ""), "-", "-"]
                            for _, row in industry_df.head(50).iterrows()
                        ]
        except Exception as e:
            logger.error(f"获取行业股票列表失败: {e}")

        try:
            if HAS_AKSHARE:
                df = ak.stock_board_industry_name_em()
                if df is not None and not df.empty:
                    matched = df[df["板块名称"].str.contains(industry, na=False)]
                    if not matched.empty:
                        cons_df = ak.stock_board_industry_cons_em(symbol=matched.iloc[0]["板块名称"])
                        if cons_df is not None and not cons_df.empty:
                            return [
                                [str(row.get("代码", "")), str(row.get("名称", "")),
                                 str(row.get("最新价", "")), str(row.get("涨跌幅", "")),
                                 str(row.get("总市值", ""))]
                                for _, row in cons_df.head(50).iterrows()
                            ]
        except Exception as e:
            logger.error(f"Akshare 获取行业股票失败: {e}")

        return None
