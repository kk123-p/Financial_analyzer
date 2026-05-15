"""
UI 布局组件 - 从 app.py 拆分出来
包含：侧边栏、主内容区、状态栏、KPI卡片、数据表格
"""
import tkinter as tk
from ..logging_config import get_logger

logger = get_logger(__name__)

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    HAS_BOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    HAS_BOOTSTRAP = False


def build_sidebar(app):
    """构建侧边栏导航"""
    from .app import SIDEBAR_SECTIONS

    # Header
    header = ttk.Frame(app.sidebar_frame)
    header.pack(fill="x", padx=4, pady=(4, 8))
    ttk.Label(header, text="FA Pro", font=("Microsoft YaHei UI", 14, "bold")).pack(side="left", padx=4)

    # Input area
    input_frame = ttk.LabelFrame(app.sidebar_frame, text=" 股票 ")
    input_frame.pack(fill="x", padx=4, pady=(0, 8))
    inner_input = ttk.Frame(input_frame)
    inner_input.pack(fill="x", padx=8, pady=8)

    app.stock_var = tk.StringVar()
    entry = ttk.Entry(inner_input, textvariable=app.stock_var, width=18)
    entry.pack(fill="x", pady=(0, 4))
    entry.bind("<Return>", lambda e: app._run_analysis())

    btn_row = ttk.Frame(inner_input)
    btn_row.pack(fill="x")
    ttk.Button(btn_row, text="分析", command=app._run_analysis, width=8).pack(side="left", padx=1)
    ttk.Button(btn_row, text="获取", command=app._fetch_data_only, width=8).pack(side="left", padx=1)

    # Source selector
    src_frame = ttk.Frame(inner_input)
    src_frame.pack(fill="x", pady=(4, 0))
    ttk.Label(src_frame, text="源:", width=3).pack(side="left")
    app.source_var = tk.StringVar(value=app.data_adapter.active_source)
    src_combo = ttk.Combobox(src_frame, textvariable=app.source_var, width=10, state="readonly",
                             values=["tushare", "akshare", "sina", "yfinance"])
    src_combo.pack(side="left", fill="x", expand=True)

    # Navigation sections
    nav_frame = ttk.Frame(app.sidebar_frame)
    nav_frame.pack(fill="both", expand=True, padx=4)

    for section_name, items in SIDEBAR_SECTIONS:
        section_label = ttk.Label(nav_frame, text=f" {section_name}", font=("Microsoft YaHei UI", 9, "bold"),
                                  anchor="w")
        section_label.pack(fill="x", pady=(6, 2))

        for icon, label, key in items:
            btn = ttk.Button(nav_frame, text=f"{icon} {label}", anchor="w",
                             command=lambda k=key: app._on_nav_click(k))
            btn.pack(fill="x", pady=1)


def build_main_area(app):
    """构建主内容区"""
    from .theme import Colors, Fonts

    app.notebook = ttk.Notebook(app.content_frame)
    app.notebook.pack(fill="both", expand=True)

    # Tab 1: Analysis output
    result_tab = ttk.Frame(app.notebook)
    app.notebook.add(result_tab, text="  分析结果  ")

    text_wrap = ttk.Frame(result_tab)
    text_wrap.pack(fill="both", expand=True)

    c = Colors
    f = Fonts

    app.result_text = tk.Text(
        text_wrap, font=f.RESULT, bg=c.BG_SECONDARY, fg=c.FG_PRIMARY,
        relief="flat", wrap="word", state="disabled", undo=False,
        spacing1=2, spacing3=2, padx=10, pady=8,
        insertbackground=c.ACCENT, selectbackground=c.ACCENT_SUBTLE,
        selectforeground=c.FG_PRIMARY,
    )
    result_sb = ttk.Scrollbar(text_wrap, orient="vertical", command=app.result_text.yview)
    app.result_text.configure(yscrollcommand=result_sb.set)
    app.result_text.pack(side="left", fill="both", expand=True)
    result_sb.pack(side="right", fill="y")
    _configure_result_tags(app)

    # Tab 2: Charts
    chart_tab = ttk.Frame(app.notebook)
    app.notebook.add(chart_tab, text="  图表  ")

    chart_toolbar = ttk.Frame(chart_tab)
    chart_toolbar.pack(fill="x", padx=4, pady=4)

    app.chart_type_var = tk.StringVar(value="K线图")
    chart_types = ["K线图", "均线图", "柱状图"]
    for ct in chart_types:
        ttk.Radiobutton(chart_toolbar, text=ct, variable=app.chart_type_var,
                        value=ct, command=app._show_chart).pack(side="left", padx=4)

    app.chart_container = ttk.Frame(chart_tab)
    app.chart_container.pack(fill="both", expand=True)

    # Tab 3: Data table
    data_tab = ttk.Frame(app.notebook)
    app.notebook.add(data_tab, text="  数据  ")

    # Tab 4: AI
    ai_tab = ttk.Frame(app.notebook)
    app.notebook.add(ai_tab, text="  AI  ")
    try:
        from .deepseek_dialog import DeepSeekPanel
        app.ai_panel = DeepSeekPanel(ai_tab)
        app.ai_panel.pack(fill="both", expand=True)
    except Exception:
        ttk.Label(ai_tab, text="AI 模块未加载").pack(expand=True)

    # KPI cards
    _build_kpi_area(app)

    # Progress
    app.progress = ttk.Progressbar(app.content_frame, mode="indeterminate")
    app.progress.pack(fill="x", padx=4, pady=2)


def build_status_bar(app):
    """构建状态栏"""
    status_frame = ttk.Frame(app.content_frame, height=24)
    status_frame.pack(fill="x", padx=4, pady=(0, 4))
    status_frame.pack_propagate(False)

    app.status_var = tk.StringVar(value="就绪")
    app.status_label = ttk.Label(status_frame, textvariable=app.status_var, font=("Microsoft YaHei UI", 9))
    app.status_label.pack(side="left", padx=4)

    app.source_label = ttk.Label(status_frame, text=f"数据源: {app.data_adapter.active_source.upper()}",
                                  font=("Microsoft YaHei UI", 9))
    app.source_label.pack(side="right", padx=4)


def _configure_result_tags(app):
    """配置结果文本标签"""
    t = app.result_text
    from .theme import Colors, Fonts
    c, f = Colors, Fonts

    t.tag_configure("heading", font=f.HEADING, foreground=c.ACCENT, spacing1=8, spacing3=4)
    t.tag_configure("section", font=f.BODY_BOLD, foreground=c.INFO, spacing1=6, spacing3=2)
    t.tag_configure("bold", font=f.BODY_BOLD)
    t.tag_configure("success", foreground=c.SUCCESS)
    t.tag_configure("danger", foreground=c.DANGER)
    t.tag_configure("warning", foreground=c.WARNING)
    t.tag_configure("info", foreground=c.INFO)
    t.tag_configure("muted", foreground=c.FG_MUTED, font=f.SMALL)


def _build_kpi_area(app):
    """构建 KPI 卡片区"""
    from .theme import Colors, Fonts

    kpi_frame = ttk.Frame(app.content_frame)
    kpi_frame.pack(fill="x", padx=4, pady=4)

    app.kpi_labels = {}
    app.kpi_sparklines = {}

    kpi_items = [
        ("price", "股价"), ("change", "涨跌幅"),
        ("pe", "PE"), ("pb", "PB"),
        ("market_cap", "市值"), ("industry", "行业"),
    ]

    for key, label in kpi_items:
        card = ttk.Frame(kpi_frame, padding=4)
        card.pack(side="left", fill="both", expand=True, padx=2)

        ttk.Label(card, text=label, font=("Microsoft YaHei UI", 8), foreground="gray").pack()
        lbl = ttk.Label(card, text="--", font=("Microsoft YaHei UI", 12, "bold"))
        lbl.pack()
        app.kpi_labels[key] = lbl

        sf = ttk.Frame(card, height=20)
        sf.pack(fill="x")
        app.kpi_sparklines[key] = sf
