"""
图表模块 - 基于 Matplotlib 的金融图表
支持 K线图、均线图、柱状图、组合图
交互功能：鼠标滚轮缩放、拖拽平移
"""
import pandas as pd
import numpy as np
from datetime import datetime

from ..logging_config import get_logger

logger = get_logger(__name__)

# 延迟导入
_mpl = None
_mpf = None


def _ensure_mpl():
    """延迟导入 matplotlib（使用 TkAgg 后端以支持交互）"""
    global _mpl, _mpf
    if _mpl is None:
        try:
            import matplotlib
            # 不在这里设置 backend，由 show_charts 在主线程中设置
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            import matplotlib.ticker as mticker
            from matplotlib.patches import FancyBboxPatch

            _setup_chinese_font(plt)

            _mpl = {
                "plt": plt,
                "mdates": mdates,
                "mticker": mticker,
                "FancyBboxPatch": FancyBboxPatch,
            }
        except ImportError:
            raise ImportError("需要 matplotlib: pip install matplotlib")

    if _mpf is None:
        try:
            import mplfinance as mpf
            _mpf = mpf
        except ImportError:
            _mpf = None
    return _mpl, _mpf


def _setup_chinese_font(plt):
    """配置 matplotlib 中文字体"""
    import matplotlib.font_manager as fm

    candidates = [
        "Microsoft YaHei UI", "Microsoft YaHei", "SimHei",
        "SimSun", "FangSong", "KaiTi",
        "WenQuanYi Micro Hei", "WenQuanYi Zen Hei",
        "Noto Sans CJK SC", "Noto Sans SC",
        "Source Han Sans SC", "PingFang SC",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    chosen = None
    for name in candidates:
        if name in available:
            chosen = name
            break

    if chosen:
        plt.rcParams["font.sans-serif"] = [chosen] + plt.rcParams.get("font.sans-serif", ["DejaVu Sans"])
        plt.rcParams["axes.unicode_minus"] = False
        logger.info(f"matplotlib 中文字体: {chosen}")
    else:
        logger.warning("未找到中文字体，图表中文可能显示为方块")
        plt.rcParams["axes.unicode_minus"] = False


# ============================================================================
# 配色方案
# ============================================================================
COLORS = {
    # 背景层级 - 深蓝黑
    "bg": "#0B0F1A",
    "card_bg": "#151D2E",
    "surface": "#111827",
    # 文字
    "text": "#F1F5F9",
    "text_muted": "#94A3B8",
    "text_dim": "#475569",
    # 网格与边框
    "grid": "#1E293B",
    "border": "#334155",
    # 涨跌色
    "up": "#22C55E",
    "down": "#EF4444",
    # 强调色
    "accent": "#3B82F6",
    "accent_hover": "#2563EB",
    "gold": "#F59E0B",
    "info": "#38BDF8",
    "purple": "#A78BFA",
    "teal": "#06B6D4",
    "pink": "#EC4899",
    # 均线色
    "ma5": "#EF4444",
    "ma10": "#06B6D4",
    "ma20": "#F59E0B",
    "ma60": "#A78BFA",
    # 图表色系（6色）
    "series_1": "#3B82F6",
    "series_2": "#22C55E",
    "series_3": "#F59E0B",
    "series_4": "#EF4444",
    "series_5": "#A78BFA",
    "series_6": "#06B6D4",
    # 柱状图
    "bar": "#3B82F6",
    "bar_alt": "#F59E0B",
}


def _apply_dark_style(fig, axes):
    """应用深色主题到图表 - Financial Dashboard 风格"""
    import matplotlib.axes as maxes

    fig.patch.set_facecolor(COLORS["bg"])

    if isinstance(axes, maxes.Axes):
        axes_list = [axes]
    else:
        axes_list = np.asarray(axes).flatten().tolist()

    for ax in axes_list:
        ax.set_facecolor(COLORS["card_bg"])
        ax.tick_params(colors=COLORS["text_muted"], labelsize=9, length=0)
        ax.xaxis.label.set_color(COLORS["text_muted"])
        ax.yaxis.label.set_color(COLORS["text_muted"])
        ax.title.set_color(COLORS["gold"])

        for spine in ax.spines.values():
            spine.set_color(COLORS["grid"])
            spine.set_linewidth(0.5)

        ax.grid(True, color=COLORS["grid"], alpha=0.4, linewidth=0.5, linestyle="-")
        ax.set_axisbelow(True)


def _format_date_axis(ax, dates, max_ticks=12):
    """格式化日期坐标轴"""
    _ensure_mpl()
    mdates = _mpl["mdates"]

    n = len(dates)
    if n == 0:
        return

    step = max(1, n // max_ticks)
    tick_positions = list(range(0, n, step))

    # 根据时间跨度选择格式
    if n > 0:
        span_days = (dates[-1] - dates[0]).days if hasattr(dates[-1], 'days') else n
        if span_days > 365 * 2:
            fmt = "%Y-%m"
        elif span_days > 180:
            fmt = "%m-%d"
        else:
            fmt = "%m-%d"
    else:
        fmt = "%m-%d"

    tick_labels = [dates[i].strftime(fmt) for i in tick_positions if i < len(dates)]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha="right", fontsize=8)


def _format_volume_axis(ax):
    """格式化成交量纵轴（万手/亿手）"""
    _ensure_mpl()
    mticker = _mpl["mticker"]

    def _fmt(v, p):
        if v >= 1e8:
            return f"{v/1e8:.1f}亿"
        elif v >= 1e4:
            return f"{v/1e4:.0f}万"
        else:
            return f"{v:.0f}"

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(_fmt))


def _format_price_axis(ax, prices):
    """格式化价格纵轴（根据价格范围选择精度）"""
    _ensure_mpl()
    mticker = _mpl["mticker"]

    price_range = max(prices) - min(prices) if len(prices) > 0 else 1
    if price_range < 1:
        fmt = "{:.3f}"
    elif price_range < 10:
        fmt = "{:.2f}"
    else:
        fmt = "{:.1f}"

    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, p: fmt.format(v)))


def _add_scroll_zoom(fig, axes_list):
    """为图表添加鼠标滚轮缩放和拖拽平移功能"""
    class ZoomPan:
        def __init__(self):
            self.press = None
            self.cur_xlim = None
            self.cur_ylim = None

        def on_scroll(self, event):
            """鼠标滚轮缩放"""
            if event.inaxes is None:
                return
            ax = event.inaxes
            cur_xlim = ax.get_xlim()
            cur_ylim = ax.get_ylim()

            xdata = event.xdata
            ydata = event.ydata

            # 缩放比例
            base_scale = 1.3
            if event.button == 'up':
                scale = 1 / base_scale
            elif event.button == 'down':
                scale = base_scale
            else:
                return

            new_width = (cur_xlim[1] - cur_xlim[0]) * scale
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale

            relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
            rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

            ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
            ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])
            fig.canvas.draw_idle()

        def on_press(self, event):
            """鼠标按下 - 开始拖拽"""
            if event.inaxes is None:
                return
            if event.button == 1:  # 左键
                self.press = (event.xdata, event.ydata)
                self.cur_xlim = event.inaxes.get_xlim()
                self.cur_ylim = event.inaxes.get_ylim()

        def on_release(self, event):
            """鼠标释放 - 结束拖拽"""
            self.press = None

        def on_motion(self, event):
            """鼠标移动 - 拖拽平移"""
            if self.press is None or event.inaxes is None:
                return
            ax = event.inaxes
            dx = event.xdata - self.press[0]
            dy = event.ydata - self.press[1]

            ax.set_xlim(self.cur_xlim[0] - dx, self.cur_xlim[1] - dx)
            ax.set_ylim(self.cur_ylim[0] - dy, self.cur_ylim[1] - dy)
            fig.canvas.draw_idle()

    zp = ZoomPan()
    fig.canvas.mpl_connect('scroll_event', zp.on_scroll)
    fig.canvas.mpl_connect('button_press_event', zp.on_press)
    fig.canvas.mpl_connect('button_release_event', zp.on_release)
    fig.canvas.mpl_connect('motion_notify_event', zp.on_motion)


# ============================================================================
# K线图（蜡烛图）
# ============================================================================
def create_candlestick_chart(df: pd.DataFrame, title: str = "K线图",
                              stock_code: str = "", days: int = 120,
                              show_volume: bool = True,
                              show_ma: bool = True,
                              ma_periods: list = None) -> object:
    """创建K线图（支持滚轮缩放和拖拽）"""
    _, mpf = _ensure_mpl()

    if df is None or df.empty:
        logger.warning("无数据，无法创建K线图")
        return None

    data = df.head(days).copy()
    data = _prepare_ohlc_data(data)
    if data is None or data.empty:
        return None

    if mpf is not None:
        return _create_mpf_candlestick(data, title, stock_code, show_volume, show_ma, ma_periods)

    return _create_manual_candlestick(data, title, stock_code, show_volume, show_ma, ma_periods)


def _prepare_ohlc_data(df: pd.DataFrame) -> pd.DataFrame | None:
    """标准化 OHLC 数据格式，设置 DatetimeIndex"""
    data = df.copy()

    col_map = {}
    for target, candidates in [
        ("Open", ["open", "Open"]),
        ("High", ["high", "High"]),
        ("Low", ["low", "Low"]),
        ("Close", ["close", "Close"]),
        ("Volume", ["vol", "Volume", "volume"]),
    ]:
        for c in candidates:
            if c in data.columns:
                col_map[target] = c
                break

    required = ["Open", "High", "Low", "Close"]
    missing = [k for k in required if k not in col_map]
    if missing:
        logger.warning(f"缺少必要的列: {missing}")
        return None

    rename_map = {v: k for k, v in col_map.items()}
    data = data.rename(columns=rename_map)

    for col in ["Open", "High", "Low", "Close"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    if "Volume" in data.columns:
        data["Volume"] = pd.to_numeric(data["Volume"], errors="coerce")

    if "trade_date" in data.columns:
        data["trade_date"] = pd.to_datetime(data["trade_date"], format="%Y%m%d", errors="coerce")
        data = data.set_index("trade_date")
    elif not isinstance(data.index, pd.DatetimeIndex):
        try:
            data.index = pd.to_datetime(data.index)
        except Exception:
            data.index = pd.date_range(end=datetime.now(), periods=len(data), freq="B")

    data = data.sort_index()
    data = data.dropna(subset=["Open", "High", "Low", "Close"])

    return data


def _create_mpf_candlestick(data, title, stock_code, show_volume, show_ma, ma_periods):
    """使用 mplfinance 创建K线图"""
    mpf = _mpf
    plt = _mpl["plt"]

    mc = mpf.make_marketcolors(
        up=COLORS["up"], down=COLORS["down"],
        edge={"up": COLORS["up"], "down": COLORS["down"]},
        wick={"up": COLORS["up"], "down": COLORS["down"]},
        volume={"up": COLORS["up"], "down": COLORS["down"]},
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        facecolor=COLORS["card_bg"],
        edgecolor=COLORS["grid"],
        gridcolor=COLORS["grid"],
        gridstyle="--",
        rc={
            "font.size": 9,
            "axes.labelcolor": COLORS["text"],
            "xtick.color": COLORS["text"],
            "ytick.color": COLORS["text"],
        },
    )

    if ma_periods is None:
        ma_periods = [5, 10, 20]
    ma_colors = [COLORS["ma5"], COLORS["ma10"], COLORS["ma20"], COLORS["ma60"]]
    add_plots = []
    if show_ma:
        for i, period in enumerate(ma_periods):
            if period <= len(data):
                ma = data["Close"].rolling(window=period).mean()
                color = ma_colors[i % len(ma_colors)]
                add_plots.append(mpf.make_addplot(ma, color=color, width=1.2, label=f"MA{period}"))

    fig_height = 8 if show_volume else 6
    fig, axes = mpf.plot(
        data,
        type="candle",
        style=style,
        addplot=add_plots if add_plots else None,
        volume=show_volume,
        figsize=(14, fig_height),
        returnfig=True,
        panel_ratios=(3, 1) if show_volume else None,
        tight_layout=True,
    )

    label = f"{stock_code} {title}" if stock_code else title
    fig.suptitle(label, fontsize=14, color=COLORS["gold"],
                 fontweight="bold", y=0.98, fontfamily="Microsoft YaHei UI")

    # 添加交互功能
    axes_list = axes if isinstance(axes, (list, np.ndarray)) else [axes]
    _add_scroll_zoom(fig, axes_list)

    return fig


def _create_manual_candlestick(data, title, stock_code, show_volume, show_ma, ma_periods):
    """纯 matplotlib 手动绘制K线图（支持交互）"""
    plt = _mpl["plt"]

    if ma_periods is None:
        ma_periods = [5, 10, 20]

    n_rows = 2 if show_volume else 1
    fig, axes = plt.subplots(n_rows, 1, figsize=(14, 8 if show_volume else 6),
                              gridspec_kw={"height_ratios": [3, 1]} if show_volume else None,
                              sharex=True)
    if n_rows == 1:
        axes = [axes]

    ax_price = axes[0]
    _apply_dark_style(fig, axes)

    x = np.arange(len(data))
    opens = data["Open"].values
    highs = data["High"].values
    lows = data["Low"].values
    closes = data["Close"].values

    # 绘制蜡烛
    for i in x:
        color = COLORS["up"] if closes[i] >= opens[i] else COLORS["down"]
        body_bottom = min(opens[i], closes[i])
        body_height = abs(closes[i] - opens[i])
        ax_price.bar(i, body_height, bottom=body_bottom, width=0.6,
                     color=color, edgecolor=color, linewidth=0.5)
        ax_price.vlines(i, lows[i], highs[i], color=color, linewidth=0.8)

    # 均线
    if show_ma:
        ma_colors = [COLORS["ma5"], COLORS["ma10"], COLORS["ma20"], COLORS["ma60"]]
        for i, period in enumerate(ma_periods):
            if period <= len(data):
                ma = data["Close"].rolling(window=period).mean().values
                ax_price.plot(x, ma, color=ma_colors[i % len(ma_colors)],
                              linewidth=1.2, label=f"MA{period}")
        ax_price.legend(loc="upper left", fontsize=9, framealpha=0.3,
                        facecolor=COLORS["card_bg"], edgecolor=COLORS["grid"],
                        labelcolor=COLORS["text"])

    # 价格轴格式
    _format_price_axis(ax_price, closes)
    ax_price.set_ylabel("价格 (元)", fontsize=10, color=COLORS["text"])

    # 成交量
    if show_volume and "Volume" in data.columns:
        ax_vol = axes[1]
        volumes = data["Volume"].values
        vol_colors = [COLORS["up"] if closes[i] >= opens[i] else COLORS["down"] for i in x]
        ax_vol.bar(x, volumes, color=vol_colors, width=0.6, alpha=0.7)
        ax_vol.set_ylabel("成交量 (手)", fontsize=10, color=COLORS["text"])
        _format_volume_axis(ax_vol)

    # X轴日期格式
    dates = data.index if isinstance(data.index, pd.DatetimeIndex) else None
    if dates is not None:
        _format_date_axis(axes[-1], dates)

    label = f"{stock_code} {title}" if stock_code else title
    fig.suptitle(label, fontsize=14, color=COLORS["gold"], fontweight="bold", y=0.98)

    fig.tight_layout(rect=[0, 0, 1, 0.95])

    # 添加交互功能
    _add_scroll_zoom(fig, axes)

    return fig


# ============================================================================
# 均线分析图
# ============================================================================
def create_ma_chart(df: pd.DataFrame, title: str = "均线分析",
                    stock_code: str = "", days: int = 250,
                    periods: list = None) -> object:
    """创建均线分析图（支持交互）"""
    _ensure_mpl()
    plt = _mpl["plt"]

    if df is None or df.empty:
        return None

    if periods is None:
        periods = [5, 10, 20, 60]

    data = df.head(days).copy()
    if "close" in data.columns:
        close = pd.to_numeric(data["close"], errors="coerce")
    elif "Close" in data.columns:
        close = pd.to_numeric(data["Close"], errors="coerce")
    else:
        logger.warning("缺少 close 列")
        return None

    fig, ax = plt.subplots(figsize=(14, 7))
    _apply_dark_style(fig, ax)

    x = np.arange(len(close))

    ax.plot(x, close.values, color=COLORS["accent"], linewidth=1.5,
            label="收盘价", alpha=0.9)

    ma_colors = [COLORS["ma5"], COLORS["ma10"], COLORS["ma20"], COLORS["ma60"]]
    for i, period in enumerate(periods):
        if period <= len(close):
            ma = close.rolling(window=period).mean()
            color = ma_colors[i % len(ma_colors)]
            ax.plot(x, ma.values, color=color, linewidth=1.2, label=f"MA{period}")

    # 支撑/阻力
    if len(close) >= 20:
        recent = close.head(20)
        high_val = recent.max()
        low_val = recent.min()
        ax.axhline(y=high_val, color=COLORS["down"], linestyle="--", alpha=0.4, linewidth=0.8)
        ax.axhline(y=low_val, color=COLORS["up"], linestyle="--", alpha=0.4, linewidth=0.8)
        ax.annotate(f"阻力 {high_val:.2f}", xy=(0, high_val),
                    fontsize=9, color=COLORS["down"], fontweight="bold",
                    xytext=(10, 10), textcoords="offset points")
        ax.annotate(f"支撑 {low_val:.2f}", xy=(0, low_val),
                    fontsize=9, color=COLORS["up"], fontweight="bold",
                    xytext=(10, -15), textcoords="offset points")

    # 坐标轴格式
    _format_price_axis(ax, close.values)
    ax.set_ylabel("价格 (元)", fontsize=10, color=COLORS["text"])

    dates = data.index if isinstance(data.index, pd.DatetimeIndex) else None
    if dates is not None:
        _format_date_axis(ax, dates)

    ax.legend(loc="upper left", fontsize=9, framealpha=0.3,
              facecolor=COLORS["card_bg"], edgecolor=COLORS["grid"],
              labelcolor=COLORS["text"])

    label = f"{stock_code} {title}" if stock_code else title
    fig.suptitle(label, fontsize=14, color=COLORS["gold"], fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    _add_scroll_zoom(fig, [ax])

    return fig


# ============================================================================
# 柱状图（通用）
# ============================================================================
def create_bar_chart(labels: list, values: list, title: str = "",
                     xlabel: str = "", ylabel: str = "",
                     stock_code: str = "",
                     color_positive: str = None,
                     color_negative: str = None,
                     show_values: bool = True,
                     highlight_zero: bool = True,
                     figsize: tuple = None,
                     unit: str = "") -> object:
    """创建柱状图（支持交互）"""
    _ensure_mpl()
    plt = _mpl["plt"]

    if color_positive is None:
        color_positive = COLORS["up"]
    if color_negative is None:
        color_negative = COLORS["down"]
    if figsize is None:
        figsize = (max(8, len(labels) * 1.2), 6)

    fig, ax = plt.subplots(figsize=figsize)
    _apply_dark_style(fig, ax)

    colors = []
    for v in values:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            colors.append(COLORS["text_muted"])
        elif v >= 0:
            colors.append(color_positive)
        else:
            colors.append(color_negative)

    bars = ax.bar(range(len(labels)), values, color=colors, width=0.6, alpha=0.85)

    if show_values:
        for bar, v in zip(bars, values):
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                y_pos = bar.get_height()
                va = "bottom" if v >= 0 else "top"
                if abs(v) >= 1e8:
                    fmt = f"{v/1e8:,.1f}亿"
                elif abs(v) >= 1e4:
                    fmt = f"{v/1e4:,.1f}万"
                elif abs(v) < 100:
                    fmt = f"{v:,.2f}"
                else:
                    fmt = f"{v:,.0f}"
                ax.text(bar.get_x() + bar.get_width() / 2, y_pos, fmt,
                        ha="center", va=va, fontsize=8, color=COLORS["text"])

    if highlight_zero:
        ax.axhline(y=0, color=COLORS["grid"], linewidth=1, linestyle="-")

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=10, color=COLORS["text"])
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10, color=COLORS["text"])

    # 自动格式化 Y 轴
    _ensure_mpl()
    mticker = _mpl["mticker"]
    if unit:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, p: f"{v:,.0f}{unit}"))
    else:
        # 根据数值范围自动选择单位
        max_val = max(abs(v) for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))) if values else 1
        if max_val >= 1e8:
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(
                lambda v, p: f"{v/1e8:,.1f}亿"))
        elif max_val >= 1e4:
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(
                lambda v, p: f"{v/1e4:,.1f}万"))

    label = f"{stock_code} {title}" if stock_code else title
    fig.suptitle(label, fontsize=14, color=COLORS["gold"], fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    _add_scroll_zoom(fig, [ax])

    return fig


# ============================================================================
# 组合图：行情概览
# ============================================================================
def create_market_overview_chart(df: pd.DataFrame, stock_code: str = "",
                                  days: int = 120) -> object:
    """创建行情概览组合图（K线 + 成交量 + RSI）（支持交互）"""
    _ensure_mpl()
    plt = _mpl["plt"]

    if df is None or df.empty:
        return None

    data = df.head(days).copy()
    if "close" in data.columns:
        close = pd.to_numeric(data["close"], errors="coerce")
    else:
        return None

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10),
                                          gridspec_kw={"height_ratios": [4, 1.5, 1.5]},
                                          sharex=True)
    _apply_dark_style(fig, [ax1, ax2, ax3])

    x = np.arange(len(data))

    # 价格 + 均线
    ax1.plot(x, close.values, color=COLORS["accent"], linewidth=1.5, label="收盘价")
    for period, color, label in [(5, COLORS["ma5"], "MA5"), (10, COLORS["ma10"], "MA10"),
                                  (20, COLORS["ma20"], "MA20")]:
        if period <= len(close):
            ma = close.rolling(window=period).mean()
            ax1.plot(x, ma.values, color=color, linewidth=1, label=label, alpha=0.8)

    _format_price_axis(ax1, close.values)
    ax1.set_ylabel("价格 (元)", fontsize=10, color=COLORS["text"])
    ax1.legend(loc="upper left", fontsize=8, framealpha=0.3,
               facecolor=COLORS["card_bg"], edgecolor=COLORS["grid"],
               labelcolor=COLORS["text"])

    # 成交量
    if "vol" in data.columns:
        volumes = pd.to_numeric(data["vol"], errors="coerce")
        opens = pd.to_numeric(data.get("open", data.get("Open", pd.Series())), errors="coerce")
        closes_vals = close.values
        opens_vals = opens.values if len(opens) > 0 else closes_vals
        vol_colors = [COLORS["up"] if closes_vals[i] >= opens_vals[i] else COLORS["down"]
                      for i in range(len(closes_vals))]
        ax2.bar(x, volumes.values, color=vol_colors, width=0.6, alpha=0.7)
        ax2.set_ylabel("成交量 (手)", fontsize=10, color=COLORS["text"])
        _format_volume_axis(ax2)

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    ax3.plot(x, rsi.values, color=COLORS["gold"], linewidth=1.2, label="RSI(14)")
    ax3.axhline(y=70, color=COLORS["down"], linestyle="--", alpha=0.5, linewidth=0.8)
    ax3.axhline(y=30, color=COLORS["up"], linestyle="--", alpha=0.5, linewidth=0.8)
    ax3.fill_between(x, 30, 70, alpha=0.05, color=COLORS["accent"])
    ax3.set_ylabel("RSI", fontsize=10, color=COLORS["text"])
    ax3.set_ylim(0, 100)
    ax3.legend(loc="upper left", fontsize=8, framealpha=0.3,
               facecolor=COLORS["card_bg"], edgecolor=COLORS["grid"],
               labelcolor=COLORS["text"])

    # X轴日期
    dates = data.index if isinstance(data.index, pd.DatetimeIndex) else None
    if dates is not None:
        _format_date_axis(ax3, dates)

    label = f"{stock_code} 行情概览" if stock_code else "行情概览"
    fig.suptitle(label, fontsize=14, color=COLORS["gold"], fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    _add_scroll_zoom(fig, [ax1, ax2, ax3])

    return fig


# ============================================================================
# 显示和保存
# ============================================================================
def show_charts(figures: list, titles: list = None):
    """在 Tkinter 窗口中显示图表（交互式：支持拖拽和滚轮缩放）"""
    _ensure_mpl()
    import tkinter as tk
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

    if not figures:
        return

    root = tk._get_default_root()
    if root is None:
        win = tk.Tk()
    else:
        win = tk.Toplevel(root)

    win.title("财务分析图表")
    win.configure(bg=COLORS["bg"])

    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    w, h = min(1400, sw - 100), min(900, sh - 100)
    win.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    canvas = tk.Canvas(win, bg=COLORS["bg"], highlightthickness=0)
    scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg=COLORS["bg"])

    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    win.bind("<MouseWheel>", _on_mousewheel)
    canvas.bind("<MouseWheel>", _on_mousewheel)

    for i, fig in enumerate(figures):
        if fig is None:
            continue

        frame = tk.Frame(scroll_frame, bg=COLORS["card_bg"],
                         highlightbackground=COLORS["grid"], highlightthickness=1)
        frame.pack(fill=tk.X, padx=15, pady=10)

        if titles and i < len(titles):
            tk.Label(frame, text=titles[i], bg=COLORS["card_bg"], fg=COLORS["gold"],
                     font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w", padx=10, pady=(8, 0))

        fig_canvas = FigureCanvasTkAgg(fig, master=frame)
        fig_canvas.draw()
        fig_canvas.get_tk_widget().pack(fill=tk.X, padx=5, pady=5)

        # 工具栏（提供缩放、平移、重置等按钮）
        toolbar_frame = tk.Frame(frame, bg=COLORS["card_bg"])
        toolbar_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        toolbar = NavigationToolbar2Tk(fig_canvas, toolbar_frame)
        toolbar.update()

    # 底部按钮
    btn_frame = tk.Frame(win, bg=COLORS["bg"])
    btn_frame.pack(fill=tk.X, padx=15, pady=10)

    tk.Button(btn_frame, text="保存所有图表", bg=COLORS["gold"], fg=COLORS["bg"],
              font=("Microsoft YaHei UI", 10, "bold"), relief="flat", padx=16, pady=6,
              cursor="hand2", command=lambda: save_charts(figures)).pack(side=tk.LEFT)

    # 提示标签
    tk.Label(btn_frame, text="操作提示: 滚轮缩放 | 左键拖拽 | 工具栏可重置视图",
             bg=COLORS["bg"], fg=COLORS.get("text_muted", COLORS["text_muted"]),
             font=("Microsoft YaHei UI", 9)).pack(side=tk.LEFT, padx=20)

    tk.Button(btn_frame, text="关闭", bg=COLORS["card_bg"], fg=COLORS.get("text_muted", COLORS["text_muted"]),
              font=("Microsoft YaHei UI", 10), relief="flat", padx=16, pady=6,
              cursor="hand2", command=win.destroy).pack(side=tk.RIGHT)

    if root is None:
        win.mainloop()


def save_charts(figures: list, directory: str = None, prefix: str = "chart"):
    """保存图表到文件"""
    _ensure_mpl()

    if not figures:
        return

    if directory is None:
        import tkinter as tk
        from tkinter import filedialog
        root = tk._get_default_root()
        if root is not None:
            directory = filedialog.askdirectory(title="选择保存目录", parent=root)
        else:
            directory = filedialog.askdirectory(title="选择保存目录")
        if not directory:
            return

    from pathlib import Path
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = Path(directory)

    for i, fig in enumerate(figures):
        if fig is None:
            continue
        filename = save_dir / f"{prefix}_{i+1}_{ts}.png"
        fig.savefig(str(filename), dpi=150, bbox_inches="tight",
                     facecolor=fig.get_facecolor(), edgecolor="none")
        logger.info(f"图表已保存: {filename}")


# ============================================================================
# 新增图表类型 - Financial Data Visualization Skill
# ============================================================================

def create_sparkline_chart(data: list, width: int = 120, height: int = 40,
                            line_color: str = None, show_area: bool = True,
                            show_end_dot: bool = True) -> object:
    """创建迷你趋势图（Sparkline）- 嵌入 KPI 卡片"""
    _ensure_mpl()
    plt = _mpl["plt"]

    if not data or len(data) < 2:
        return None

    if line_color is None:
        line_color = COLORS["up"] if data[-1] >= data[0] else COLORS["down"]

    fig, ax = plt.subplots(figsize=(width / 100, height / 100), dpi=100)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    x = np.arange(len(data))
    ax.plot(x, data, color=line_color, linewidth=1.5, solid_capstyle="round")

    if show_area:
        ax.fill_between(x, data, alpha=0.15, color=line_color)

    if show_end_dot:
        ax.plot(x[-1], data[-1], "o", color=line_color, markersize=3)

    ax.set_xlim(0, len(data) - 1)
    ax.set_ylim(min(data) * 0.98, max(data) * 1.02)
    ax.axis("off")
    ax.margins(0)

    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    return fig


def create_area_chart(df: pd.DataFrame, title: str = "价格走势",
                      stock_code: str = "", days: int = 120,
                      value_col: str = "close") -> object:
    """创建渐变面积图 - 用于价格/指标趋势展示"""
    _ensure_mpl()
    plt = _mpl["plt"]

    if df is None or df.empty:
        return None

    data = df.head(days).copy()
    col = value_col if value_col in data.columns else "close"
    if col not in data.columns:
        return None

    values = pd.to_numeric(data[col], errors="coerce").dropna()
    if len(values) < 2:
        return None

    is_positive = values.iloc[-1] >= values.iloc[0]
    line_color = COLORS["up"] if is_positive else COLORS["down"]

    fig, ax = plt.subplots(figsize=(14, 5))
    _apply_dark_style(fig, ax)

    x = np.arange(len(values))
    ax.plot(x, values.values, color=line_color, linewidth=2, solid_capstyle="round")

    # 渐变填充
    from matplotlib.collections import LineCollection
    for i in range(len(values) - 1):
        ax.fill_between(x[i:i+2], values.values[i:i+2],
                         alpha=0.3 * (i / len(values)), color=line_color)

    # 整体底层填充
    ax.fill_between(x, values.values, alpha=0.08, color=line_color)

    _format_price_axis(ax, values.values)
    ax.set_ylabel("价格 (元)", fontsize=10, color=COLORS["text_muted"])

    dates = data.index if isinstance(data.index, pd.DatetimeIndex) else None
    if dates is not None:
        _format_date_axis(ax, dates)

    # 标注最新价
    latest = values.iloc[-1]
    change_pct = (values.iloc[-1] - values.iloc[0]) / values.iloc[0] * 100
    label_text = f"最新: {latest:.2f}  {change_pct:+.2f}%"
    ax.annotate(label_text, xy=(x[-1], latest),
                xytext=(-80, 20), textcoords="offset points",
                fontsize=10, fontweight="bold", color=line_color,
                arrowprops=dict(arrowstyle="->", color=line_color, lw=1.2),
                bbox=dict(boxstyle="round,pad=0.3", facecolor=COLORS["card_bg"],
                          edgecolor=line_color, alpha=0.9))

    label = f"{stock_code} {title}" if stock_code else title
    fig.suptitle(label, fontsize=14, color=COLORS["gold"], fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    _add_scroll_zoom(fig, [ax])
    return fig


def create_percentage_bar_chart(labels: list, values: list, title: str = "涨跌幅对比",
                                 stock_code: str = "") -> object:
    """创建百分比涨跌条 - 水平双向条形图"""
    _ensure_mpl()
    plt = _mpl["plt"]

    if not labels or not values:
        return None

    fig, ax = plt.subplots(figsize=(10, max(3, len(labels) * 0.6 + 1)))
    _apply_dark_style(fig, ax)

    bar_colors = [COLORS["up"] if v >= 0 else COLORS["down"] for v in values]
    y_pos = np.arange(len(labels))

    bars = ax.barh(y_pos, values, color=bar_colors, height=0.55, alpha=0.85,
                    edgecolor=[c for c in bar_colors], linewidth=0.5)

    # 数值标签
    for bar, v in zip(bars, values):
        x_pos = bar.get_width()
        ha = "left" if v >= 0 else "right"
        offset = 0.3 if v >= 0 else -0.3
        ax.text(x_pos + offset, bar.get_y() + bar.get_height() / 2,
                f"{v:+.2f}%", ha=ha, va="center",
                fontsize=9, fontweight="bold",
                color=COLORS["up"] if v >= 0 else COLORS["down"])

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=10)
    ax.axvline(x=0, color=COLORS["grid"], linewidth=1)
    ax.set_xlabel("涨跌幅 (%)", fontsize=10, color=COLORS["text_muted"])

    # 去掉上边框和右边框
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    label = f"{stock_code} {title}" if stock_code else title
    fig.suptitle(label, fontsize=14, color=COLORS["gold"], fontweight="bold", y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.95])

    return fig


def create_multi_metric_dashboard(df: pd.DataFrame, stock_code: str = "",
                                    days: int = 60) -> object:
    """创建多指标仪表盘 - 4象限布局（价格趋势+成交量+RSI+MACD）"""
    _ensure_mpl()
    plt = _mpl["plt"]

    if df is None or df.empty:
        return None

    data = df.head(days).copy()
    close_col = "close" if "close" in data.columns else "Close"
    if close_col not in data.columns:
        return None

    close = pd.to_numeric(data[close_col], errors="coerce")
    if len(close) < 20:
        return None

    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor(COLORS["bg"])

    # 2x2 网格布局
    gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.25,
                          left=0.06, right=0.96, top=0.92, bottom=0.06)

    x = np.arange(len(close))

    # ---- 左上: 价格趋势 + 均线 ----
    ax1 = fig.add_subplot(gs[0, 0])
    _apply_dark_style(fig, ax1)
    ax1.plot(x, close.values, color=COLORS["accent"], linewidth=1.5, label="收盘价")
    for period, color, lbl in [(5, COLORS["ma5"], "MA5"), (10, COLORS["ma10"], "MA10"),
                                (20, COLORS["ma20"], "MA20")]:
        if period <= len(close):
            ma = close.rolling(window=period).mean()
            ax1.plot(x, ma.values, color=color, linewidth=1, label=lbl, alpha=0.8)
    _format_price_axis(ax1, close.values)
    ax1.set_ylabel("价格", fontsize=9, color=COLORS["text_muted"])
    ax1.legend(loc="upper left", fontsize=7, framealpha=0.3,
               facecolor=COLORS["card_bg"], edgecolor=COLORS["grid"], labelcolor=COLORS["text"])
    ax1.set_title("价格趋势", fontsize=10, color=COLORS["gold"], pad=8)

    # ---- 右上: 成交量 ----
    ax2 = fig.add_subplot(gs[0, 1])
    _apply_dark_style(fig, ax2)
    vol_col = "vol" if "vol" in data.columns else "Volume"
    if vol_col in data.columns:
        volumes = pd.to_numeric(data[vol_col], errors="coerce")
        opens = pd.to_numeric(data.get("open", data.get("Open", close)), errors="coerce")
        vol_colors = [COLORS["up"] if close.values[i] >= (opens.values[i] if hasattr(opens, 'values') else close.values[i]) else COLORS["down"]
                      for i in range(len(close))]
        ax2.bar(x, volumes.values, color=vol_colors, width=0.6, alpha=0.7)
        _format_volume_axis(ax2)
    ax2.set_ylabel("成交量", fontsize=9, color=COLORS["text_muted"])
    ax2.set_title("成交量", fontsize=10, color=COLORS["gold"], pad=8)

    # ---- 左下: RSI ----
    ax3 = fig.add_subplot(gs[1, 0])
    _apply_dark_style(fig, ax3)
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss_series = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss_series
    rsi = 100 - (100 / (1 + rs))
    ax3.plot(x, rsi.values, color=COLORS["gold"], linewidth=1.2, label="RSI(14)")
    ax3.axhline(y=70, color=COLORS["down"], linestyle="--", alpha=0.5, linewidth=0.8)
    ax3.axhline(y=30, color=COLORS["up"], linestyle="--", alpha=0.5, linewidth=0.8)
    ax3.fill_between(x, 30, 70, alpha=0.05, color=COLORS["accent"])
    ax3.set_ylabel("RSI", fontsize=9, color=COLORS["text_muted"])
    ax3.set_ylim(0, 100)
    ax3.legend(loc="upper left", fontsize=7, framealpha=0.3,
               facecolor=COLORS["card_bg"], edgecolor=COLORS["grid"], labelcolor=COLORS["text"])
    ax3.set_title("RSI (14)", fontsize=10, color=COLORS["gold"], pad=8)

    # ---- 右下: MACD ----
    ax4 = fig.add_subplot(gs[1, 1])
    _apply_dark_style(fig, ax4)
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9).mean()
    macd_hist = macd_line - signal

    hist_colors = [COLORS["up"] if v >= 0 else COLORS["down"] for v in macd_hist.values]
    ax4.bar(x, macd_hist.values, color=hist_colors, width=0.6, alpha=0.6, label="MACD柱")
    ax4.plot(x, macd_line.values, color=COLORS["accent"], linewidth=1, label="DIF")
    ax4.plot(x, signal.values, color=COLORS["gold"], linewidth=1, label="DEA")
    ax4.axhline(y=0, color=COLORS["grid"], linewidth=0.5)
    ax4.set_ylabel("MACD", fontsize=9, color=COLORS["text_muted"])
    ax4.legend(loc="upper left", fontsize=7, framealpha=0.3,
               facecolor=COLORS["card_bg"], edgecolor=COLORS["grid"], labelcolor=COLORS["text"])
    ax4.set_title("MACD (12,26,9)", fontsize=10, color=COLORS["gold"], pad=8)

    # X轴日期
    dates = data.index if isinstance(data.index, pd.DatetimeIndex) else None
    if dates is not None:
        for ax in [ax1, ax2, ax3, ax4]:
            _format_date_axis(ax, dates, max_ticks=8)

    label = f"{stock_code} 技术指标仪表盘" if stock_code else "技术指标仪表盘"
    fig.suptitle(label, fontsize=14, color=COLORS["gold"], fontweight="bold", y=0.98)

    _add_scroll_zoom(fig, [ax1, ax2, ax3, ax4])
    return fig


# ============================================================================
# Phase 2: 深度分析图表
# ============================================================================

def create_dupont_waterfall(nm_old, nm_new, at_old, at_new, em_old, em_new,
                            roe_old, roe_new, stock_code=""):
    """杜邦分析瀑布图 - 展示各因子对 ROE 变动的贡献"""
    plt, _, _, _, _ = _ensure_mpl()
    if plt is None:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))
    _apply_dark_style(fig, ax)

    # 计算各因子贡献 (连环替代法)
    nm_contrib = (nm_new - nm_old) * at_old * em_old / 100 if all(v is not None for v in [nm_new, nm_old, at_old, em_old]) else 0
    at_contrib = nm_new * (at_new - at_old) * em_old / 100 if all(v is not None for v in [nm_new, at_new, at_old, em_old]) else 0
    em_contrib = nm_new * at_new * (em_new - em_old) / 100 if all(v is not None for v in [nm_new, at_new, em_new, em_old]) else 0

    categories = ['ROE(期初)', '净利率贡献', '周转率贡献', '杠杆贡献', 'ROE(期末)']
    values = [roe_old, nm_contrib, at_contrib, em_contrib, roe_new]

    # 瀑布图
    cumulative = [roe_old]
    for v in values[1:-1]:
        cumulative.append(cumulative[-1] + v)

    colors = [COLORS["accent"], COLORS["up"] if nm_contrib >= 0 else COLORS["down"],
              COLORS["up"] if at_contrib >= 0 else COLORS["down"],
              COLORS["up"] if em_contrib >= 0 else COLORS["down"],
              COLORS["gold"]]

    bottoms = [0, roe_old, roe_old + nm_contrib, roe_old + nm_contrib + at_contrib, 0]
    bar_values = [roe_old, nm_contrib, at_contrib, em_contrib, roe_new]

    bars = ax.bar(categories, bar_values, bottom=bottoms, color=colors, width=0.6, alpha=0.85)

    # 标注数值
    for i, (bar, val) in enumerate(zip(bars, bar_values)):
        y_pos = bar.get_y() + bar.get_height() / 2
        label = f"{val:+.2f}pp" if i in [1, 2, 3] else f"{val:.2f}%"
        ax.text(bar.get_x() + bar.get_width() / 2, y_pos, label,
                ha="center", va="center", fontsize=10, color=COLORS["text"], fontweight="bold")

    ax.set_title(f"杜邦分析瀑布图 - {stock_code}" if stock_code else "杜邦分析瀑布图",
                 fontsize=14, color=COLORS["gold"], fontweight="bold", pad=15)
    ax.set_ylabel("ROE (%)", fontsize=11, color=COLORS["text_muted"])
    ax.axhline(y=0, color=COLORS["grid"], linewidth=0.5)

    fig.tight_layout()
    return fig


def create_fscore_radar(scores: dict, stock_code=""):
    """F-score 雷达图"""
    plt, _, _, _, _ = _ensure_mpl()
    if plt is None:
        return None

    categories = list(scores.keys())
    values = list(scores.values())
    N = len(categories)

    if N < 3:
        return None

    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    values += values[:1]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    _apply_dark_style(fig, ax)

    ax.plot(angles, values, "o-", linewidth=2, color=COLORS["accent"], alpha=0.8)
    ax.fill(angles, values, alpha=0.15, color=COLORS["accent"])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories, fontsize=10, color=COLORS["text"])
    ax.set_ylim(0, max(max(values[:-1]) * 1.2, 1))
    ax.set_title(f"财务健康雷达图 - {stock_code}" if stock_code else "财务健康雷达图",
                 fontsize=14, color=COLORS["gold"], fontweight="bold", pad=20)

    fig.tight_layout()
    return fig


def create_peer_comparison_bar(company_name: str, metrics: dict,
                               peer_avgs: dict, stock_code=""):
    """行业对比柱状图"""
    plt, _, _, _, _ = _ensure_mpl()
    if plt is None:
        return None

    labels = list(metrics.keys())
    company_vals = [metrics[k] for k in labels]
    peer_vals = [peer_avgs.get(k, 0) for k in labels]

    x = np.arange(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    _apply_dark_style(fig, ax)

    bars1 = ax.bar(x - width / 2, company_vals, width, label=company_name,
                   color=COLORS["accent"], alpha=0.85)
    bars2 = ax.bar(x + width / 2, peer_vals, width, label="行业均值",
                   color=COLORS["text_muted"], alpha=0.6)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10, color=COLORS["text"])
    ax.legend(fontsize=10, framealpha=0.3,
              facecolor=COLORS["card_bg"], edgecolor=COLORS["grid"], labelcolor=COLORS["text"])
    ax.set_title(f"行业对比 - {stock_code}" if stock_code else "行业对比",
                 fontsize=14, color=COLORS["gold"], fontweight="bold", pad=15)

    # 标注数值
    for bar in bars1:
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{bar.get_height():.1f}", ha="center", va="bottom",
                fontsize=8, color=COLORS["accent"])

    fig.tight_layout()
    return fig


def create_valuation_gauge(pe_pct: float, pb_pct: float = None, stock_code=""):
    """估值分位仪表盘"""
    plt, _, _, _, _ = _ensure_mpl()
    if plt is None:
        return None

    fig, axes = plt.subplots(1, 2 if pb_pct else 1, figsize=(8 if pb_pct else 5, 4))
    if not isinstance(axes, np.ndarray):
        axes = [axes]

    _apply_dark_style(fig, axes[0])

    for i, (pct, label) in enumerate([(pe_pct, "PE 分位"), (pb_pct, "PB 分位")]):
        if pct is None or i >= len(axes):
            continue
        ax = axes[i]
        _apply_dark_style(fig, ax)

        # 半圆仪表
        theta = np.linspace(0, np.pi, 100)
        r = 1
        ax.plot(r * np.cos(theta), r * np.sin(theta), color=COLORS["grid"], linewidth=2)

        # 颜色区间
        zones = [(0, 20, COLORS["up"]), (20, 40, "#4CAF50"), (40, 60, COLORS["gold"]),
                 (60, 80, "#FF9800"), (80, 100, COLORS["down"])]
        for z_start, z_end, z_color in zones:
            t = np.linspace(z_start / 100 * np.pi, z_end / 100 * np.pi, 20)
            ax.fill_between(np.cos(t), np.sin(t), 0, alpha=0.15, color=z_color)

        # 指针
        angle = pct / 100 * np.pi
        ax.annotate("", xy=(0.8 * np.cos(angle), 0.8 * np.sin(angle)), xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->", color=COLORS["gold"], lw=2.5))

        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-0.2, 1.3)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_title(f"{label}: {pct:.0f}%", fontsize=12, color=COLORS["text"], fontweight="bold")

    fig.suptitle(f"估值分位仪表 - {stock_code}" if stock_code else "估值分位",
                 fontsize=14, color=COLORS["gold"], fontweight="bold")
    fig.tight_layout()
    return fig
