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
        return _empty_chart()

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
        return _empty_chart()

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
        return _empty_chart()

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


def _empty_chart():
    return Response(
        content=json.dumps({
            "title": {"text": "无数据", "left": "center", "textStyle": {"color": "#8B949E"}},
            "series": [],
        }, ensure_ascii=False),
        media_type="application/json",
    )
