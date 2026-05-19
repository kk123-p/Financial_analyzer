"""图表 API — Plotly JSON / matplotlib PNG"""
import io
import logging
from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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


@router.get("/candlestick")
async def chart_candlestick(request: Request, days: int = Query(120)):
    session = _get_session(request)
    df = _get_daily(session)
    if df is None:
        return _empty_chart()

    df = df.tail(days).copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=[0.7, 0.3],
    )

    # K线
    fig.add_trace(go.Candlestick(
        x=df["trade_date"],
        open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        name="K线",
        increasing_line_color="#3FB950",
        decreasing_line_color="#F85149",
        increasing_fillcolor="#3FB950",
        decreasing_fillcolor="#F85149",
    ), row=1, col=1)

    # 均线
    for period, color in [(5, "#F85149"), (10, "#39D2C0"), (20, "#D29922")]:
        if len(df) >= period:
            df[f"ma{period}"] = df["close"].rolling(period).mean()
            fig.add_trace(go.Scatter(
                x=df["trade_date"], y=df[f"ma{period}"],
                mode="lines", name=f"MA{period}",
                line=dict(color=color, width=1),
            ), row=1, col=1)

    # 成交量
    colors = ["#3FB950" if c >= o else "#F85149"
              for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(
        x=df["trade_date"], y=df["vol"],
        name="成交量", marker_color=colors,
        opacity=0.5,
    ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#060912",
        plot_bgcolor="#0C1017",
        font=dict(color="#8B949E", size=11),
        height=500,
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=True,
        legend=dict(orientation="h", yanchor="top", y=1.12, xanchor="left", x=0),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="#21262D", zeroline=False)
    fig.update_yaxes(gridcolor="#21262D", zeroline=False)
    # 隐藏成交量 X 轴标签
    fig.update_xaxes(title_text="", row=2, col=1)

    return Response(
        content=fig.to_json(),
        media_type="application/json",
    )


@router.get("/ma")
async def chart_ma(request: Request, days: int = Query(250)):
    session = _get_session(request)
    df = _get_daily(session)
    if df is None:
        return _empty_chart()

    df = df.tail(days).copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["trade_date"], y=df["close"],
        mode="lines", name="收盘价",
        line=dict(color="#F0F6FC", width=1.5),
    ))

    for period, color in [("5", "#F85149"), ("10", "#39D2C0"),
                           ("20", "#D29922"), ("60", "#BC8CFF")]:
        ma = df["close"].rolling(int(period)).mean()
        fig.add_trace(go.Scatter(
            x=df["trade_date"], y=ma,
            mode="lines", name=f"MA{period}",
            line=dict(color=color, width=1),
        ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#060912",
        plot_bgcolor="#0C1017",
        font=dict(color="#8B949E", size=11),
        height=450,
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="#21262D", zeroline=False)
    fig.update_yaxes(gridcolor="#21262D", zeroline=False)

    return Response(content=fig.to_json(), media_type="application/json")


@router.get("/bar")
async def chart_bar(request: Request, days: int = Query(60)):
    session = _get_session(request)
    df = _get_daily(session)
    if df is None:
        return _empty_chart()

    df = df.tail(days).copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce")
    df["pct_chg"] = df["close"].pct_change() * 100 if "pct_chg" not in df.columns else df["pct_chg"]

    colors = ["#3FB950" if v >= 0 else "#F85149" for v in df["pct_chg"]]
    fig = go.Figure(go.Bar(
        x=df["trade_date"], y=df["pct_chg"],
        marker_color=colors, name="涨跌幅%",
        hovertemplate="%{x|%Y-%m-%d}<br>%{y:.2f}%<extra></extra>",
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#060912",
        plot_bgcolor="#0C1017",
        font=dict(color="#8B949E", size=11),
        height=400,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig.update_xaxes(gridcolor="#21262D", zeroline=False)
    fig.update_yaxes(gridcolor="#21262D", zeroline=True, zerolinecolor="#21262D")

    return Response(content=fig.to_json(), media_type="application/json")


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
        content='{"data":[],"layout":{"title":{"text":"无数据"}}}',
        media_type="application/json",
    )
