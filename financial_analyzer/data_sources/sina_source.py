"""
新浪财经数据源 - 作为 Akshare (东方财富) 的备选方案
当东方财富 API 不可用时自动回退到新浪财经
"""
import pandas as pd
import requests
import json
from datetime import datetime

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Referer": "https://finance.sina.com.cn/",
}


def _to_sina_code(symbol: str) -> str:
    """转换股票代码: 600519.SH -> sh600519"""
    code = symbol.split(".")[0] if "." in symbol else symbol
    if symbol.endswith((".SH", ".SS")):
        return f"sh{code}"
    elif symbol.endswith(".SZ"):
        return f"sz{code}"
    else:
        return f"sh{code}"


def get_daily(symbol: str, start_date: str, end_date: str) -> pd.DataFrame | None:
    """获取日K线数据
    Args:
        symbol: 股票代码 (如 600519.SH)
        start_date: 开始日期 YYYYMMDD
        end_date: 结束日期 YYYYMMDD
    Returns:
        标准化 DataFrame 或 None
    """
    try:
        sina_code = _to_sina_code(symbol)
        url = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"

        sd = datetime.strptime(start_date, "%Y%m%d")
        ed = datetime.strptime(end_date, "%Y%m%d")
        days = (ed - sd).days
        datalen = min(max(int(days * 0.72), 30), 1000)

        resp = requests.get(url, params={
            "symbol": sina_code, "scale": "240", "ma": "no", "datalen": datalen
        }, headers=_HEADERS, timeout=15)

        if resp.status_code != 200 or not resp.text or resp.text == "null":
            return None

        data = json.loads(resp.text)
        if not data:
            return None

        df = pd.DataFrame(data)
        df = df.rename(columns={"day": "trade_date"})
        df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.strftime("%Y%m%d")
        df = df[(df["trade_date"] >= start_date) & (df["trade_date"] <= end_date)]
        if df.empty:
            return None

        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["vol"] = pd.to_numeric(df["volume"], errors="coerce")
        df["ts_code"] = symbol
        return df
    except Exception:
        return None


def get_basic(symbol: str) -> pd.DataFrame | None:
    """获取实时行情基本信息"""
    try:
        sina_code = _to_sina_code(symbol)
        url = f"https://hq.sinajs.cn/list={sina_code}"
        resp = requests.get(url, headers={
            **_HEADERS, "Referer": "https://finance.sina.com.cn/"
        }, timeout=10)

        if resp.status_code != 200 or not resp.text:
            return None

        raw = resp.text
        if '"' not in raw:
            return None
        parts = raw.split('"')[1].split(",")
        if len(parts) < 32:
            return None

        return pd.DataFrame([{
            "name": parts[0],
            "open": float(parts[1]),
            "pre_close": float(parts[2]),
            "close": float(parts[3]),
            "high": float(parts[4]),
            "low": float(parts[5]),
            "vol": float(parts[8]),
            "amount": float(parts[9]),
            "ts_code": symbol,
        }])
    except Exception:
        return None


def get_market_overview() -> dict | None:
    """获取大盘指数概览（上证/深证/创业板）"""
    try:
        url = "https://hq.sinajs.cn/list=sh000001,sz399001,sz399006"
        resp = requests.get(url, headers={
            **_HEADERS, "Referer": "https://finance.sina.com.cn/"
        }, timeout=10)

        if resp.status_code != 200:
            return None

        result = {}
        for line in resp.text.strip().split("\n"):
            if '"' not in line:
                continue
            code = line.split("=")[0].split("_")[-1]
            parts = line.split('"')[1].split(",")
            if len(parts) < 4:
                continue
            pre_close = float(parts[2])
            close = float(parts[3])
            result[code] = {
                "name": parts[0],
                "close": close,
                "change": close - pre_close,
                "change_pct": (close - pre_close) / pre_close * 100 if pre_close else 0,
            }
        return result
    except Exception:
        return None
