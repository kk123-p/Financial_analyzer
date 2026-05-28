"""图表 API — ECharts JSON / matplotlib PNG"""
import io
import json
import logging
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, Request, Query
from fastapi.responses import Response

from .data_api import _get_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chart", tags=["charts"])


def _get_daily(session: dict) -> pd.DataFrame | None:
    """从 session 获取 daily 数据"""
    data = session.get("data", {})
    daily_records = data.get("daily", [])
    if not daily_records:
        return None
    return pd.DataFrame(daily_records)


def _safe_float(v):
    """安全转换为 float，NaN/None 返回 None"""
    if v is None:
        return None
    try:
        f = float(v)
        return None if np.isnan(f) else round(f, 4)
    except (ValueError, TypeError):
        return None


@router.get("/candlestick")
async def chart_candlestick(request: Request, days: int = Query(120)):
    """K线图 + 成交量 — 返回 ECharts option JSON"""
    session = _get_session(request)
    df = _get_daily(session)
    if df is None:
        return _empty_chart("请先获取数据")

    df = df.tail(days).copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    dates = df["trade_date"].dt.strftime("%Y-%m-%d").tolist()

    # K线数据 [open, close, low, high]
    candle_data = []
    for _, row in df.iterrows():
        candle_data.append([
            _safe_float(row.get("open")),
            _safe_float(row.get("close")),
            _safe_float(row.get("low")),
            _safe_float(row.get("high")),
        ])

    # 均线
    ma_series = {}
    for period, color in [(5, "#F85149"), (10, "#39D2C0"), (20, "#D29922")]:
        if len(df) >= period:
            ma = df["close"].rolling(period).mean()
            ma_series[period] = {
                "values": [_safe_float(v) for v in ma.tolist()],
                "color": color,
            }

    # 成交量颜色
    vol_colors = []
    for _, row in df.iterrows():
        c, o = row.get("close", 0), row.get("open", 0)
        vol_colors.append("#3FB950" if c >= o else "#F85149")

    vol_data = [_safe_float(v) for v in df.get("vol", df.get("volume", pd.Series(dtype=float))).tolist()]

    # 构建 ECharts option
    series = [
        {
            "name": "K线",
            "type": "candlestick",
            "xAxisIndex": 0,
            "yAxisIndex": 0,
            "data": candle_data,
            "itemStyle": {
                "color": "#3FB950",
                "color0": "#F85149",
                "borderColor": "#3FB950",
                "borderColor0": "#F85149",
            },
        },
    ]

    for period, info in ma_series.items():
        series.append({
            "name": f"MA{period}",
            "type": "line",
            "xAxisIndex": 0,
            "yAxisIndex": 0,
            "data": info["values"],
            "smooth": True,
            "symbol": "none",
            "lineStyle": {"color": info["color"], "width": 1},
        })

    series.append({
        "name": "成交量",
        "type": "bar",
        "xAxisIndex": 1,
        "yAxisIndex": 1,
        "data": vol_data,
        "itemStyle": {"color": vol_colors, "opacity": 0.5},
    })

    option = {
        "animation": False,
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"},
            "backgroundColor": "rgba(13,17,23,0.92)",
            "borderColor": "#30363D",
            "textStyle": {"color": "#E6EDF3", "fontSize": 12},
        },
        "legend": {
            "data": ["K线", "MA5", "MA10", "MA20", "成交量"],
            "textStyle": {"color": "#8B949E"},
            "top": 0,
            "left": 0,
        },
        "axisPointer": {
            "link": [{"xAxisIndex": "all"}],
        },
        "grid": [
            {"left": 50, "right": 10, "top": 30, "height": "55%"},
            {"left": 50, "right": 10, "top": "75%", "height": "16%"},
        ],
        "xAxis": [
            {
                "type": "category",
                "data": dates,
                "gridIndex": 0,
                "axisLine": {"lineStyle": {"color": "#30363D"}},
                "splitLine": {"show": False},
                "axisLabel": {"color": "#8B949E"},
                "boundaryGap": True,
            },
            {
                "type": "category",
                "data": dates,
                "gridIndex": 1,
                "axisLine": {"lineStyle": {"color": "#30363D"}},
                "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "boundaryGap": True,
            },
        ],
        "yAxis": [
            {
                "scale": True,
                "gridIndex": 0,
                "splitArea": {"show": False},
                "axisLine": {"lineStyle": {"color": "#30363D"}},
                "splitLine": {"lineStyle": {"color": "#21262D"}},
                "axisLabel": {"color": "#8B949E"},
            },
            {
                "scale": True,
                "gridIndex": 1,
                "splitNumber": 2,
                "axisLine": {"lineStyle": {"color": "#30363D"}},
                "splitLine": {"lineStyle": {"color": "#21262D"}},
                "axisLabel": {"color": "#8B949E"},
            },
        ],
        "dataZoom": [
            {
                "type": "inside",
                "xAxisIndex": [0, 1],
                "start": 50,
                "end": 100,
            },
            {
                "type": "slider",
                "xAxisIndex": [0, 1],
                "top": "93%",
                "height": 16,
                "start": 50,
                "end": 100,
                "borderColor": "#30363D",
                "backgroundColor": "#060912",
                "fillerColor": "rgba(63,185,80,0.15)",
                "handleStyle": {"color": "#3FB950"},
                "textStyle": {"color": "#8B949E"},
            },
        ],
        "series": series,
    }

    return Response(
        content=json.dumps(option, ensure_ascii=False),
        media_type="application/json",
    )


@router.get("/ma")
async def chart_ma(request: Request, days: int = Query(250)):
    """均线图 — 返回 ECharts option JSON"""
    session = _get_session(request)
    df = _get_daily(session)
    if df is None:
        return _empty_chart("请先获取数据")

    df = df.tail(days).copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    dates = df["trade_date"].dt.strftime("%Y-%m-%d").tolist()
    close_data = [_safe_float(v) for v in df["close"].tolist()]

    series = [
        {
            "name": "收盘价",
            "type": "line",
            "data": close_data,
            "symbol": "none",
            "lineStyle": {"color": "#F0F6FC", "width": 1.5},
        },
    ]

    for period, color in [("5", "#F85149"), ("10", "#39D2C0"),
                           ("20", "#D29922"), ("60", "#BC8CFF")]:
        ma = df["close"].rolling(int(period)).mean()
        series.append({
            "name": f"MA{period}",
            "type": "line",
            "data": [_safe_float(v) for v in ma.tolist()],
            "smooth": True,
            "symbol": "none",
            "lineStyle": {"color": color, "width": 1},
        })

    option = {
        "animation": False,
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(13,17,23,0.92)",
            "borderColor": "#30363D",
            "textStyle": {"color": "#E6EDF3", "fontSize": 12},
        },
        "legend": {
            "data": ["收盘价", "MA5", "MA10", "MA20", "MA60"],
            "textStyle": {"color": "#8B949E"},
            "top": 0,
            "left": 0,
        },
        "grid": {"left": 50, "right": 10, "top": 35, "bottom": 50},
        "xAxis": {
            "type": "category",
            "data": dates,
            "axisLine": {"lineStyle": {"color": "#30363D"}},
            "splitLine": {"show": False},
            "axisLabel": {"color": "#8B949E"},
        },
        "yAxis": {
            "scale": True,
            "axisLine": {"lineStyle": {"color": "#30363D"}},
            "splitLine": {"lineStyle": {"color": "#21262D"}},
            "axisLabel": {"color": "#8B949E"},
        },
        "dataZoom": [
            {
                "type": "inside",
                "start": 0,
                "end": 100,
            },
            {
                "type": "slider",
                "top": "90%",
                "height": 16,
                "start": 0,
                "end": 100,
                "borderColor": "#30363D",
                "backgroundColor": "#060912",
                "fillerColor": "rgba(57,210,192,0.15)",
                "handleStyle": {"color": "#39D2C0"},
                "textStyle": {"color": "#8B949E"},
            },
        ],
        "series": series,
    }

    return Response(
        content=json.dumps(option, ensure_ascii=False),
        media_type="application/json",
    )


@router.get("/bar")
async def chart_bar(request: Request, days: int = Query(60)):
    """涨跌幅柱状图 — 返回 ECharts option JSON"""
    session = _get_session(request)
    df = _get_daily(session)
    if df is None:
        return _empty_chart("请先获取数据")

    df = df.tail(days).copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")

    if "pct_chg" not in df.columns:
        df["pct_chg"] = df["close"].pct_change() * 100
    df["pct_chg"] = df["pct_chg"].fillna(0)

    dates = df["trade_date"].dt.strftime("%Y-%m-%d").tolist()
    pct_data = []
    bar_colors = []
    for v in df["pct_chg"]:
        fv = _safe_float(v)
        pct_data.append(fv if fv is not None else 0)
        bar_colors.append("#3FB950" if (fv or 0) >= 0 else "#F85149")

    option = {
        "animation": False,
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(13,17,23,0.92)",
            "borderColor": "#30363D",
            "textStyle": {"color": "#E6EDF3", "fontSize": 12},
        },
        "grid": {"left": 50, "right": 10, "top": 20, "bottom": 50},
        "xAxis": {
            "type": "category",
            "data": dates,
            "axisLine": {"lineStyle": {"color": "#30363D"}},
            "splitLine": {"show": False},
            "axisLabel": {"color": "#8B949E"},
        },
        "yAxis": {
            "type": "value",
            "axisLine": {"lineStyle": {"color": "#30363D"}},
            "splitLine": {"lineStyle": {"color": "#21262D"}},
            "axisLabel": {"color": "#8B949E"},
        },
        "dataZoom": [
            {
                "type": "inside",
                "start": 0,
                "end": 100,
            },
        ],
        "series": [
            {
                "name": "涨跌幅%",
                "type": "bar",
                "data": pct_data,
                "itemStyle": {"color": bar_colors},
            },
        ],
    }

    return Response(
        content=json.dumps(option, ensure_ascii=False),
        media_type="application/json",
    )


@router.get("/dupont_waterfall")
async def chart_dupont_waterfall(request: Request):
    """杜邦瀑布图 — ECharts waterfall bar chart"""
    from financial_analyzer.ai.report_builder import ReportBuilder

    session = _get_session(request)
    data = session.get("data", {})
    stock_code = session.get("stock_code", "")
    if not data:
        return _empty_chart("请先获取数据")

    try:
        report = ReportBuilder.build(data, stock_code)
        three_factor = report.get("dupont_analysis", {}).get("three_factor", [])
        if len(three_factor) < 2:
            return _empty_chart("财务数据不足，需要至少2期数据")

        new_p, old_p = three_factor[0], three_factor[1]
        old_nm = float(old_p["net_margin"])
        new_nm = float(new_p["net_margin"])
        old_at = float(old_p["asset_turnover"])
        new_at = float(new_p["asset_turnover"])
        old_em = float(old_p["equity_multiplier"])
        new_em = float(new_p["equity_multiplier"])

        old_roe = old_nm * old_at * old_em
        step1 = new_nm * old_at * old_em
        step2 = new_nm * new_at * old_em
        new_roe = new_nm * new_at * new_em

        nm_contrib = step1 - old_roe
        at_contrib = step2 - step1
        em_contrib = new_roe - step2

        categories = [
            f"ROE({old_p['end_date']})",
            "净利率贡献",
            "周转率贡献",
            "杠杆贡献",
            f"ROE({new_p['end_date']})",
        ]

        # Transparent base bars for waterfall positioning
        base_vals = [0, old_roe, old_roe + nm_contrib,
                     old_roe + nm_contrib + at_contrib, 0]

        # Visible bars
        bar_vals = [old_roe, nm_contrib, at_contrib, em_contrib, new_roe]

        def _bar_color(idx, val):
            if idx in (0, 4):
                return "#D29922"
            return "#3FB950" if val >= 0 else "#F85149"

        bar_colors = [_bar_color(i, v) for i, v in enumerate(bar_vals)]

        def _label_fmt(idx, val):
            if idx in (0, 4):
                return f"{val:.2f}%"
            return f"+{val:.2f}pp" if val >= 0 else f"{val:.2f}pp"

        option = {
            "animation": False,
            "tooltip": {
                "trigger": "axis",
                "backgroundColor": "rgba(13,17,23,0.92)",
                "borderColor": "#30363D",
                "textStyle": {"color": "#E6EDF3", "fontSize": 12},
                "formatter": "{b}",
            },
            "grid": {"left": 60, "right": 30, "top": 40, "bottom": 50},
            "xAxis": {
                "type": "category",
                "data": categories,
                "axisLine": {"lineStyle": {"color": "#30363D"}},
                "axisLabel": {"color": "#8B949E", "rotate": 0},
            },
            "yAxis": {
                "type": "value",
                "axisLine": {"lineStyle": {"color": "#30363D"}},
                "splitLine": {"lineStyle": {"color": "#21262D"}},
                "axisLabel": {"color": "#8B949E", "formatter": "{value}%"},
            },
            "series": [
                {
                    "name": "base",
                    "type": "bar",
                    "stack": "waterfall",
                    "itemStyle": {
                        "color": "transparent",
                        "borderColor": "transparent",
                    },
                    "emphasis": {"itemStyle": {"color": "transparent", "borderColor": "transparent"}},
                    "data": base_vals,
                },
                {
                    "name": "value",
                    "type": "bar",
                    "stack": "waterfall",
                    "data": [
                        {
                            "value": round(v, 4),
                            "itemStyle": {"color": bar_colors[i]},
                            "label": {
                                "show": True,
                                "position": "top" if i in (0, 4) or v >= 0 else "bottom",
                                "formatter": _label_fmt(i, v),
                                "color": "#E6EDF3",
                                "fontSize": 11,
                            },
                        }
                        for i, v in enumerate(bar_vals)
                    ],
                },
            ],
        }

        return Response(
            content=json.dumps(option, ensure_ascii=False),
            media_type="application/json",
        )
    except Exception as e:
        logger.error(f"Dupont waterfall chart failed: {e}")
        return _empty_chart("图表渲染失败")


@router.get("/valuation_dashboard")
async def chart_valuation_dashboard(request: Request):
    """估值仪表盘 — PE/PB 双 gauge"""
    from financial_analyzer.ai.report_builder import ReportBuilder

    session = _get_session(request)
    data = session.get("data", {})
    stock_code = session.get("stock_code", "")
    if not data:
        return _empty_chart("请先获取数据")

    try:
        report = ReportBuilder.build(data, stock_code)
        valuation = report.get("valuation", {})
        pe_pct = valuation.get("pe_percentile", {})
        pb_pct = valuation.get("pb_percentile", {})
        snap = report.get("company_snapshot", {})

        if not pe_pct and not pb_pct:
            return _empty_chart("估值数据不足，需要更长的历史数据")

        pe_current = pe_pct.get("current", 0) or 0
        pe_percentile = pe_pct.get("percentile", 50) or 50
        pe_avg = pe_pct.get("avg", 0) or 0

        pb_current = pb_pct.get("current", 0) or 0
        pb_percentile = pb_pct.get("percentile", 50) or 50
        pb_avg = pb_pct.get("avg", 0) or 0

        def _gauge_axisline():
            return {
                "lineStyle": {
                    "width": 20,
                    "color": [
                        [0.3, "#3FB950"],
                        [0.7, "#D29922"],
                        [1, "#F85149"],
                    ],
                },
            }

        def _gauge_series(name, value, percentile, avg_val, center_x):
            return {
                "name": name,
                "type": "gauge",
                "center": [center_x, "55%"],
                "radius": "80%",
                "min": 0,
                "max": 100,
                "splitNumber": 10,
                "axisLine": _gauge_axisline(),
                "axisTick": {"show": False},
                "splitLine": {"length": 8, "lineStyle": {"color": "#30363D"}},
                "axisLabel": {"color": "#8B949E", "fontSize": 10, "distance": 16},
                "pointer": {
                    "length": "60%",
                    "width": 4,
                    "itemStyle": {"color": "#E6EDF3"},
                },
                "anchor": {"show": True, "size": 8, "itemStyle": {"color": "#E6EDF3"}},
                "title": {
                    "show": True,
                    "offsetCenter": [0, "75%"],
                    "color": "#E6EDF3",
                    "fontSize": 14,
                    "fontWeight": "bold",
                },
                "detail": {
                    "valueAnimation": False,
                    "color": "#E6EDF3",
                    "fontSize": 20,
                    "fontWeight": "bold",
                    "offsetCenter": [0, "45%"],
                    "formatter": "{value}%",
                },
                "data": [{
                    "value": round(float(percentile), 1),
                    "name": f"{name}\n当前: {value:.2f}  均值: {avg_val:.2f}",
                }],
            }

        option = {
            "animation": False,
            "tooltip": {"show": False},
            "series": [
                _gauge_series("PE", pe_current, pe_percentile, pe_avg, "25%"),
                _gauge_series("PB", pb_current, pb_percentile, pb_avg, "75%"),
            ],
        }

        return Response(
            content=json.dumps(option, ensure_ascii=False),
            media_type="application/json",
        )
    except Exception as e:
        logger.error(f"Valuation dashboard chart failed: {e}")
        return _empty_chart("图表渲染失败")


@router.get("/tech_panel")
async def chart_tech_panel(request: Request, days: int = Query(120)):
    """技术指标多面板 — MACD / RSI / KDJ"""
    session = _get_session(request)
    df = _get_daily(session)
    if df is None:
        return _empty_chart("请先获取数据")

    days = min(max(days, 30), 500)
    df = df.tail(days).copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df = df.sort_values("trade_date").reset_index(drop=True)
    dates = df["trade_date"].dt.strftime("%Y-%m-%d").tolist()

    close = df["close"].astype(float)
    high = df["high"].astype(float)
    low = df["low"].astype(float)

    # --- MACD ---
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False).mean()
    macd_bar = (dif - dea) * 2

    # --- RSI(14) ---
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(span=14, adjust=False).mean()
    avg_loss = loss.ewm(span=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)

    # --- KDJ(9,3,3) ---
    low9 = low.rolling(9).min()
    high9 = high.rolling(9).max()
    rsv = (close - low9) / (high9 - low9).replace(0, np.nan) * 100
    k_val = rsv.ewm(com=2, adjust=False).mean()  # SMA(RSV,3) ≈ EWM(com=2)
    d_val = k_val.ewm(com=2, adjust=False).mean()
    j_val = 3 * k_val - 2 * d_val

    # --- MA lines ---
    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()

    close_data = [_safe_float(v) for v in close.tolist()]
    ma5_data = [_safe_float(v) for v in ma5.tolist()]
    ma10_data = [_safe_float(v) for v in ma10.tolist()]
    ma20_data = [_safe_float(v) for v in ma20.tolist()]

    dif_data = [_safe_float(v) for v in dif.tolist()]
    dea_data = [_safe_float(v) for v in dea.tolist()]
    macd_data = []
    for v in macd_bar.tolist():
        fv = _safe_float(v)
        macd_data.append({
            "value": fv if fv is not None else 0,
            "itemStyle": {"color": "#3FB950" if (fv or 0) >= 0 else "#F85149"},
        })

    rsi_data = [_safe_float(v) for v in rsi.tolist()]
    k_data = [_safe_float(v) for v in k_val.tolist()]
    d_data = [_safe_float(v) for v in d_val.tolist()]
    j_data = [_safe_float(v) for v in j_val.tolist()]

    grid_style = {
        "axisLine": {"lineStyle": {"color": "#30363D"}},
        "splitLine": {"lineStyle": {"color": "#21262D"}},
        "axisLabel": {"color": "#8B949E"},
    }
    xaxis_style = {
        "axisLine": {"lineStyle": {"color": "#30363D"}},
        "splitLine": {"show": False},
        "axisLabel": {"color": "#8B949E"},
    }

    option = {
        "animation": False,
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross", "link": [{"xAxisIndex": "all"}]},
            "backgroundColor": "rgba(13,17,23,0.92)",
            "borderColor": "#30363D",
            "textStyle": {"color": "#E6EDF3", "fontSize": 12},
        },
        "legend": {
            "data": ["收盘价", "MA5", "MA10", "MA20", "DIF", "DEA", "MACD", "RSI", "K", "D", "J"],
            "textStyle": {"color": "#8B949E"},
            "top": 0,
            "left": 0,
            "type": "scroll",
        },
        "axisPointer": {"link": [{"xAxisIndex": "all"}]},
        "grid": [
            {"left": 55, "right": 15, "top": 35, "height": "28%"},
            {"left": 55, "right": 15, "top": "40%", "height": "14%"},
            {"left": 55, "right": 15, "top": "58%", "height": "14%"},
            {"left": 55, "right": 15, "top": "76%", "height": "14%"},
        ],
        "xAxis": [
            {**{"type": "category", "data": dates, "gridIndex": 0, "boundaryGap": True, "axisLabel": {"show": False}}, **xaxis_style},
            {**{"type": "category", "data": dates, "gridIndex": 1, "boundaryGap": True, "axisLabel": {"show": False}}, **xaxis_style},
            {**{"type": "category", "data": dates, "gridIndex": 2, "boundaryGap": True, "axisLabel": {"show": False}}, **xaxis_style},
            {**{"type": "category", "data": dates, "gridIndex": 3, "boundaryGap": True}, **xaxis_style},
        ],
        "yAxis": [
            {**{"scale": True, "gridIndex": 0, "splitNumber": 4}, **grid_style},
            {**{"scale": True, "gridIndex": 1, "splitNumber": 3}, **grid_style},
            {**{"scale": True, "gridIndex": 2, "splitNumber": 3, "min": 0, "max": 100}, **grid_style},
            {**{"scale": True, "gridIndex": 3, "splitNumber": 3}, **grid_style},
        ],
        "dataZoom": [
            {
                "type": "inside",
                "xAxisIndex": [0, 1, 2, 3],
                "start": 50,
                "end": 100,
            },
            {
                "type": "slider",
                "xAxisIndex": [0, 1, 2, 3],
                "top": "93%",
                "height": 16,
                "start": 50,
                "end": 100,
                "borderColor": "#30363D",
                "backgroundColor": "#060912",
                "fillerColor": "rgba(63,185,80,0.15)",
                "handleStyle": {"color": "#3FB950"},
                "textStyle": {"color": "#8B949E"},
            },
        ],
        "series": [
            {
                "name": "收盘价", "type": "line", "xAxisIndex": 0, "yAxisIndex": 0,
                "data": close_data, "symbol": "none",
                "lineStyle": {"color": "#F0F6FC", "width": 1.5},
            },
            {
                "name": "MA5", "type": "line", "xAxisIndex": 0, "yAxisIndex": 0,
                "data": ma5_data, "symbol": "none", "smooth": True,
                "lineStyle": {"color": "#F85149", "width": 1},
            },
            {
                "name": "MA10", "type": "line", "xAxisIndex": 0, "yAxisIndex": 0,
                "data": ma10_data, "symbol": "none", "smooth": True,
                "lineStyle": {"color": "#39D2C0", "width": 1},
            },
            {
                "name": "MA20", "type": "line", "xAxisIndex": 0, "yAxisIndex": 0,
                "data": ma20_data, "symbol": "none", "smooth": True,
                "lineStyle": {"color": "#D29922", "width": 1},
            },
            {
                "name": "DIF", "type": "line", "xAxisIndex": 1, "yAxisIndex": 1,
                "data": dif_data, "symbol": "none",
                "lineStyle": {"color": "#39D2C0", "width": 1},
            },
            {
                "name": "DEA", "type": "line", "xAxisIndex": 1, "yAxisIndex": 1,
                "data": dea_data, "symbol": "none",
                "lineStyle": {"color": "#D29922", "width": 1},
            },
            {
                "name": "MACD", "type": "bar", "xAxisIndex": 1, "yAxisIndex": 1,
                "data": macd_data,
            },
            {
                "name": "RSI", "type": "line", "xAxisIndex": 2, "yAxisIndex": 2,
                "data": rsi_data, "symbol": "none",
                "lineStyle": {"color": "#BC8CFF", "width": 1.5},
                "markLine": {
                    "silent": True,
                    "data": [
                        {"yAxis": 30, "lineStyle": {"color": "#3FB950", "type": "dashed", "width": 1}},
                        {"yAxis": 70, "lineStyle": {"color": "#F85149", "type": "dashed", "width": 1}},
                    ],
                    "label": {"show": False},
                },
            },
            {
                "name": "K", "type": "line", "xAxisIndex": 3, "yAxisIndex": 3,
                "data": k_data, "symbol": "none",
                "lineStyle": {"color": "#39D2C0", "width": 1},
            },
            {
                "name": "D", "type": "line", "xAxisIndex": 3, "yAxisIndex": 3,
                "data": d_data, "symbol": "none",
                "lineStyle": {"color": "#D29922", "width": 1},
            },
            {
                "name": "J", "type": "line", "xAxisIndex": 3, "yAxisIndex": 3,
                "data": j_data, "symbol": "none",
                "lineStyle": {"color": "#BC8CFF", "width": 1},
            },
        ],
    }

    return Response(
        content=json.dumps(option, ensure_ascii=False),
        media_type="application/json",
    )


@router.get("/img/{chart_type}")
async def chart_img(request: Request, chart_type: str):
    """服务端 matplotlib 渲染 PNG（瀑布图、雷达图等复杂图表）"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    session = _get_session(request)
    data_raw = session.get("data", {})
    stock_code = session.get("stock_code", "")

    if not data_raw:
        return Response(content=b"", media_type="image/png")

    data = {k: pd.DataFrame(v) for k, v in data_raw.items()}

    try:
        from financial_analyzer.charts.matplotlib_charts import (
            create_dupont_waterfall, create_fscore_radar,
            create_peer_comparison_bar, create_valuation_gauge,
        )

        fig = None
        if chart_type == "dupont":
            # 从 deep analyzer 获取数据
            from financial_analyzer.analyzers.deep_analysis import DeepAnalyzer
            from financial_analyzer.ai.report_builder import ReportBuilder
            report = ReportBuilder.build(data, stock_code)
            dupont = report.get("dupont_analysis", {}).get("three_factor", [])
            if len(dupont) >= 2:
                new, old = dupont[0], dupont[1]
                fig = create_dupont_waterfall(
                    old["net_margin"], new["net_margin"],
                    old["asset_turnover"], new["asset_turnover"],
                    old["equity_multiplier"], new["equity_multiplier"],
                    old["roe"], new["roe"], stock_code,
                )
        elif chart_type == "fscore":
            report = ReportBuilder.build(data, stock_code)
            scores = report.get("risk_models", {}).get("fscore", {}).get("details", {})
            if scores:
                fig = create_fscore_radar(scores, stock_code)

        if fig is None:
            return Response(content=b"", media_type="image/png")

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                    facecolor="#060912", edgecolor="none")
        plt.close(fig)
        buf.seek(0)
        return Response(content=buf.read(), media_type="image/png")
    except Exception as e:
        logger.error(f"Chart PNG render failed: {e}")
        return Response(content=b"", media_type="image/png")


def _empty_chart(message: str = "无数据"):
    return Response(
        content=json.dumps({
            "title": {"text": message, "left": "center", "textStyle": {"color": "#8B949E"}},
            "series": [],
        }, ensure_ascii=False),
        media_type="application/json",
    )
