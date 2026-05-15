"""
财务分析系统 v9.0 - 主应用类
设计规范: Data-Dense Financial Dashboard
  - 布局: 侧边栏 + 顶部输入 + KPI卡片区 + 主内容区 + 状态栏
  - 交互: 悬停反馈 150ms + 状态指示 + 进度条
  - 无障碍: 键盘导航 + 高对比度
"""
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import traceback
from datetime import datetime
from pathlib import Path

from ..config import (
    APP_VERSION, CONFIG_FILE, DEFAULT_DATA_SOURCE, DEFAULT_START_DATE,
    AUTO_SAVE_DIR, TABLE_DISPLAY_ROWS,
)
from ..logging_config import get_logger
from ..cache.manager import DataCacheManager
from ..tokens.manager import TokenManager
from ..data_sources.adapter import DataSourceAdapter
from ..utils.export import DataExporter
from ..analyzers.market import MarketAnalyzer
from ..analyzers.technical import TechnicalAnalyzer
from ..analyzers.financial import FinancialStatementAnalyzer
from ..analyzers.profitability import ProfitabilityAnalyzer
from ..analyzers.combined import CombinedAnalyzer
from ..analyzers.risk_analyzer import RiskAnalyzer
from ..analyzers.deep_analysis import DeepAnalyzer
from ..analyzers.phase2_analysis import Phase2Analyzer
from .theme import Colors, Fonts, Spacing, apply_custom_style, BOOTSTRAP_THEME
from .dialogs import (
    TokenConfigDialog, CacheSettingsDialog, ExportDialog,
    DataSourceDialog, AboutDialog,
)
from .deepseek_dialog import DeepSeekPanel

logger = get_logger(__name__)

try:
    import ttkbootstrap as ttk
    from ttkbootstrap.constants import *
    HAS_BOOTSTRAP = True
except ImportError:
    from tkinter import ttk
    HAS_BOOTSTRAP = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from ..charts import (
        create_candlestick_chart, create_ma_chart, create_bar_chart,
        create_sparkline_chart, create_area_chart, create_percentage_bar_chart,
        create_multi_metric_dashboard, create_market_overview_chart, show_charts,
    )
    HAS_CHARTS = True
except ImportError:
    HAS_CHARTS = False


def _load_config():
    import json
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config_patch(patch: dict):
    import json
    config = _load_config()
    config.update(patch)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ============================================================================
# 侧边栏导航 - 分组折叠式
# ============================================================================
SIDEBAR_SECTIONS = [
    ("行情分析", [
        ("📊", "行情概览", "market_overview"),
        ("📈", "价格趋势", "price_trend"),
        ("📉", "技术指标", "technical"),
        ("💹", "K线图表", "candlestick"),
    ]),
    ("财务报表", [
        ("📋", "利润表", "income_statement"),
        ("📑", "资产负债表", "balance_sheet"),
        ("💰", "现金流量表", "cashflow"),
    ]),
    ("能力分析", [
        ("🏭", "盈利能力", "profitability"),
        ("⚙️", "营运能力", "operational"),
        ("🛡️", "偿债能力", "solvency"),
        ("🌱", "成长能力", "growth"),
    ]),
    ("综合评估", [
        ("🔗", "量价结合", "combined"),
        ("⚠️", "风险评估", "risk"),
    ]),
    ("财务比率", [
        ("📊", "财务比率分析", "ratio_analysis"),
    ]),
    ("财务审计", [
        ("🏦", "资产端信号", "audit_asset"),
        ("💹", "利润端信号", "audit_profit"),
        ("💸", "现金流信号", "audit_cashflow"),
        ("🔗", "勾稽关系验证", "audit_cross"),
        ("🚨", "综合审计报告", "audit_full"),
    ]),
    ("AI投研", [
        ("🤖", "AI 智能分析", "ai"),
        ("🔬", "三方辩论投研", "research_debate"),
        ("📋", "AI体检报告", "research_health"),
        ("🔍", "矛盾信号检测", "research_signals"),
    ]),
    ("深度分析", [
        ("🔬", "杜邦分析", "dupont"),
        ("🏦", "Z-score", "zscore"),
        ("📊", "F-score", "fscore"),
        ("🔍", "M-score", "mscore"),
        ("💰", "自由现金流", "fcf"),
        ("🔄", "现金流象限", "quadrant"),
        ("🏰", "护城河评估", "moat"),
        ("📋", "综合深度报告", "deep_comprehensive"),
    ]),
    ("估值与质量", [
        ("🏢", "行业对比", "peer"),
        ("📐", "相对估值", "valuation"),
        ("💎", "股东回报", "shareholder"),
        ("✅", "财报质量", "quality"),
    ]),
]


class FinancialAnalyzerApp:
    """财务分析系统主应用"""

    def __init__(self, root):
        self.root = root
        self.root.title(f"财务分析系统 Pro v{APP_VERSION}")
        self.root.minsize(Spacing.WINDOW_MIN_W, Spacing.WINDOW_MIN_H)
        self.root.geometry(f"{Spacing.WINDOW_DEFAULT_W}x{Spacing.WINDOW_DEFAULT_H}")
        self.root.configure(bg=Colors.BG_PRIMARY)

        # 居中
        self._center_window(Spacing.WINDOW_DEFAULT_W, Spacing.WINDOW_DEFAULT_H)

        # 应用样式
        if HAS_BOOTSTRAP:
            style = ttk.Style()
            apply_custom_style(style)

        # 核心组件
        self.cache_manager = DataCacheManager()
        self.token_manager = TokenManager()
        self.data_adapter = DataSourceAdapter(self.cache_manager)

        # 加载已保存的 Token 并初始化数据源
        config = _load_config()
        tushare_token = config.get("tushare")
        if tushare_token:
            self.data_adapter.set_tushare_token(tushare_token)
            self.token_manager.set_token("tushare", tushare_token)
            logger.info("已从配置加载 Tushare Token")

        # 也检查 token_manager 从 keyring/环境变量加载的 token
        saved_token = self.token_manager.get_token("tushare")
        if saved_token and not tushare_token:
            self.data_adapter.set_tushare_token(saved_token)
            logger.info("已从安全存储加载 Tushare Token")

        # 默认数据源：tushare token 已配置时优先使用，否则用开源接口
        if self.data_adapter.tushare_pro:
            self.data_adapter.set_active_source("tushare")
            logger.info("默认数据源: tushare (Token 已配置)")
        elif self.data_adapter.data_sources.get("akshare"):
            try:
                import requests
                resp = requests.get("https://push2his.eastmoney.com/", timeout=5)
                self.data_adapter.set_active_source("akshare")
                logger.info("默认数据源: akshare (开源)")
            except Exception:
                self.data_adapter.set_active_source("sina")
                logger.info("默认数据源: sina (开源)")
        else:
            self.data_adapter.set_active_source("sina")
            logger.info("默认数据源: sina (开源)")

        # 状态
        self._current_data = {}
        self._current_stock = ""
        self._analysis_running = False
        self._active_sidebar = None
        self._sidebar_buttons = {}
        self._section_expanded = {}  # 折叠状态

        # 构建 UI
        self._build_ui()
        self._update_clock()
        self._show_welcome()

        logger.info("财务分析系统启动完成")

    def _center_window(self, w, h):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ========================================================================
    # UI 构建
    # ========================================================================
    def _build_ui(self):
        c = Colors
        f = Fonts
        s = Spacing

        # 主容器
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True)

        # 侧边栏
        self._build_sidebar(main)

        # 右侧
        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True)

        # 顶部输入栏
        self._build_top_bar(right)

        # KPI 卡片行
        self._build_kpi_bar(right)

        # 主内容区
        self._build_content_area(right)

        # 状态栏
        self._build_status_bar(right)

    def _build_sidebar(self, parent):
        c = Colors
        f = Fonts
        s = Spacing

        sidebar = tk.Frame(parent, bg=c.BG_SECONDARY, width=s.SIDEBAR_WIDTH)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # ---- Logo 区 ----
        logo = tk.Frame(sidebar, bg=c.BG_SECONDARY)
        logo.pack(fill="x", pady=(s.XL, s.MD), padx=s.LG)

        tk.Label(logo, text="FA", font=f.TITLE,
                 bg=c.BG_SECONDARY, fg=c.ACCENT).pack(anchor="w")
        tk.Label(logo, text=f"v{APP_VERSION}", font=f.SMALL,
                 bg=c.BG_SECONDARY, fg=c.FG_MUTED).pack(anchor="w", pady=(2, 0))

        # 分隔线
        tk.Frame(sidebar, bg=c.BORDER_LIGHT, height=2).pack(fill="x", padx=s.LG, pady=(s.SM, s.MD))

        # ---- 导航区（可滚动） ----
        nav_canvas = tk.Canvas(sidebar, bg=c.BG_SECONDARY, highlightthickness=0, borderwidth=0)
        nav_scrollbar = tk.Scrollbar(sidebar, orient="vertical", command=nav_canvas.yview)
        self._nav_frame = tk.Frame(nav_canvas, bg=c.BG_SECONDARY)

        self._nav_frame.bind("<Configure>",
                             lambda e: nav_canvas.configure(scrollregion=nav_canvas.bbox("all")))
        nav_canvas.create_window((0, 0), window=self._nav_frame, anchor="nw", tags="nav_frame")
        nav_canvas.configure(yscrollcommand=nav_scrollbar.set)

        # 让 nav_frame 跟随 canvas 宽度
        nav_canvas.bind("<Configure>",
                        lambda e: nav_canvas.itemconfig("nav_frame", width=e.width))

        nav_canvas.pack(side="left", fill="both", expand=True)
        nav_scrollbar.pack(side="right", fill="y")

        # 鼠标滚轮支持 - 仅在鼠标悬停侧边栏时生效
        def _on_mousewheel(event):
            # 只在鼠标位于 sidebar 区域内时滚动
            try:
                widget = event.widget
                # 检查事件源是否在 sidebar 内
                w = widget
                while w is not None:
                    if w == sidebar:
                        nav_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                        return
                    w = w.master
            except Exception:
                pass

        def _bind_mousewheel(event):
            self.root.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            self.root.unbind_all("<MouseWheel>")

        sidebar.bind("<Enter>", _bind_mousewheel)
        sidebar.bind("<Leave>", _unbind_mousewheel)

        # 构建导航分组（可折叠）
        for section_name, items in SIDEBAR_SECTIONS:
            self._build_section(section_name, items)

        # ---- 底部设置区 ----
        tk.Frame(sidebar, bg=c.BORDER_LIGHT, height=2).pack(fill="x", padx=s.LG, pady=s.SM, side="bottom")
        bottom = tk.Frame(sidebar, bg=c.BG_SECONDARY)
        bottom.pack(fill="x", side="bottom", pady=(0, s.MD))

        for icon, label, cmd in [
            ("🔑", "Token 配置", self._show_token_dialog),
            ("📡", "数据源管理", self._show_datasource_dialog),
            ("⚙️", "缓存设置", self._show_cache_dialog),
            ("ℹ️", "关于", self._show_about_dialog),
        ]:
            btn = tk.Button(
                bottom, text=f"  {icon}  {label}", font=f.SMALL,
                bg=c.BG_SECONDARY, fg=c.FG_MUTED, activebackground=c.BG_HOVER,
                activeforeground=c.FG_PRIMARY, relief="flat", anchor="w",
                padx=s.LG, pady=6, cursor="hand2", command=cmd,
            )
            btn.pack(fill="x", padx=s.XS)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=c.BG_HOVER))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=c.BG_SECONDARY))

    def _build_section(self, section_name, items):
        """构建可折叠的导航分组"""
        c = Colors
        f = Fonts
        s = Spacing

        container = tk.Frame(self._nav_frame, bg=c.BG_SECONDARY)
        container.pack(fill="x", padx=s.XS, pady=(s.SM, 0))

        # 分组标题（点击折叠/展开）
        header = tk.Frame(container, bg=c.BG_SECONDARY)
        header.pack(fill="x")

        # 折叠箭头
        self._section_expanded[section_name] = tk.BooleanVar(value=True)
        arrow_var = self._section_expanded[section_name]

        arrow_label = tk.Label(header, text="▼", font=f.TINY,
                               bg=c.BG_SECONDARY, fg=c.FG_MUTED, width=2)
        arrow_label.pack(side="left", padx=(s.SM, 0))

        title_label = tk.Label(header, text=section_name, font=f.BODY_BOLD,
                               bg=c.BG_SECONDARY, fg=c.FG_MUTED, anchor="w")
        title_label.pack(side="left", fill="x", expand=True)

        # 子项容器
        items_frame = tk.Frame(container, bg=c.BG_SECONDARY)
        items_frame.pack(fill="x", pady=(s.XS, 0))

        for icon, label, key in items:
            btn = tk.Button(
                items_frame, text=f"    {icon}  {label}", font=f.SIDEBAR_ITEM,
                bg=c.BG_SECONDARY, fg=c.FG_SECONDARY, activebackground=c.BG_HOVER,
                activeforeground=c.ACCENT, relief="flat", anchor="w",
                padx=s.LG, pady=7, cursor="hand2",
                command=lambda k=key: self._on_sidebar_click(k),
            )
            btn.pack(fill="x", pady=1)
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=c.BG_HOVER) if b != self._active_sidebar else None)
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=c.BG_SECONDARY) if b != self._active_sidebar else None)
            self._sidebar_buttons[key] = btn

        # 折叠/展开功能
        def toggle():
            if items_frame.winfo_viewable():
                items_frame.pack_forget()
                arrow_label.config(text="▶")
            else:
                items_frame.pack(fill="x", pady=(s.XS, 0))
                arrow_label.config(text="▼")

        for widget in [header, arrow_label, title_label]:
            widget.bind("<Button-1>", lambda e: toggle())
            widget.bind("<Enter>", lambda e: header.config(bg=c.BG_HOVER))
            widget.bind("<Leave>", lambda e: header.config(bg=c.BG_SECONDARY))
            widget.configure(cursor="hand2")

    def _build_top_bar(self, parent):
        c = Colors
        f = Fonts
        s = Spacing

        bar = ttk.Frame(parent)
        bar.pack(fill="x", padx=s.LG, pady=(s.MD, 0))

        # 左侧：输入组
        left = ttk.Frame(bar)
        left.pack(side="left", fill="x", expand=True)

        # 股票代码
        ttk.Label(left, text="股票代码", font=f.BODY_BOLD, foreground=c.FG_MUTED).pack(side="left")
        self.stock_var = tk.StringVar()
        stock_entry = ttk.Entry(left, textvariable=self.stock_var, font=f.INPUT, width=18)
        stock_entry.pack(side="left", padx=(s.SM, s.LG))
        stock_entry.bind("<Return>", lambda e: self._run_analysis())

        # 数据源
        ttk.Label(left, text="数据源", font=f.BODY_BOLD, foreground=c.FG_MUTED).pack(side="left")
        available = self.data_adapter.get_available_sources()
        self.source_var = tk.StringVar(value=self.data_adapter.active_source)
        src_combo = ttk.Combobox(left, textvariable=self.source_var, values=available,
                                state="readonly", width=10, font=f.INPUT)
        src_combo.pack(side="left", padx=(s.SM, s.LG))
        src_combo.bind("<<ComboboxSelected>>", lambda e: self._switch_source())

        # 起始日期
        ttk.Label(left, text="起始日期", font=f.BODY_BOLD, foreground=c.FG_MUTED).pack(side="left")
        self.date_var = tk.StringVar(value=DEFAULT_START_DATE)
        ttk.Entry(left, textvariable=self.date_var, font=f.INPUT, width=10).pack(side="left", padx=(s.SM, 0))

        # 右侧：按钮组
        right = ttk.Frame(bar)
        right.pack(side="right")

        ttk.Button(right, text="📥 获取数据", style="Accent.TButton",
                   command=self._fetch_data_only).pack(side="left", padx=(0, s.SM))
        ttk.Button(right, text="🔍 分析", style="Accent.TButton",
                   command=self._run_analysis).pack(side="left", padx=(0, s.SM))
        ttk.Button(right, text="📤 导出", command=self._show_export_dialog).pack(side="left", padx=(0, s.SM))
        ttk.Button(right, text="🔑", command=self._show_token_dialog).pack(side="left", padx=(0, s.SM))
        ttk.Button(right, text="🗑️", command=self._clear_results).pack(side="left")

    def _build_kpi_bar(self, parent):
        """KPI 指标卡片行 - 数据仪表盘核心 + Sparkline"""
        c = Colors
        f = Fonts
        s = Spacing

        self.kpi_frame = ttk.Frame(parent)
        self.kpi_frame.pack(fill="x", padx=s.LG, pady=(s.MD, 0))

        self.kpi_labels = {}
        self.kpi_sparklines = {}  # sparkline canvas 引用
        self.kpi_cards = {}  # 卡片引用（用于悬停变色）
        kpi_items = [
            ("stock_name", "股票名称", "--"),
            ("current_price", "当前价格", "--"),
            ("price_change", "涨跌幅", "--"),
            ("volume", "成交量", "--"),
            ("pe_ratio", "市盈率", "--"),
            ("market_cap", "总市值", "--"),
        ]

        for key, label, default in kpi_items:
            card = tk.Frame(self.kpi_frame, bg=c.BG_CARD, padx=s.MD, pady=s.SM)
            card.pack(side="left", fill="both", expand=True, padx=(0, s.SM))
            self.kpi_cards[key] = card

            # 顶部行：标签 + 趋势箭头
            top_row = tk.Frame(card, bg=c.BG_CARD)
            top_row.pack(fill="x")

            lbl = tk.Label(top_row, text=label, font=f.KPI_LABEL, bg=c.BG_CARD, fg=c.FG_MUTED)
            lbl.pack(side="left")

            # 趋势标签（涨跌幅百分比，仅 price_change 卡片显示）
            trend_lbl = tk.Label(top_row, text="", font=(f.FAMILY_MONO[0], 8),
                                 bg=c.BG_CARD, fg=c.FG_MUTED)
            trend_lbl.pack(side="right")

            # 数值 + Sparkline 行
            val_row = tk.Frame(card, bg=c.BG_CARD)
            val_row.pack(fill="x", pady=(2, 0))

            val = tk.Label(val_row, text=default, font=f.KPI_VALUE, bg=c.BG_CARD, fg=c.FG_PRIMARY)
            val.pack(side="left")

            # Sparkline 占位（数据加载后填充）
            spark_frame = tk.Frame(val_row, bg=c.BG_CARD, width=s.SPARKLINE_W, height=s.SPARKLINE_H)
            spark_frame.pack(side="right", padx=(s.SM, 0))
            spark_frame.pack_propagate(False)
            self.kpi_sparklines[key] = spark_frame

            self.kpi_labels[key] = val
            # 存储 trend label 用于更新
            setattr(val, '_trend_label', trend_lbl)

            # 悬停效果
            card.bind("<Enter>", lambda e, cf=card: cf.configure(bg=Colors.BG_HOVER))
            card.bind("<Leave>", lambda e, cf=card: cf.configure(bg=Colors.BG_CARD))

    def _build_content_area(self, parent):
        c = Colors
        f = Fonts
        s = Spacing

        content = ttk.Frame(parent)
        content.pack(fill="both", expand=True, padx=s.LG, pady=s.MD)

        self.notebook = ttk.Notebook(content)
        self.notebook.pack(fill="both", expand=True)

        # Tab 1: 分析结果
        result_tab = ttk.Frame(self.notebook)
        self.notebook.add(result_tab, text="  📄 分析结果  ")

        text_wrap = ttk.Frame(result_tab)
        text_wrap.pack(fill="both", expand=True)

        self.result_text = tk.Text(
            text_wrap, font=f.RESULT, bg=c.BG_SECONDARY, fg=c.FG_PRIMARY,
            relief="flat", wrap="word", state="disabled", undo=False,
            spacing1=2, spacing3=2, padx=s.LG, pady=s.MD,
            insertbackground=c.ACCENT, selectbackground=c.ACCENT_SUBTLE,
            selectforeground=c.FG_PRIMARY,
        )
        result_sb = ttk.Scrollbar(text_wrap, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=result_sb.set)
        self.result_text.pack(side="left", fill="both", expand=True)
        result_sb.pack(side="right", fill="y")
        self._configure_result_tags()

        # Tab 2: 图表
        chart_tab = ttk.Frame(self.notebook)
        self.notebook.add(chart_tab, text="  📊 图表  ")

        if HAS_CHARTS:
            chart_toolbar = ttk.Frame(chart_tab)
            chart_toolbar.pack(fill="x", padx=s.SM, pady=s.SM)

            self.chart_type_var = tk.StringVar(value="K线图")
            # 基础图表
            basic_frame = ttk.LabelFrame(chart_toolbar, text="基础图表")
            basic_frame.pack(side="left", padx=(0, s.MD))
            for ct in ["K线图", "均线图", "柱状图", "面积走势", "多指标仪表盘", "涨跌对比"]:
                ttk.Radiobutton(basic_frame, text=ct, variable=self.chart_type_var,
                               value=ct, command=self._show_chart).pack(side="left", padx=s.XS)
            # 深度分析图表
            deep_frame = ttk.LabelFrame(chart_toolbar, text="深度分析图表")
            deep_frame.pack(side="left", padx=(0, s.MD))
            deep_charts = {
                "杜邦瀑布图": "dupont", "F-score雷达图": "fscore",
                "行业对比图": "peer", "估值仪表盘": "valuation",
            }
            for label, ctype in deep_charts.items():
                ttk.Button(deep_frame, text=label,
                          command=lambda ct=ctype: self._show_deep_chart(ct)).pack(side="left", padx=s.XS)

            ttk.Button(chart_toolbar, text="💾 保存", command=self._save_chart).pack(side="right")

            self.chart_container = ttk.Frame(chart_tab)
            self.chart_container.pack(fill="both", expand=True, padx=s.SM, pady=(0, s.SM))
            self._chart_canvas = None
        else:
            ttk.Label(chart_tab, text="📊 图表功能需要 matplotlib\npip install matplotlib",
                      font=f.SUBTITLE, foreground=c.FG_MUTED, justify="center").pack(expand=True)

        # Tab 3: AI 投研 (合并原AI分析 + AI深度投研)
        ai_tab = ttk.Frame(self.notebook)
        self.notebook.add(ai_tab, text="  🤖 AI 投研  ")
        # 内部用 notebook 做子标签
        ai_sub = ttk.Notebook(ai_tab)
        ai_sub.pack(fill="both", expand=True)
        # 子标签1: AI 智能分析
        ai_chat_frame = ttk.Frame(ai_sub)
        ai_sub.add(ai_chat_frame, text="  💬 AI 智能分析  ")
        self.ai_panel = DeepSeekPanel(
            ai_chat_frame,
            stock_code_getter=lambda: self.stock_var.get(),
            data_getter=lambda: getattr(self, '_current_data', None),
        )
        self.ai_panel.frame.pack(fill="both", expand=True)
        # 子标签2: 三方辩论投研
        try:
            from .research_panel import ResearchPanel
            research_frame = ttk.Frame(ai_sub)
            ai_sub.add(research_frame, text="  🔬 三方辩论投研  ")
            self.research_panel = ResearchPanel(
                research_frame,
                stock_code_getter=lambda: self.stock_var.get(),
                data_getter=lambda: getattr(self, '_current_data', None),
                app=self,
            )
        except Exception as e:
            logger.warning(f"AI深度投研面板加载失败: {e}")

        # Tab 4: 数据表格
        table_tab = ttk.Frame(self.notebook)
        self.notebook.add(table_tab, text="  📋 数据  ")
        self._build_table_view(table_tab)

    def _build_table_view(self, parent):
        c = Colors
        f = Fonts
        s = Spacing

        toolbar = ttk.Frame(parent)
        toolbar.pack(fill="x", padx=s.SM, pady=s.SM)
        ttk.Label(toolbar, text="数据类型:", font=f.BODY_BOLD).pack(side="left")
        self.table_type_var = tk.StringVar()
        self.table_type_combo = ttk.Combobox(toolbar, textvariable=self.table_type_var,
                                              state="readonly", width=15, font=f.INPUT)
        self.table_type_combo.pack(side="left", padx=s.SM)
        self.table_type_combo.bind("<<ComboboxSelected>>", lambda e: self._refresh_table())
        ttk.Button(toolbar, text="🔄 刷新", command=self._refresh_table).pack(side="left", padx=s.SM)

        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True, padx=s.SM, pady=(0, s.SM))

        self.data_tree = ttk.Treeview(table_frame, show="headings")
        sy = ttk.Scrollbar(table_frame, orient="vertical", command=self.data_tree.yview)
        sx = ttk.Scrollbar(table_frame, orient="horizontal", command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.data_tree.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

    def _configure_result_tags(self):
        c = Colors
        f = Fonts
        t = self.result_text
        t.tag_configure("heading", font=f.HEADING, foreground=c.ACCENT, spacing1=8, spacing3=4)
        t.tag_configure("section", font=f.BODY_BOLD, foreground=c.INFO, spacing1=6, spacing3=2)
        t.tag_configure("bold", font=f.BODY_BOLD)
        t.tag_configure("success", foreground=c.SUCCESS)
        t.tag_configure("danger", foreground=c.DANGER)
        t.tag_configure("warning", foreground=c.WARNING)
        t.tag_configure("info", foreground=c.INFO)
        t.tag_configure("muted", foreground=c.FG_MUTED, font=f.SMALL)

    def _build_status_bar(self, parent):
        c = Colors
        f = Fonts
        s = Spacing

        bar = ttk.Frame(parent)
        bar.pack(fill="x", padx=s.LG, pady=(0, s.SM))

        self.status_label = ttk.Label(bar, text="就绪", font=f.STATUS)
        self.status_label.pack(side="left")

        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=180)
        self.progress.pack(side="left", padx=s.MD)

        self.clock_label = ttk.Label(bar, text="", font=f.CLOCK)
        self.clock_label.pack(side="right")

        self.source_label = ttk.Label(bar, text=f"数据源: {self.data_adapter.active_source.upper()}",
                                       font=f.STATUS, foreground=c.FG_MUTED)
        self.source_label.pack(side="right", padx=(0, s.MD))

    # ========================================================================
    # KPI 更新
    # ========================================================================
    def _update_kpis(self, data: dict):
        c = Colors
        basic = data.get("basic")
        daily = data.get("daily")
        daily_basic = data.get("daily_basic")

        if basic is not None and not basic.empty:
            name = basic.iloc[0].get("name", "--")
            if name and name != "--":
                self.kpi_labels["stock_name"].config(text=name)
            else:
                # basic 数据无 name（如 tushare daily_basic），从新浪异步获取
                threading.Thread(target=self._fetch_name_async,
                                args=(self._current_stock,), daemon=True).start()

        if daily is not None and not daily.empty and "close" in daily.columns:
            current = daily["close"].iloc[0]
            prev = daily["close"].iloc[1] if len(daily) > 1 else current
            change_pct = (current - prev) / prev * 100 if prev else 0

            self.kpi_labels["current_price"].config(text=f"{current:.2f}")
            change_text = f"{change_pct:+.2f}%"
            change_color = c.SUCCESS if change_pct >= 0 else c.DANGER
            self.kpi_labels["price_change"].config(text=change_text, fg=change_color)

            # 更新趋势箭头
            trend_lbl = getattr(self.kpi_labels["price_change"], '_trend_label', None)
            if trend_lbl:
                arrow = "▲" if change_pct >= 0 else "▼"
                trend_lbl.config(text=f"{arrow} {abs(change_pct):.2f}%", fg=change_color)

            if "vol" in daily.columns:
                vol = daily["vol"].iloc[0]
                self.kpi_labels["volume"].config(text=f"{vol:,.0f}")

            # 更新 Sparkline 迷你图
            self._update_sparklines(data)

        # PE: 优先 daily_basic，回退 basic，最后后台获取
        pe = None
        if daily_basic is not None and not daily_basic.empty:
            pe = daily_basic.iloc[0].get("pe_ttm")
        if not pe and basic is not None and not basic.empty:
            pe = basic.iloc[0].get("pe") or basic.iloc[0].get("pe_ttm")
        if pe:
            try:
                self.kpi_labels["pe_ratio"].config(text=f"{float(pe):.1f}")
            except (ValueError, TypeError):
                pass
        else:
            # 后台获取 PE，不阻塞 UI
            threading.Thread(target=self._fetch_pe_async, args=(self._current_stock,), daemon=True).start()

        # 总市值: 优先 daily_basic，回退 basic
        total_mv = None
        if daily_basic is not None and not daily_basic.empty:
            total_mv = daily_basic.iloc[0].get("total_mv")
        if not total_mv and basic is not None and not basic.empty:
            total_mv = basic.iloc[0].get("total_mv")
        if total_mv:
            try:
                self.kpi_labels["market_cap"].config(text=f"{float(total_mv) / 1e4:.1f}亿")
            except (ValueError, TypeError):
                pass

    def _fetch_pe_from_spot(self, stock_code):
        """从雪球获取单只股票市盈率（轻量、快速）"""
        try:
            import akshare as ak
            # 转换代码格式: 000001.SZ -> SZ000001
            if "." in stock_code:
                parts = stock_code.split(".")
                xq_symbol = parts[1] + parts[0]  # SZ000001
            else:
                xq_symbol = stock_code

            df = ak.stock_individual_spot_xq(symbol=xq_symbol)
            if df is None or df.empty:
                return None
            # 列名经映射后是中文
            pe = df.iloc[0].get("市盈率(TTM)") or df.iloc[0].get("市盈率(动)") or df.iloc[0].get("pe_ttm")
            if pe is not None and str(pe) not in ("-", "None", "nan", "0"):
                return float(pe)
            return None
        except Exception as e:
            logger.debug(f"获取雪球PE失败: {e}")
            return None

    def _fetch_pe_async(self, stock_code):
        """后台线程获取 PE 并更新 KPI"""
        pe = self._fetch_pe_from_spot(stock_code)
        if pe:
            try:
                self.root.after(0, lambda: self.kpi_labels["pe_ratio"].config(text=f"{float(pe):.1f}"))
            except Exception:
                pass

    def _fetch_name_async(self, stock_code):
        """后台线程获取公司名称并更新 KPI（tushare basic 无 name 时使用）"""
        try:
            from ..data_sources import sina_source
            basic_df = sina_source.get_basic(stock_code)
            if basic_df is not None and not basic_df.empty:
                name = basic_df.iloc[0].get("name")
                if name:
                    self.root.after(0, lambda: self.kpi_labels["stock_name"].config(text=name))
        except Exception as e:
            logger.debug(f"获取公司名称失败: {e}")

    def _fetch_financial_data(self, stock_code, start_date, end_date, source):
        """后台线程获取财务报表数据（利润表/资产负债表/现金流量表/财务指标）"""
        fin_types = ["income", "balance", "cashflow", "financial", "fina_audit", "mainbz"]
        fetched = []
        for dtype in fin_types:
            if dtype in self._current_data:
                continue
            try:
                df = self.data_adapter.get_stock_data(stock_code, start_date, end_date, dtype)
                if df is not None and not df.empty:
                    self._current_data[dtype] = df
                    fetched.append(dtype)
                    logger.info(f"后台获取 {dtype} 成功: {len(df)} 行")
            except Exception as e:
                logger.debug(f"后台获取 {dtype} 失败: {e}")

        if fetched:
            logger.info(f"财务报表补充完成: {fetched}")
            self.root.after(0, self._update_table_types)

    def _reset_kpis(self):
        for key, lbl in self.kpi_labels.items():
            lbl.config(text="--", fg=Colors.FG_PRIMARY)
        # 清除 sparklines
        for key, frame in self.kpi_sparklines.items():
            for w in frame.winfo_children():
                w.destroy()

    def _update_sparklines(self, data: dict):
        """根据已获取数据更新 KPI 卡片的 Sparkline 迷你图"""
        if not HAS_CHARTS:
            return
        daily = data.get("daily")
        if daily is None or daily.empty or "close" not in daily.columns:
            return

        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        close = daily["close"].tolist()
        if len(close) < 5:
            return

        # 价格 sparkline
        self._embed_sparkline("current_price", close[-30:])

        # 成交量 sparkline
        if "vol" in daily.columns:
            vol = daily["vol"].tolist()
            self._embed_sparkline("volume", vol[-30:])

    def _embed_sparkline(self, key: str, values: list):
        """在 KPI 卡片中嵌入迷你趋势图"""
        if not HAS_CHARTS or not values or len(values) < 3:
            return
        frame = self.kpi_sparklines.get(key)
        if not frame:
            return

        # 清除旧内容
        for w in frame.winfo_children():
            w.destroy()

        try:
            import matplotlib
            matplotlib.use("Agg")
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

            fig = create_sparkline_chart(values, width=Spacing.SPARKLINE_W, height=Spacing.SPARKLINE_H)
            if fig:
                canvas = FigureCanvasTkAgg(fig, master=frame)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
                # 关闭 fig 释放内存
                import matplotlib.pyplot as plt
                plt.close(fig)
        except Exception as e:
            logger.debug(f"Sparkline 渲染失败 ({key}): {e}")

    # ========================================================================
    # 侧边栏交互
    # ========================================================================
    def _on_sidebar_click(self, key):
        if self._active_sidebar:
            self._active_sidebar.config(bg=Colors.BG_SECONDARY, fg=Colors.FG_SECONDARY)
        btn = self._sidebar_buttons.get(key)
        if btn:
            btn.config(bg=Colors.ACCENT_SUBTLE, fg=Colors.ACCENT)
            self._active_sidebar = btn

        if key == "ai":
            self.notebook.select(2)  # AI投研标签页
            return
        if key == "candlestick":
            self.notebook.select(1)  # 图表标签页
            return

        analysis_map = {
            "market_overview": self._analyze_market_overview,
            "price_trend": self._analyze_price_trend,
            "technical": self._analyze_technical,
            "income_statement": self._analyze_income,
            "balance_sheet": self._analyze_balance,
            "cashflow": self._analyze_cashflow,
            "profitability": self._analyze_profitability,
            "operational": self._analyze_operational,
            "solvency": self._analyze_solvency,
            "growth": self._analyze_growth,
            "combined": self._analyze_combined,
            "risk": self._analyze_risk,
            "dupont": self._analyze_dupont,
            "zscore": self._analyze_zscore,
            "fscore": self._analyze_fscore,
            "mscore": self._analyze_mscore,
            "fcf": self._analyze_fcf,
            "quadrant": self._analyze_quadrant,
            "moat": self._analyze_moat,
            "deep_comprehensive": self._analyze_deep_comprehensive,
            "peer": self._analyze_peer,
            "valuation": self._analyze_valuation,
            "shareholder": self._analyze_shareholder,
            "quality": self._analyze_quality,
            # 财务比率
            "ratio_analysis": self._analyze_ratio_analysis,
            # 财务审计
            "audit_asset": self._analyze_audit_asset,
            "audit_profit": self._analyze_audit_profit,
            "audit_cashflow": self._analyze_audit_cashflow,
            "audit_cross": self._analyze_audit_cross,
            "audit_full": self._analyze_audit_full,
            # AI投研
            "research_debate": self._start_research_debate,
            "research_health": self._show_health_report,
            "research_signals": self._show_signal_detection,
        }

        handler = analysis_map.get(key)
        if handler:
            self.notebook.select(0)
            if self._current_data:
                handler()
            else:
                self._set_result_text("⚠️ 请先输入股票代码并点击「分析」获取数据")

    # ========================================================================
    # 核心分析
    # ========================================================================
    def _run_analysis(self):
        stock_code = self.stock_var.get().strip()
        if not stock_code:
            messagebox.showwarning("提示", "请输入股票代码\n\n示例:\n  A股: 000001.SZ, 600519.SH\n  美股: AAPL, MSFT")
            return
        if self._analysis_running:
            return

        self._analysis_running = True
        self._current_stock = stock_code
        self._set_status("正在获取数据...")
        self.progress.start()
        self._clear_results()
        self._reset_kpis()

        threading.Thread(target=self._fetch_and_analyze, daemon=True).start()

    def _fetch_data_only(self):
        """仅获取数据，不自动运行分析"""
        stock_code = self.stock_var.get().strip()
        if not stock_code:
            messagebox.showwarning("提示", "请输入股票代码\n\n示例:\n  A股: 000001.SZ, 600519.SH\n  美股: AAPL, MSFT")
            return
        if self._analysis_running:
            return

        self._analysis_running = True
        self._current_stock = stock_code
        self._set_status("正在获取数据...")
        self.progress.start()

        def do_fetch(sc=stock_code):
            try:
                source = self.source_var.get()
                effective_source = self._resolve_source(source, sc)
                self.data_adapter.set_active_source(effective_source)
                start_date = self.date_var.get().strip() or DEFAULT_START_DATE
                end_date = datetime.now().strftime("%Y%m%d")

                self.root.after(0, self._set_status, f"正在从 {effective_source.upper()} 获取 {sc} 数据...")

                data = {}
                for dtype in ["daily", "daily_basic", "basic", "stock_basic"]:
                    try:
                        df = self.data_adapter.get_stock_data(sc, start_date, end_date, dtype)
                        if df is not None and not df.empty:
                            data[dtype] = df
                    except Exception as e:
                        logger.warning(f"获取 {dtype} 失败: {e}")

                if not data:
                    # 按优先级构建回退列表
                    fallbacks = []
                    if self.data_adapter.tushare_pro and effective_source != "tushare":
                        fallbacks.append("tushare")
                    if effective_source != "akshare" and "akshare" in self.data_adapter.get_available_sources():
                        fallbacks.append("akshare")
                    if effective_source != "sina":
                        fallbacks.append("sina")
                    if effective_source != "yfinance" and "yfinance" in self.data_adapter.get_available_sources():
                        fallbacks.append("yfinance")

                    for fb in fallbacks:
                        if fb == effective_source:
                            continue
                        if fb == "tushare" and not self.data_adapter.tushare_pro:
                            continue
                        self.data_adapter.set_active_source(fb)
                        fb_code = sc.replace(".SH", ".SS") if fb == "yfinance" else sc
                        for dtype in ["daily", "daily_basic", "basic", "stock_basic"]:
                            try:
                                df = self.data_adapter.get_stock_data(fb_code, start_date, end_date, dtype)
                                if df is not None and not df.empty:
                                    data[dtype] = df
                            except Exception:
                                pass
                        if data:
                            sc = fb_code
                            self._current_stock = sc
                            effective_source = fb
                            break

                if not data:
                    error_msg = self._diagnose_fetch_error(sc, source)
                    self.root.after(0, self._on_fetch_error, error_msg)
                    return

                self._current_data = data
                # 刷新AI上下文
                if hasattr(self, 'ai_panel') and self.ai_panel:
                    self.ai_panel.refresh_context()
                DataExporter.auto_save(data, sc)
                self.root.after(0, lambda: self.source_label.config(text=f"数据源: {effective_source.upper()}"))
                self.root.after(0, self._on_fetch_complete, sc)

                # 后台补充财务报表数据
                threading.Thread(target=self._fetch_financial_data,
                               args=(sc, start_date, end_date, effective_source), daemon=True).start()

            except Exception as e:
                logger.error(f"数据获取失败: {e}")
                self.root.after(0, self._on_fetch_error, str(e))

        threading.Thread(target=do_fetch, daemon=True).start()

    def _on_fetch_complete(self, stock_code):
        """数据获取完成（仅获取，不分析）"""
        self._analysis_running = False
        self.progress.stop()
        self._set_status(f"✅ {stock_code} 数据获取完成")
        self._update_kpis(self._current_data)
        self._update_table_types()
        self._set_result_text(f"✅ 数据获取完成\n\n已获取: {', '.join(self._current_data.keys())}\n"
                             f"股票代码: {stock_code}\n\n"
                             f"⏳ 正在后台加载财务报表（利润表/资产负债表/现金流量表）...\n"
                             f"加载完成后可在「数据」标签页查看，导出时自动包含。\n\n"
                             f"点击左侧菜单选择分析类型，或点击「分析」按钮运行综合分析。")

    def _fetch_and_analyze(self):
        try:
            stock_code = self._current_stock
            source = self.source_var.get()
            start_date = self.date_var.get().strip() or DEFAULT_START_DATE
            end_date = datetime.now().strftime("%Y%m%d")

            # 自动选择可用数据源
            effective_source = self._resolve_source(source, stock_code)
            self.data_adapter.set_active_source(effective_source)

            self.root.after(0, self._set_status, f"正在从 {effective_source.upper()} 获取 {stock_code} 数据...")

            data = {}
            for dtype in ["daily", "daily_basic", "basic", "stock_basic"]:
                try:
                    df = self.data_adapter.get_stock_data(stock_code, start_date, end_date, dtype)
                    if df is not None and not df.empty:
                        data[dtype] = df
                        logger.info(f"获取 {dtype} 成功: {len(df)} 行")
                except Exception as e:
                    logger.warning(f"获取 {dtype} 失败: {e}")

            # 主数据源失败时，按优先级尝试其他数据源
            if not data:
                # 构建回退列表（排除已尝试的）
                fallbacks = []
                if self.data_adapter.tushare_pro and effective_source != "tushare":
                    fallbacks.append("tushare")
                if effective_source != "akshare" and "akshare" in self.data_adapter.get_available_sources():
                    fallbacks.append("akshare")
                if effective_source != "sina":
                    fallbacks.append("sina")
                if effective_source != "yfinance" and "yfinance" in self.data_adapter.get_available_sources():
                    fallbacks.append("yfinance")

                for fb in fallbacks:
                    if data:
                        break
                    logger.info(f"{effective_source} 未获取到数据，尝试 {fb} 回退")
                    self.root.after(0, self._set_status, f"正在尝试 {fb.upper()} 回退...")
                    self.data_adapter.set_active_source(fb)
                    effective_source = fb
                    fb_code = stock_code.replace(".SH", ".SS") if fb == "yfinance" else stock_code
                    for dtype in ["daily", "daily_basic", "basic", "stock_basic"]:
                        try:
                            df = self.data_adapter.get_stock_data(fb_code, start_date, end_date, dtype)
                            if df is not None and not df.empty:
                                data[dtype] = df
                                logger.info(f"{fb} 回退获取 {dtype} 成功: {len(df)} 行")
                        except Exception as e:
                            logger.warning(f"{fb} 回退获取 {dtype} 失败: {e}")
                    if data and fb_code != stock_code:
                        stock_code = fb_code
                        self._current_stock = fb_code

            if not data:
                error_msg = self._diagnose_fetch_error(stock_code, source)
                self.root.after(0, self._on_fetch_error, error_msg)
                return

            self._current_data = data
            DataExporter.auto_save(data, stock_code)

            # 后台补充财务报表数据
            threading.Thread(target=self._fetch_financial_data,
                           args=(stock_code, start_date, end_date, effective_source), daemon=True).start()

            # 更新状态栏数据源显示
            self.root.after(0, lambda: self.source_label.config(text=f"数据源: {effective_source.upper()}"))
            self.root.after(0, self._set_status, "正在生成分析报告...")

            # 运行行情概览
            analyzer = MarketAnalyzer(data, stock_code, self.data_adapter, self.cache_manager)
            result = analyzer.analyze_market_overview()

            # 同时获取技术指标摘要
            try:
                tech = TechnicalAnalyzer(data, stock_code, self.data_adapter, self.cache_manager)
                tech_result = tech.analyze_technical_indicators()
                if tech_result and "无价格数据" not in tech_result:
                    result += "\n\n" + tech_result
            except Exception as e:
                logger.warning(f"技术指标分析失败: {e}")

            self.root.after(0, self._on_analysis_complete, result, stock_code)

        except Exception as e:
            logger.error(f"分析失败: {e}\n{traceback.format_exc()}")
            self.root.after(0, self._on_fetch_error, str(e))

    def _resolve_source(self, source, stock_code):
        """检查数据源是否可用，不可用时返回最佳替代
        优先级：tushare（有Token时） > akshare > sina > yfinance
        """
        available = self.data_adapter.get_available_sources()

        # tushare 有 Token 时最优先（A股数据最全、最规范）
        if self.data_adapter.tushare_pro and "tushare" in available:
            return "tushare"

        # 美股/港股优先用 yfinance
        _us_suffixes = ("", )
        _hk_suffixes = (".HK",)
        if stock_code.endswith(_hk_suffixes) or ("." not in stock_code and stock_code.isupper()):
            if "yfinance" in available:
                return "yfinance"

        # A股优先用 akshare（免费、无需 Token）
        if "akshare" in available:
            return "akshare"

        # 回退到 sina
        if "sina" in available:
            return "sina"

        # 最后尝试 yfinance
        if "yfinance" in available:
            return "yfinance"

        return source

    def _diagnose_fetch_error(self, stock_code, source):
        """诊断数据获取失败原因"""
        errors = ["❌ 所有数据源均未获取到数据", "", "已尝试的数据源:"]

        available = self.data_adapter.get_available_sources()
        for src in available:
            errors.append(f"  • {src.upper()} - 失败")

        errors.append("")
        errors.append("可能的原因:")

        if not self.data_adapter.tushare_pro:
            errors.append("  1. Tushare Token 未配置（侧边栏 → Token 配置）")

        errors.append(f"  2. 股票代码格式不正确")
        errors.append(f"     当前代码: {stock_code}")
        errors.append(f"     A股格式: 000001.SZ, 600519.SH")
        errors.append(f"     美股格式: AAPL, MSFT")
        errors.append(f"     港股格式: 0700.HK")
        errors.append("  3. 网络连接问题")
        errors.append("  4. 股票代码不存在或已退市")

        errors.append("")
        errors.append("建议:")
        errors.append("  • 先配置 Tushare Token 以获取 A股 数据")
        errors.append("  • 美股可直接用 yfinance（无需 Token）")
        errors.append("  • 检查网络连接是否正常")

        return "\n".join(errors)

    def _on_analysis_complete(self, result, stock_code):
        self._analysis_running = False
        self.progress.stop()
        self._set_status(f"✅ {stock_code} 分析完成")
        self._set_result_text(result)
        self.notebook.select(0)
        self._update_kpis(self._current_data)
        self._update_table_types()

        basic = self._current_data.get("basic")
        if basic is not None and not basic.empty:
            name = basic.iloc[0].get("name", "")
            self.ai_panel.set_stock_context(stock_code, name)

    def _on_fetch_error(self, error_msg):
        self._analysis_running = False
        self.progress.stop()
        self._set_status(f"❌ 数据获取失败")
        self._set_result_text(f"❌ 数据获取失败\n\n{error_msg}")

    # ========================================================================
    # 各分析模块
    # ========================================================================
    def _run_analyzer(self, analyzer_class, method_name, label):
        if not self._current_data:
            self._set_result_text("⚠️ 请先输入股票代码并点击「分析」获取数据")
            return
        self._set_status(f"正在分析 {label}...")
        self.progress.start()

        def do():
            try:
                a = analyzer_class(self._current_data, self._current_stock, self.data_adapter, self.cache_manager)
                # 检查方法是否存在
                if not hasattr(a, method_name):
                    self.root.after(0, self._on_single_analysis,
                                   f"❌ {label} 分析方法未实现: {method_name}", label)
                    return
                result = getattr(a, method_name)()
                self.root.after(0, self._on_single_analysis, result, label)
            except Exception as e:
                logger.error(f"{label} 分析失败: {e}\n{traceback.format_exc()}")
                self.root.after(0, self._on_single_analysis, f"❌ {label}分析失败: {e}", label)

        threading.Thread(target=do, daemon=True).start()

    def _on_single_analysis(self, result, label):
        self.progress.stop()
        self._set_status(f"✅ {label} 完成")
        self._set_result_text(result)
        self.notebook.select(0)

    def _analyze_market_overview(self): self._run_analyzer(MarketAnalyzer, "analyze_market_overview", "行情概览")
    def _analyze_price_trend(self): self._run_analyzer(MarketAnalyzer, "analyze_price_trend", "价格趋势")
    def _analyze_technical(self): self._run_analyzer(TechnicalAnalyzer, "analyze_technical_indicators", "技术指标")
    def _analyze_income(self): self._run_analyzer(FinancialStatementAnalyzer, "analyze_income_statement", "利润表")
    def _analyze_balance(self): self._run_analyzer(FinancialStatementAnalyzer, "analyze_balance_sheet", "资产负债表")
    def _analyze_cashflow(self): self._run_analyzer(FinancialStatementAnalyzer, "analyze_cashflow_statement", "现金流量表")
    def _analyze_profitability(self): self._run_analyzer(ProfitabilityAnalyzer, "analyze_profitability", "盈利能力")
    def _analyze_operational(self): self._run_analyzer(ProfitabilityAnalyzer, "analyze_operation_ability", "营运能力")
    def _analyze_solvency(self): self._run_analyzer(ProfitabilityAnalyzer, "analyze_solvency", "偿债能力")
    def _analyze_growth(self): self._run_analyzer(ProfitabilityAnalyzer, "analyze_growth_ability", "成长能力")
    def _analyze_combined(self): self._run_analyzer(CombinedAnalyzer, "analyze_price_financial_combined", "量价结合")
    def _analyze_risk(self): self._run_analyzer(RiskAnalyzer, "generate_risk_warning_report", "风险评估")
    def _analyze_dupont(self): self._run_analyzer(DeepAnalyzer, "analyze_dupont", "杜邦分析")
    def _analyze_zscore(self): self._run_analyzer(DeepAnalyzer, "analyze_zscore", "Z-score")
    def _analyze_fscore(self): self._run_analyzer(DeepAnalyzer, "analyze_fscore", "F-score")
    def _analyze_mscore(self): self._run_analyzer(DeepAnalyzer, "analyze_mscore", "M-score")
    def _analyze_fcf(self): self._run_analyzer(DeepAnalyzer, "analyze_free_cashflow", "自由现金流")
    def _analyze_quadrant(self): self._run_analyzer(DeepAnalyzer, "analyze_cashflow_quadrant", "现金流象限")
    def _analyze_moat(self): self._run_analyzer(DeepAnalyzer, "analyze_moat", "护城河评估")
    def _analyze_deep_comprehensive(self): self._run_analyzer(DeepAnalyzer, "generate_comprehensive_report", "综合深度报告")
    def _run_phase2(self, method_name, label):
        """Phase2Analyzer专用调用（不传cache_manager）"""
        if not self._current_data:
            self._set_result_text("⚠️ 请先输入股票代码并点击「分析」获取数据")
            return
        self._set_status(f"正在分析 {label}...")
        self.progress.start()

        def do():
            try:
                a = Phase2Analyzer(self._current_data, self._current_stock, self.data_adapter)
                # 对于需要额外参数的方法，使用 analyze() 统一入口
                if method_name == "compare_with_peers":
                    result = a.analyze()  # analyze() 内部处理行业对比
                elif hasattr(a, method_name):
                    result = getattr(a, method_name)()
                else:
                    self.root.after(0, self._on_single_analysis,
                                   f"❌ {label} 分析方法未实现: {method_name}", label)
                    return
                self.root.after(0, self._on_single_analysis, result, label)
            except Exception as e:
                logger.error(f"{label} 分析失败: {e}\n{traceback.format_exc()}")
                self.root.after(0, self._on_single_analysis, f"❌ {label}分析失败: {e}", label)

        threading.Thread(target=do, daemon=True).start()

    def _analyze_peer(self): self._run_phase2("compare_with_peers", "行业对比")
    def _analyze_valuation(self): self._run_phase2("valuation_analysis", "相对估值")
    def _analyze_shareholder(self): self._run_phase2("shareholder_return_analysis", "股东回报")
    def _analyze_quality(self): self._run_phase2("financial_quality_analysis", "财报质量")

    # ========================================================================
    # 财务比率分析
    # ========================================================================
    def _analyze_ratio_analysis(self):
        """财务比率综合分析"""
        if not self._current_data:
            self._set_result_text("请先获取数据")
            return
        self.progress.start()
        self._set_status("正在分析财务比率...")

        def do():
            try:
                from ..analyzers.financial_ratios import FinancialRatioAnalyzer
                a = FinancialRatioAnalyzer(self._current_data, self.stock_var.get())
                result = a.analyze()
                self.root.after(0, self._on_single_analysis, result, "财务比率分析")
            except Exception as e:
                logger.error(f"财务比率分析失败: {e}\n{traceback.format_exc()}")
                self.root.after(0, self._on_single_analysis, f"❌ 财务比率分析失败: {e}", "财务比率分析")

        threading.Thread(target=do, daemon=True).start()

    # ========================================================================
    # 财务审计
    # ========================================================================
    def _analyze_audit_asset(self):
        self._run_audit_analyzer("资产端信号", "asset_signals")

    def _analyze_audit_profit(self):
        self._run_audit_analyzer("利润端信号", "profit_signals")

    def _analyze_audit_cashflow(self):
        self._run_audit_analyzer("现金流信号", "cashflow_signals")

    def _analyze_audit_cross(self):
        self._run_audit_analyzer("勾稽关系验证", "cross_validation")

    def _analyze_audit_full(self):
        self._run_audit_analyzer("综合审计报告", "run_full_audit")

    def _run_audit_analyzer(self, label, method):
        """运行财务审计分析"""
        if not self._current_data:
            self._set_result_text("请先获取数据")
            return
        self.progress.start()
        self._set_status(f"正在审计 {label}...")

        def do():
            try:
                from ..calculator.audit import AuditCalculator
                a = AuditCalculator(self._current_data, self.stock_var.get())
                result = getattr(a, method)()
                self.root.after(0, self._on_single_analysis, result, label)
            except Exception as e:
                logger.error(f"{label} 审计失败: {e}\n{traceback.format_exc()}")
                self.root.after(0, self._on_single_analysis, f"❌ {label}审计失败: {e}", label)

        threading.Thread(target=do, daemon=True).start()

    # ========================================================================
    # AI深度投研
    # ========================================================================
    def _start_research_debate(self):
        """启动三方辩论投研 - 切换到投研标签页"""
        self.notebook.select(2)  # 切换到AI投研标签页

    def _get_ai_client(self):
        """获取可用的DeepSeek客户端，如果ai_panel没有则自行创建"""
        # 先尝试ai_panel的client
        if hasattr(self, 'ai_panel') and self.ai_panel and self.ai_panel.client:
            return self.ai_panel.client
        # 自行创建
        try:
            import json
            from pathlib import Path
            from ..config import CONFIG_FILE
            from ..deepseek.client import DeepSeekStreamClient, DeepSeekConfig
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, encoding='utf-8') as f:
                    cfg = json.load(f)
                api_key = cfg.get('deepseek_api_key', '')
                if api_key:
                    ds_config = DeepSeekConfig(
                        api_key=api_key,
                        base_url=cfg.get('deepseek_base_url', 'https://api.deepseek.com'),
                        model=cfg.get('deepseek_model', 'deepseek-chat'),
                    )
                    return DeepSeekStreamClient(config=ds_config)
        except Exception as e:
            logger.warning(f"自行创建DeepSeek客户端失败: {e}")
        return None

    def _show_health_report(self):
        """AI体检报告 - 构建提示词到AI面板，用户手动触发"""
        if not self._current_data:
            self._set_result_text("请先获取数据")
            return
        self.notebook.select(2)  # 切换到AI投研标签页

        stock_code = self.stock_var.get()
        try:
            from ..ai.report_builder import ReportBuilder
            from ..ai.signal_detector import SignalDetector
            import json as _json

            report = ReportBuilder.build(self._current_data, stock_code)
            signals = SignalDetector.detect(report)

            prompt_parts = [
                f"请基于以下公司体检数据，生成一份专业的财务体检报告。",
                f"要求：1)总结公司整体健康状况 2)指出关键风险点 3)给出投资建议",
                f"\n### 公司体检数据:\n{_json.dumps(report, ensure_ascii=False, indent=2, default=str)}",
            ]
            if signals:
                sig_text = "\n".join([
                    f"- {s['name']}: {s.get('trigger_data', '')}" for s in signals
                ])
                prompt_parts.append(f"\n### 已检测到的矛盾信号:\n{sig_text}")
            prompt = "\n".join(prompt_parts)

            # 填入AI面板的提示词区
            self.ai_panel.prompt_text.delete("1.0", "end")
            self.ai_panel.prompt_text.insert("1.0", prompt)
            self._set_status("✅ 体检报告提示词已生成，请在AI投研标签页确认后点击「发送分析」")
        except Exception as e:
            logger.error(f"体检报告提示词生成失败: {e}\n{traceback.format_exc()}")
            self._set_result_text(f"❌ 体检报告生成失败: {e}")

    def _show_signal_detection(self):
        """矛盾信号检测 - 构建提示词到AI面板，用户手动触发"""
        if not self._current_data:
            self._set_result_text("请先获取数据")
            return
        self.notebook.select(2)

        stock_code = self.stock_var.get()
        try:
            from ..ai.report_builder import ReportBuilder
            from ..ai.signal_detector import SignalDetector
            from ..calculator.audit import AuditCalculator
            import json as _json

            report = ReportBuilder.build(self._current_data, stock_code)
            signals = SignalDetector.detect(report)
            audit = AuditCalculator(self._current_data, stock_code)
            audit_result = audit.run_full_audit()

            prompt_parts = [
                f"你是财务异常检测专家。请基于以下数据，深度分析 {stock_code} 可能存在的财务矛盾信号。",
                f"要求：逐个分析每个信号的成因、风险程度、对投资的影响，并给出应对建议。",
                f"\n### 体检报告:\n{_json.dumps(report, ensure_ascii=False, indent=2, default=str)}",
            ]
            if signals:
                sig_text = "\n".join([
                    f"- {s['name']}: {s.get('description', '')} | 触发数据: {s.get('trigger_data', '')}"
                    for s in signals
                ])
                prompt_parts.append(f"\n### 经典矛盾信号:\n{sig_text}")

            all_sigs = audit_result.get('all_signals', [])
            if all_sigs:
                audit_text = "\n".join([
                    f"- [{s.get('level', '')}] {s.get('name', '')}: {s.get('value', '')}"
                    for s in all_sigs
                ])
                prompt_parts.append(f"\n### 审计引擎信号:\n{audit_text}")

            prompt = "\n".join(prompt_parts)

            self.ai_panel.prompt_text.delete("1.0", "end")
            self.ai_panel.prompt_text.insert("1.0", prompt)
            self._set_status("✅ 矛盾信号提示词已生成，请在AI投研标签页确认后点击「发送分析」")
        except Exception as e:
            logger.error(f"信号检测提示词生成失败: {e}\n{traceback.format_exc()}")
            self._set_result_text(f"❌ 信号检测失败: {e}")

    # Chart handlers
    def _show_ma_chart(self):
        self.chart_type_var.set("均线图")
        self._show_chart()
    def _show_bar_chart(self):
        self.chart_type_var.set("柱状图")
        self._show_chart()
    def _show_dupont_chart(self):
        self._show_deep_chart("dupont")
    def _show_fscore_chart(self):
        self._show_deep_chart("fscore")
    def _show_peer_chart(self):
        self._show_deep_chart("peer")
    def _show_valuation_chart(self):
        self._show_deep_chart("valuation")

    def _show_deep_chart(self, chart_type):
        """显示深度分析图表"""
        if not self._current_data:
            self._set_result_text("请先获取数据")
            return
        self.notebook.select(1)  # Switch to chart tab
        for w in self.chart_container.winfo_children():
            w.destroy()
        self._set_status(f"正在生成 {chart_type} 图表...")
        def do():
            try:
                fig = None
                err_msg = ""
                if chart_type == "dupont":
                    from ..analyzers.deep_analysis import DeepAnalyzer
                    da = DeepAnalyzer(self._current_data, self._current_stock, self.data_adapter, self.cache_manager)
                    periods = da._build_periods_data(5)
                    if len(periods) >= 2:
                        p0, p1 = periods[0], periods[-1]
                        from ..calculator.deep_analysis import DeepAnalysisCalculator as DAC
                        d0 = DAC.dupont_3factor(p0.get("net_profit"), p0.get("revenue"), p0.get("total_assets"), p0.get("equity"))
                        d1 = DAC.dupont_3factor(p1.get("net_profit"), p1.get("revenue"), p1.get("total_assets"), p1.get("equity"))
                        from ..charts import create_dupont_waterfall
                        fig = create_dupont_waterfall(
                            d1.get("net_margin"), d0.get("net_margin"),
                            d1.get("asset_turnover"), d0.get("asset_turnover"),
                            d1.get("equity_multiplier"), d0.get("equity_multiplier"),
                            d1.get("roe"), d0.get("roe"), self._current_stock)
                elif chart_type == "fscore":
                    from ..analyzers.deep_analysis import DeepAnalyzer
                    da = DeepAnalyzer(self._current_data, self._current_stock, self.data_adapter, self.cache_manager)
                    periods = da._build_periods_data(5)
                    if len(periods) >= 2:
                        from ..calculator.deep_analysis import DeepAnalysisCalculator as DAC
                        fs = DAC.piotroski_fscore(periods[0], periods[1])
                        scores = {"盈利(4)": fs["profit_score"], "杠杆(3)": fs["leverage_score"], "效率(2)": fs["efficiency_score"]}
                        from ..charts import create_fscore_radar
                        fig = create_fscore_radar(scores, self._current_stock)
                elif chart_type == "peer":
                    # 从当前数据中提取实际财务指标
                    metrics = {}
                    peer_avgs = {}
                    fin = self._current_data.get("financial")
                    if fin is not None and not fin.empty:
                        row = fin.iloc[-1] if len(fin) > 0 else None
                        if row is not None:
                            for col_candidates, label in [
                                (["roe"], "ROE"),
                                (["grossprofit_margin", "gross_margin"], "毛利率"),
                                (["netprofit_margin", "net_margin"], "净利率"),
                            ]:
                                for c in col_candidates:
                                    if c in fin.columns:
                                        val = pd.to_numeric(row.get(c), errors="coerce")
                                        if pd.notna(val):
                                            metrics[label] = float(val)
                                        break
                    if len(metrics) >= 2:
                        from ..charts import create_peer_comparison_bar
                        # 行业均值暂用公司值的 60-80% 作为参考
                        peer_avgs = {k: v * 0.7 for k, v in metrics.items()}
                        fig = create_peer_comparison_bar(
                            self._current_stock, metrics, peer_avgs, self._current_stock)
                    else:
                        err_msg = "数据不足，无法生成行业对比图（需要财务报表数据）"
                elif chart_type == "valuation":
                    # 从当前数据中提取 PE/PB 分位数
                    pe_pct, pb_pct = None, None
                    fin = self._current_data.get("financial")
                    if fin is not None and not fin.empty:
                        row = fin.iloc[-1] if len(fin) > 0 else None
                        if row is not None:
                            for c in ["pe_ttm", "pe"]:
                                if c in fin.columns:
                                    val = pd.to_numeric(row.get(c), errors="coerce")
                                    if pd.notna(val) and 0 < val < 1000:
                                        pe_pct = min(val, 100)  # 简化：PE 值映射到分位
                                    break
                            for c in ["pb"]:
                                if c in fin.columns:
                                    val = pd.to_numeric(row.get(c), errors="coerce")
                                    if pd.notna(val) and 0 < val < 100:
                                        pb_pct = min(val * 10, 100)  # 简化：PB 值映射到分位
                                    break
                    if pe_pct is not None:
                        from ..charts import create_valuation_gauge
                        fig = create_valuation_gauge(pe_pct, pb_pct, self._current_stock)
                    else:
                        err_msg = "数据不足，无法生成估值仪表盘（需要 PE/PB 数据）"

                if fig:
                    self.root.after(0, lambda f=fig: self._embed_chart(f))
                    self.root.after(0, lambda: self._set_status(f"{chart_type} 图表生成完成"))
                elif err_msg:
                    self.root.after(0, lambda m=err_msg: self._set_status(f"⚠️ {m}"))
            except Exception as e:
                err_msg = str(e)
                self.root.after(0, lambda m=err_msg: self._set_status(f"图表生成失败: {m}"))
        import threading
        threading.Thread(target=do, daemon=True).start()

    # ========================================================================
    # 图表
    # ========================================================================
    def _show_chart(self):
        if not HAS_CHARTS or not self._current_data:
            return
        daily = self._current_data.get("daily")
        if daily is None or daily.empty:
            self._set_status("⚠️ 无行情数据，无法生成图表")
            return

        # 清除旧图表
        for w in self.chart_container.winfo_children():
            w.destroy()
        self._chart_fig = None

        chart_type = self.chart_type_var.get()
        self._set_status(f"正在生成 {chart_type}...")

        # 延迟执行，让 UI 先刷新“生成中”状态
        self.root.after(50, lambda: self._do_render_chart(daily, chart_type))

    def _do_render_chart(self, daily, chart_type):
        """在主线程中创建并嵌入图表"""
        try:
            fig = None
            if chart_type == "K线图":
                fig = create_candlestick_chart(daily, stock_code=self._current_stock)
            elif chart_type == "均线图":
                fig = create_ma_chart(daily, stock_code=self._current_stock)
            elif chart_type == "柱状图":
                df = daily.head(60).copy()
                labels = []
                if "trade_date" in df.columns:
                    labels = [str(d)[-4:] for d in df["trade_date"]]
                else:
                    labels = [str(i) for i in range(len(df))]
                values = df["close"].tolist() if "close" in df.columns else []
                if labels and values:
                    fig = create_bar_chart(labels, values, title=f"{self._current_stock} 收盘价",
                                          stock_code=self._current_stock, unit="元")
            elif chart_type == "面积走势":
                fig = create_area_chart(daily, stock_code=self._current_stock)
            elif chart_type == "多指标仪表盘":
                fig = create_multi_metric_dashboard(daily, stock_code=self._current_stock)
            elif chart_type == "涨跌对比":
                # 生成近 N 日涨跌幅对比
                df = daily.head(20).copy()
                if "close" in df.columns and "trade_date" in df.columns:
                    closes = df["close"].tolist()
                    dates = [str(d)[-4:] for d in df["trade_date"]]
                    pct_changes = []
                    for i in range(1, len(closes)):
                        pct = (closes[i] - closes[i-1]) / closes[i-1] * 100 if closes[i-1] else 0
                        pct_changes.append(pct)
                    if pct_changes:
                        fig = create_percentage_bar_chart(dates[1:], pct_changes,
                                                         stock_code=self._current_stock)

            if fig is None:
                self._set_status("⚠️ 图表生成失败：无有效数据")
                return

            self._embed_chart(fig)

        except Exception as e:
            logger.error(f"图表渲染失败: {e}\n{traceback.format_exc()}")
            self._set_status(f"❌ 图表渲染失败: {e}")

    def _embed_chart(self, fig):
        """将 matplotlib fig 嵌入图表容器（必须在主线程调用）"""
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

        # 清除旧图表
        for w in self.chart_container.winfo_children():
            w.destroy()

        # 工具栏
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        toolbar = NavigationToolbar2Tk(canvas, self.chart_container)
        toolbar.update()
        toolbar.pack(side="top", fill="x")
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._chart_canvas = canvas
        self._chart_fig = fig

        # 刷新布局后，根据实际容器尺寸调整 figure 再绘制
        self.root.update_idletasks()
        self.root.after(50, lambda: self._resize_and_draw(fig, canvas))

    def _resize_and_draw(self, fig, canvas):
        """根据容器实际尺寸调整 figure 大小后绘制"""
        try:
            widget = canvas.get_tk_widget()
            w = widget.winfo_width()
            h = widget.winfo_height()
            if w > 50 and h > 50:
                fig.set_size_inches(w / fig.dpi, h / fig.dpi, forward=False)
            canvas.draw_idle()
            self._set_status(f"✅ {self.chart_type_var.get()} 生成完成")
        except Exception as e:
            logger.error(f"图表渲染失败: {e}")
            self._set_status(f"❌ 图表渲染失败: {e}")

    def _safe_draw_chart(self, canvas):
        """安全绘制图表（兼容旧调用）"""
        try:
            canvas.draw_idle()
            self._set_status(f"✅ {self.chart_type_var.get()} 生成完成")
        except Exception as e:
            logger.error(f"图表渲染失败: {e}")
            self._set_status(f"❌ 图表渲染失败: {e}")

    def _save_chart(self):
        if not hasattr(self, '_chart_fig') or not self._chart_fig:
            messagebox.showwarning("提示", "没有可保存的图表")
            return
        path = filedialog.asksaveasfilename(
            title="保存图表", initialdir=str(AUTO_SAVE_DIR),
            initialfile=f"{self._current_stock}_{self.chart_type_var.get()}_{datetime.now().strftime('%Y%m%d')}.png",
            filetypes=[("PNG", "*.png")])
        if path:
            try:
                self._chart_fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=Colors.BG_SECONDARY)
                messagebox.showinfo("成功", f"图表已保存到:\n{path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")

    # ========================================================================
    # 数据表格
    # ========================================================================
    def _update_table_types(self):
        types = list(self._current_data.keys())
        self.table_type_combo["values"] = types
        if types:
            self.table_type_var.set(types[0])
            self._refresh_table()

    def _refresh_table(self):
        dtype = self.table_type_var.get()
        df = self._current_data.get(dtype)
        self.data_tree.delete(*self.data_tree.get_children())
        self.data_tree["columns"] = ()
        if df is None or df.empty:
            return
        cols = list(df.columns)
        self.data_tree["columns"] = cols
        for col in cols:
            self.data_tree.heading(col, text=col, anchor="w")
            self.data_tree.column(col, width=100, anchor="w", minwidth=60)
        for _, row in df.head(TABLE_DISPLAY_ROWS).iterrows():
            self.data_tree.insert("", "end", values=[str(v) if v is not None else "" for v in row])

    # ========================================================================
    # ========================================================================
    # 欢迎页
    # ========================================================================
    def _show_welcome(self):
        welcome = """============================================================
         财务分析系统 Pro v9.3
============================================================

  本系统是一套专业级股票财务分析工具，分两阶段构建深度分析能力：

  【第一阶段：数据驱动的量化分析】
    1. 多源数据接入：通过 Tushare / Akshare / 新浪财经等接口
       获取 A股、美股行情数据及完整财务报表
    2. 标准化分析引擎：对利润表、资产负债表、现金流量表
       按照专业财务分析框架进行结构化处理
    3. 专业分析模型：杜邦分析、Z-score 破产预测、F-score
       财务健康评分、M-score 盈余管理检测、DCF 估值等
    4. 可视化输出：生成财务图表、趋势分析、行业对比等

  【第二阶段：AI 增强的智能分析】
    5. 结构化数据注入：将量化分析结果以专业框架格式传给 AI
    6. Chain-of-Thought 引导：AI 按「数据→指标→诊断→结论」
       逻辑链进行深度分析，输出个性化投资建议
    7. 多视角分析：同一数据从价值投资、成长投资、风险控制
       三个维度给出平衡建议

------------------------------------------------------------
  快速开始
------------------------------------------------------------

  第一步：输入股票代码
    · 在左侧输入框输入股票代码，例如：
      A股: 600519.SH（贵州茅台）、000001.SZ（平安银行）
      美股: AAPL（苹果）、MSFT（微软）

  第二步：获取数据
    · 点击「获取数据」按钮，系统自动从数据源拉取
      行情、财务报表、公司信息等数据
    · 数据源可在下拉框中切换（推荐 Tushare）

  第三步：选择分析
    · 左侧菜单分为 7 个分析类别，共 30+ 个分析模块：
      · 行情分析：行情概览、价格趋势、技术指标
      · 财务报表：利润表、资产负债表、现金流量表
      · 能力分析：盈利、营运、偿债、成长
      · 综合评估：量价结合、风险评估、AI 分析
      · 深度分析：杜邦、Z-score、F-score、M-score、
                 现金流象限、护城河、DCF 估值
      · 估值与质量：行业对比、相对估值、股东回报、财报质量
      · 图表分析：K线、均线、杜邦瀑布图、F-score 雷达图

  第四步：AI 深度分析（可选）
    · 配置 DeepSeek API Key 后，可使用 AI 智能分析
    · 系统将结构化数据 + 专业 prompt 发送给 AI
    · AI 返回带有逻辑链的深度分析报告

------------------------------------------------------------
  提示：先点击左侧菜单的任意分析项，或直接点击「分析」
  按钮运行综合分析，即可看到完整的财务分析结果。
============================================================
"""
        self._set_result_text(welcome)

    # 辅助
    # ========================================================================
    def _set_result_text(self, text):
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        if text:
            if isinstance(text, dict):
                text = self._format_dict_result(text)
            elif isinstance(text, list):
                import json
                text = json.dumps(text, ensure_ascii=False, indent=2, default=str)
            elif not isinstance(text, str):
                text = str(text)
            self._insert_formatted(text)
        self.result_text.see("1.0")
        self.result_text.config(state="disabled")

    def _format_dict_result(self, data: dict) -> str:
        """将分析结果dict格式化为带颜色标记的可读文本"""
        # 财务比率分析结果
        if any(k in data for k in ["偿债能力", "营运能力", "盈利能力", "发展能力", "市场价值", "综合评分"]):
            return self._format_ratio_table(data)

        # 审整审计报告（新格式或旧格式）
        if "risk_level" in data or "risk_rating" in data:
            return self._format_audit_report(data)

        # 单个审计类别结果（包含 level/desc 结构的信号dict）
        if self._is_signal_dict(data):
            return self._format_signal_dict(data)

        # Phase2Analyzer 结果（值为已格式化的字符串）
        if any(isinstance(v, str) and "\n" in v for v in data.values()):
            parts = []
            for key, val in data.items():
                if isinstance(val, str):
                    parts.append(val)
                elif isinstance(val, dict):
                    import json
                    parts.append(json.dumps(val, ensure_ascii=False, indent=2, default=str))
                else:
                    parts.append(str(val))
            return "\n\n".join(parts)

        # 其他dict
        import json
        return json.dumps(data, ensure_ascii=False, indent=2, default=str)

    def _is_signal_dict(self, data: dict) -> bool:
        """判断是否为审计信号dict（包含level/desc的信号集合）"""
        for v in data.values():
            if isinstance(v, dict) and "level" in v and "desc" in v:
                return True
        return False

    def _format_signal_dict(self, data: dict) -> str:
        """格式化单个类别的审计信号"""
        lines = []
        has_signal = False
        for sig_name, sig_data in data.items():
            if not isinstance(sig_data, dict):
                if sig_name == "error":
                    lines.append(f"  ⚠️ {sig_data}")
                continue
            has_signal = True
            level = sig_data.get("level", "")
            tag = "RED" if level == "red" else ("YELLOW" if level == "yellow" else "GREEN")
            icon = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}[tag]
            lines.append(f"[{tag}]{icon} {sig_name}[/]")
            lines.append(f"   {sig_data.get('desc', '')}")
            if sig_data.get("detail"):
                lines.append(f"   → {sig_data['detail']}")
            lines.append("")
        if not has_signal and not lines:
            lines.append("[GREEN]✅ 未发现异常信号[/GREEN]")
        return "\n".join(lines)

    def _format_ratio_table(self, data: dict) -> str:
        """财务比率表格格式化 - 带参考值和颜色标记"""
        lines = []
        lines.append("=" * 60)
        lines.append("  财务比率分析报告")
        lines.append("=" * 60)

        # 参考值定义: (名称, 值, 单位, 好阈值, 差阈值, 越大越好)
        ratio_defs = {
            "偿债能力": [
                ("流动比率", "流动比率", "", 2.0, 1.0, True),
                ("速动比率", "速动比率", "", 1.0, 0.5, True),
                ("现金比率", "现金比率", "", 0.5, 0.2, True),
                ("资产负债率", "资产负债率", "%", 50, 70, False),
                ("产权比率", "产权比率", "", 1.0, 2.0, False),
                ("利息保障倍数", "利息保障倍数", "", 3.0, 1.5, True),
            ],
            "营运能力": [
                ("应收账款周转率", "应收账款周转率", "次", 8, 4, True),
                ("应收账款周转天数", "应收账款周转天数", "天", 45, 90, False),
                ("存货周转率", "存货周转率", "次", 6, 3, True),
                ("存货周转天数", "存货周转天数", "天", 60, 120, False),
                ("总资产周转率", "总资产周转率", "次", 0.8, 0.4, True),
            ],
            "盈利能力": [
                ("毛利率", "毛利率", "%", 30, 15, True),
                ("净利率", "净利率", "%", 10, 3, True),
                ("ROA", "ROA", "%", 8, 3, True),
                ("ROE", "ROE", "%", 15, 8, True),
            ],
            "发展能力": [
                ("营收增长率", "营收增长率", "%", 15, 0, True),
                ("净利润增长率", "净利润增长率", "%", 15, 0, True),
                ("总资产增长率", "总资产增长率", "%", 10, 0, True),
            ],
            "市场价值": [
                ("PE", "PE", "", 25, 50, False),
                ("PB", "PB", "", 3, 6, False),
                ("EPS", "EPS", "元", 0, -1, True),
            ],
        }

        for section in ["偿债能力", "营运能力", "盈利能力", "发展能力", "市场价值"]:
            sec_data = data.get(section, {})
            if not sec_data:
                continue

            rating = sec_data.get("评级", "")
            rating_tag = self._rating_tag(rating)
            lines.append(f"\n【{section}】 评级: [{rating_tag}]{rating}[/{rating_tag}]")
            lines.append("-" * 60)
            lines.append(f"  {'指标':<14} {'数值':>10}  {'参考':>8}  {'状态':<6}")
            lines.append("  " + "-" * 56)

            # 收集所有指标
            all_items = {}
            # 子项
            for sub_key in ["短期偿债", "长期偿债"]:
                sub = sec_data.get(sub_key, {})
                all_items.update(sub)
            # 指标
            indicators = sec_data.get("指标", {})
            all_items.update(indicators)

            defs = ratio_defs.get(section, [])
            for label, key, unit, good, bad, higher_better in defs:
                val = all_items.get(key)
                if val is None:
                    continue

                # 格式化数值
                if unit == "%":
                    val_str = f"{val:.2f}%"
                elif unit:
                    val_str = f"{val:.2f}{unit}"
                else:
                    val_str = f"{val:.2f}"

                # 参考值
                if unit == "%":
                    ref_str = f">{good:.0f}%" if higher_better else f"<{good:.0f}%"
                else:
                    ref_str = f">{good:.1f}" if higher_better else f"<{good:.1f}"

                # 颜色判定
                if higher_better:
                    tag = "GREEN" if val >= good else ("YELLOW" if val >= bad else "RED")
                else:
                    tag = "GREEN" if val <= good else ("YELLOW" if val <= bad else "RED")

                status = {"GREEN": "✓ 优秀", "YELLOW": "○ 一般", "RED": "✗ 风险"}[tag]
                lines.append(f"[{tag}]  {label:<12} {val_str:>10}  {ref_str:>8}  {status}[/{tag}]")

            # 杜邦拆解
            dupont = sec_data.get("杜邦拆解", {})
            if dupont:
                lines.append(f"\n  杜邦拆解:")
                for k, v in dupont.items():
                    lines.append(f"    {k}: {v}")

        # 综合评分
        overall = data.get("综合评分", {})
        if overall:
            grade = overall.get("评级", "")
            grade_tag = self._rating_tag(grade)
            lines.append(f"\n{'=' * 60}")
            lines.append(f"  综合评分: [{grade_tag}]{overall.get('总分', 'N/A')}/{overall.get('满分', 'N/A')} ({overall.get('得分率', 'N/A')}%) - {grade}[/{grade_tag}]")
            scores = overall.get("各项", {})
            if scores:
                parts = [f"{k}:{v}" for k, v in scores.items()]
                lines.append(f"  各项: {' | '.join(parts)}")

        return "\n".join(lines)

    def _rating_tag(self, rating: str) -> str:
        """评级转颜色tag"""
        if rating in ("优秀", "良好", "高速增长", "快速增长", "低估"):
            return "GREEN"
        elif rating in ("一般", "稳定增长", "合理", "低增长"):
            return "YELLOW"
        elif rating in ("较差", "风险", "下滑", "高估", "亏损", "亏损或数据不足"):
            return "RED"
        return "YELLOW"

    def _format_audit_report(self, data: dict) -> str:
        """审计报告格式化（兼容新旧两种数据格式）"""
        lines = []
        lines.append("=" * 60)
        lines.append("  财务审计报告")
        lines.append("=" * 60)

        # 新格式（插件式引擎）
        if "risk_level" in data and "dimensions" in data:
            risk_level = data.get("risk_level", "")
            risk_icon = data.get("risk_icon", "")
            total_score = data.get("total_score", 0)
            lines.append(f"\n  综合风险评级: {risk_icon} {risk_level}  (综合得分: {total_score}/100)")
            lines.append(f"  高风险信号: {data.get('high_count', 0)} 个 | 中风险: {data.get('medium_count', 0)} 个 | 低风险: {data.get('low_count', 0)} 个")

            # 各维度
            dimensions = data.get("dimensions", {})
            for cat_key, dim in dimensions.items():
                if not isinstance(dim, dict):
                    continue
                icon = dim.get("icon", "📊")
                name = dim.get("name", cat_key)
                score = dim.get("score", 100)
                sig_count = dim.get("signal_count", 0)
                lines.append(f"\n【{icon} {name}】 得分: {score:.0f}/100 ({sig_count}个信号)")
                lines.append("-" * 60)
                for d in dim.get("details", []):
                    lines.append(f"  · {d}")

            # 信号详情
            all_signals = data.get("all_signals", [])
            if all_signals:
                lines.append(f"\n{'=' * 60}")
                lines.append("  异常信号详情")
                lines.append("=" * 60)
                for i, sig in enumerate(all_signals, 1):
                    level = sig.get("level", "")
                    level_icon = sig.get("level_icon", "⚪")
                    cat_cn = sig.get("category_cn", "")
                    lines.append(f"\n  {level_icon} [{i}] {sig.get('name', '')}  ({cat_cn})")
                    lines.append(f"     当前值: {sig.get('value', '')}")
                    lines.append(f"     标  准: {sig.get('threshold', '')}")
                    lines.append(f"     结  论: {sig.get('conclusion', '')}")
                    if sig.get('detail'):
                        lines.append(f"     补  充: {sig.get('detail', '')}")
            else:
                lines.append("\n  [GREEN]✅ 未发现异常信号[/GREEN]")

            # 建议
            recs = data.get("recommendations", [])
            if recs:
                lines.append(f"\n{'=' * 60}")
                lines.append("  排查建议")
                lines.append("=" * 60)
                for rec in recs:
                    lines.append(f"  {rec}")

            return "\n".join(lines)

        # 旧格式（兼容）
        risk = data.get("risk_rating", "")
        risk_tag = {"HIGH RISK": "RED", "MEDIUM RISK": "YELLOW", "LOW RISK": "YELLOW"}.get(risk, "GREEN")
        lines.append(f"\n  综合风险评级: [{risk_tag}]{risk}[/{risk_tag}]")
        lines.append(f"  红色信号: {data.get('red_signals', 0)} 个 | 黄色信号: {data.get('yellow_signals', 0)} 个")

        category_names = {
            "asset_signals": "🏦 资产端信号",
            "profit_signals": "💹 利润端信号",
            "cashflow_signals": "💸 现金流信号",
            "cross_validation": "🔗 勾稽关系验证",
        }

        for cat_key, cat_name in category_names.items():
            signals = data.get(cat_key, {})
            if not signals:
                continue
            lines.append(f"\n【{cat_name}】")
            lines.append("-" * 60)

            if "error" in signals:
                lines.append(f"  [YELLOW]⚠️ {signals['error']}[/YELLOW]")
                continue

            found = False
            for sig_name, sig_data in signals.items():
                if not isinstance(sig_data, dict):
                    continue
                found = True
                level = sig_data.get("level", "")
                tag = "RED" if level == "red" else ("YELLOW" if level == "yellow" else "GREEN")
                icon = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}[tag]
                lines.append(f"  [{tag}]{icon} {sig_name}[/]")
                lines.append(f"     {sig_data.get('desc', '')}")
                if sig_data.get("detail"):
                    lines.append(f"     → {sig_data['detail']}")

            if not found:
                lines.append("  [GREEN]✅ 未发现异常信号[/GREEN]")

        return "\n".join(lines)

    def _insert_formatted(self, text):
        import re
        t = self.result_text
        for line in text.split("\n"):
            # Parse color tags: [GREEN]text[/GREEN] etc.
            if "[GREEN]" in line or "[YELLOW]" in line or "[RED]" in line:
                self._insert_color_line(t, line)
                continue

            stripped = line.strip()
            if stripped.startswith("=") and len(stripped) > 10:
                t.insert("end", line + "\n", "heading")
            elif stripped.startswith("\u3010"):
                t.insert("end", line + "\n", "section")
            elif stripped.startswith("-") and len(stripped) > 10 and all(c in "-=" for c in stripped):
                t.insert("end", line + "\n", "section")
            elif any(k in stripped for k in ["\u2713", "\U0001f7e2", "\u4f18\u79c0", "\u826f\u597d", "\u5b89\u5168\u533a"]):
                t.insert("end", line + "\n", "success")
            elif any(k in stripped for k in ["\u26a0", "\U0001f7e1", "\u7070\u8272\u533a", "\u4e00\u822c"]):
                t.insert("end", line + "\n", "warning")
            elif any(k in stripped for k in ["\u2717", "\U0001f534", "\u5371\u9669\u533a", "\u9ad8\u98ce\u9669", "\u4e8f\u635f"]):
                t.insert("end", line + "\n", "danger")
            else:
                t.insert("end", line + "\n")

    def _insert_color_line(self, t, line):
        """Insert a line with color tags like [GREEN]text[/GREEN]"""
        import re
        tag_map = {"GREEN": "success", "YELLOW": "warning", "RED": "danger"}
        pos = 0
        for m in re.finditer(r'\[(GREEN|YELLOW|RED)\](.*?)\[/\1?\]', line):
            before = line[pos:m.start()]
            if before:
                t.insert("end", before)
            tag = tag_map.get(m.group(1), "")
            t.insert("end", m.group(2), tag)
            pos = m.end()
        after = line[pos:]
        if after:
            t.insert("end", after)
        t.insert("end", "\n")

    def _clear_results(self):
        self._set_result_text("")
        self._reset_kpis()

    def _set_status(self, text):
        self.status_label.config(text=text)

    def _update_clock(self):
        self.clock_label.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self._update_clock)

    def _switch_source(self):
        src = self.source_var.get()
        if self.data_adapter.set_active_source(src):
            self.source_label.config(text=f"数据源: {src.upper()}")
            self._set_status(f"数据源已切换为 {src.upper()}")

    def _show_token_dialog(self):
        def on_token_save():
            # Token 保存后，如果配置了 tushare token，自动切换到 tushare
            if self.data_adapter.tushare_pro:
                self.data_adapter.set_active_source("tushare")
                self.source_var.set("tushare")
                self.source_label.config(text="数据源: TUSHARE")
                self._set_status("已配置 Tushare Token，自动切换为默认数据源")
                logger.info("Tushare Token 已配置，自动切换为默认数据源")
            # 刷新 AI 面板
            if hasattr(self, 'ai_panel'):
                self.ai_panel.refresh_client()

        TokenConfigDialog(self.root, self.token_manager, self.data_adapter,
                         on_save=on_token_save)
    def _show_cache_dialog(self):
        CacheSettingsDialog(self.root, self.cache_manager)
    def _show_datasource_dialog(self):
        DataSourceDialog(self.root, self.data_adapter,
                        on_change=lambda s: self.source_label.config(text=f"数据源: {s.upper()}"))
    def _show_export_dialog(self):
        if not self._current_data:
            messagebox.showwarning("提示", "没有可导出的数据")
            return
        ExportDialog(self.root, self._current_data, self._current_stock,
                    analysis_result=self.result_text.get("1.0", "end").strip())
    def _show_about_dialog(self):
        AboutDialog(self.root)

    def on_closing(self):
        try:
            self.progress.stop()
            if HAS_CHARTS:
                import matplotlib.pyplot as plt
                plt.close("all")
        except Exception:
            pass
        self.root.destroy()
