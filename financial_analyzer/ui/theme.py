"""
Premium 深色科技主题 - Terminal Pro 风格
参考: Bloomberg Terminal × TradingView × GitHub Dark Mode
  - 配色: Deep Abyss + Accent Glow (#58A6FF)
  - 风格: Data-Dense Dashboard + Premium Tech
  - 交互: 微交互 150-200ms + 辉光反馈
  - 无障碍: WCAG AA 对比度 4.5:1+
"""

# ============================================================================
# 颜色体系 - Financial Dashboard 色板
# ============================================================================
class Colors:
    """Premium 科技深色色板 — Terminal Pro"""
    # 背景色 - 深渊黑层级
    BG_PRIMARY = "#060912"       # 最深背景（页面底色）
    BG_SECONDARY = "#0C1017"     # 侧边栏/次级面板 (GitHub Dark)
    BG_TERTIARY = "#161B22"      # 卡片/选中态
    BG_INPUT = "#0A0E16"         # 输入框
    BG_CARD = "#111820"          # 卡片背景
    BG_HOVER = "#1A2A45"         # 悬停态（蓝调）
    BG_MODAL = "#090C14"         # 弹窗背景

    # 前景色 - 高对比度
    FG_PRIMARY = "#F0F6FC"       # 主文字 (对比度 16:1+ on BG_PRIMARY)
    FG_SECONDARY = "#8B949E"     # 次要文字
    FG_MUTED = "#6B7D95"         # 弱化文字（提升可读性）
    FG_INVERSE = "#060912"       # 反色文字

    # 功能色 - 金融语义 + 辉光蓝
    ACCENT = "#58A6FF"           # 主强调色（辉光蓝 · GitHub/Supabase 风格）
    ACCENT_HOVER = "#79B8FF"     # 强调色悬停
    ACCENT_SUBTLE = "#13233A"    # 强调色底衬 (rgba 88,166,255,0.12)

    SUCCESS = "#3FB950"          # 上涨/成功/正面 (GitHub Green)
    SUCCESS_BG = "rgba(63,185,80,0.12)"
    DANGER = "#F85149"           # 下跌/危险/负面 (GitHub Red)
    DANGER_BG = "rgba(248,81,73,0.12)"
    WARNING = "#D29922"          # 警告 (GitHub Orange)
    WARNING_BG = "rgba(210,153,34,0.12)"
    INFO = "#58A6FF"             # 信息（统一使用 accent）
    INFO_BG = "rgba(88,166,255,0.12)"

    # 图表色 - 6色系（数据可视化最佳实践）
    CHART_1 = "#58A6FF"          # 辉光蓝
    CHART_2 = "#3FB950"          # 绿
    CHART_3 = "#D29922"          # 琥珀
    CHART_4 = "#F85149"          # 红
    CHART_5 = "#BC8CFF"          # 紫
    CHART_6 = "#39D2C0"          # 青
    CHART_GREEN = "#3FB950"      # K线涨
    CHART_RED = "#F85149"        # K线跌
    CHART_GRID = "#21262D"       # 网格线

    # 边框
    BORDER = "#21262D"           # 默认边框 (GitHub)
    BORDER_LIGHT = "#30363D"     # 亮边框
    BORDER_FOCUS = "#58A6FF"     # 聚焦边框（辉光蓝）

    # 状态
    STATUS_ONLINE = "#3FB950"
    STATUS_OFFLINE = "#F85149"
    STATUS_WARNING = "#D29922"

    # Sparkline
    SPARKLINE_UP = "#3FB950"
    SPARKLINE_DOWN = "#F85149"
    SPARKLINE_AREA_UP = "rgba(63,185,80,0.15)"
    SPARKLINE_AREA_DOWN = "rgba(248,81,73,0.15)"


# ============================================================================
# 字体配置 - 清晰层级
# ============================================================================
class Fonts:
    """字体定义 - Premium科技终端风格"""
    FAMILY = "Microsoft YaHei UI"
    FAMILY_MONO = "Cascadia Code"  # Windows Terminal 字体，回退 Consolas
    FAMILY_MONO_FALLBACK = "Consolas"

    # 标题层级
    TITLE = (FAMILY, 24, "bold")       # 页面标题 (增大)
    SUBTITLE = (FAMILY, 16, "bold")    # 区块标题 (增大)
    HEADING = (FAMILY, 13, "bold")     # 卡片标题 (增大)

    # 正文
    BODY = (FAMILY, 10)
    BODY_BOLD = (FAMILY, 10, "bold")
    SMALL = (FAMILY, 9)
    TINY = (FAMILY, 8)

    # 功能字体
    BUTTON = (FAMILY, 10, "bold")
    INPUT = (FAMILY, 10)
    RESULT = (FAMILY_MONO_FALLBACK, 10)  # 分析结果用等宽
    STATUS = (FAMILY, 9)
    CLOCK = (FAMILY_MONO_FALLBACK, 10, "bold")  # 时钟用等宽
    SIDEBAR_ITEM = (FAMILY, 10)
    SIDEBAR_ACTIVE = (FAMILY, 10, "bold")
    TAB = (FAMILY, 10)
    TAB_ACTIVE = (FAMILY, 10, "bold")

    # 数据字体（KPI/数字）
    KPI_VALUE = (FAMILY_MONO_FALLBACK, 22, "bold")   # 增大
    KPI_LABEL = (FAMILY, 9)
    KPI_CHANGE = (FAMILY_MONO_FALLBACK, 10, "bold")


# ============================================================================
# 间距 & 尺寸 - 8px 基准网格
# ============================================================================
class Spacing:
    """间距与尺寸 - 8px 网格系统"""
    # 间距
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32

    # 圆角
    RADIUS_SM = 4
    RADIUS_MD = 6
    RADIUS_LG = 8
    RADIUS_XL = 12

    # 组件尺寸
    SIDEBAR_WIDTH = 280
    INPUT_HEIGHT = 36
    BUTTON_HEIGHT = 36
    KPI_CARD_H = 108

    # 窗口
    WINDOW_MIN_W = 1200
    WINDOW_MIN_H = 750
    WINDOW_DEFAULT_W = 1440
    WINDOW_DEFAULT_H = 900

    # Sparkline
    SPARKLINE_W = 120
    SPARKLINE_H = 40


# ============================================================================
# ttkbootstrap 主题
# ============================================================================
BOOTSTRAP_THEME = "darkly"


def apply_custom_style(style):
    """在 ttkbootstrap darkly 主题上叠加 Premium Terminal Pro 样式"""
    c = Colors
    f = Fonts
    s = Spacing

    # ---- 全局 ----
    style.configure(".", background=c.BG_PRIMARY, foreground=c.FG_PRIMARY, font=f.BODY)

    # ---- TFrame ----
    style.configure("TFrame", background=c.BG_PRIMARY)
    style.configure("Sidebar.TFrame", background=c.BG_SECONDARY)
    style.configure("Card.TFrame", background=c.BG_CARD)

    # ---- TLabel ----
    style.configure("TLabel", background=c.BG_PRIMARY, foreground=c.FG_PRIMARY, font=f.BODY)
    style.configure("Title.TLabel", font=f.TITLE, foreground=c.ACCENT)
    style.configure("Subtitle.TLabel", font=f.SUBTITLE, foreground=c.FG_PRIMARY)
    style.configure("Heading.TLabel", font=f.HEADING, foreground=c.FG_PRIMARY)
    style.configure("Muted.TLabel", foreground=c.FG_MUTED, font=f.SMALL)
    style.configure("Success.TLabel", foreground=c.SUCCESS, font=f.BODY_BOLD)
    style.configure("Danger.TLabel", foreground=c.DANGER, font=f.BODY_BOLD)
    style.configure("Accent.TLabel", foreground=c.ACCENT)
    style.configure("KPI.TLabel", font=f.KPI_VALUE, foreground=c.FG_PRIMARY)
    style.configure("KPI_Label.TLabel", font=f.KPI_LABEL, foreground=c.FG_MUTED)

    # ---- TButton ----
    style.configure("TButton", font=f.BUTTON, padding=(s.LG, s.SM))
    style.configure("Accent.TButton", background=c.ACCENT, foreground=c.FG_INVERSE,
                    font=f.BUTTON, borderwidth=0)
    style.map("Accent.TButton",
              background=[("active", c.ACCENT_HOVER), ("disabled", c.BG_TERTIARY)])

    style.configure("Sidebar.TButton", font=f.SIDEBAR_ITEM, anchor="w", padding=(s.MD, s.SM),
                    background=c.BG_SECONDARY, foreground=c.FG_SECONDARY, borderwidth=0)
    style.map("Sidebar.TButton",
              background=[("active", c.BG_HOVER), ("!active", c.BG_SECONDARY)],
              foreground=[("active", c.ACCENT), ("!active", c.FG_SECONDARY)])

    style.configure("SidebarActive.TButton", font=f.SIDEBAR_ACTIVE, anchor="w",
                    padding=(s.MD, s.SM), background=c.ACCENT_SUBTLE,
                    foreground=c.ACCENT, borderwidth=0)

    # ---- TEntry ----
    style.configure("TEntry", font=f.INPUT, fieldbackground=c.BG_INPUT,
                    foreground=c.FG_PRIMARY, insertcolor=c.ACCENT, borderwidth=1)
    style.map("TEntry",
              fieldbackground=[("focus", c.BG_INPUT), ("!focus", c.BG_INPUT)],
              bordercolor=[("focus", c.BORDER_FOCUS), ("!focus", c.BORDER)])

    # ---- TCombobox ----
    style.configure("TCombobox", font=f.INPUT, fieldbackground=c.BG_INPUT,
                    foreground=c.FG_PRIMARY, arrowcolor=c.FG_SECONDARY)
    style.map("TCombobox",
              fieldbackground=[("readonly", c.BG_INPUT)],
              foreground=[("readonly", c.FG_PRIMARY)])

    # ---- TNotebook ----
    style.configure("TNotebook", background=c.BG_PRIMARY, borderwidth=0,
                    tabmargins=(0, 0, 0, 0))
    style.configure("TNotebook.Tab", font=f.TAB, padding=(s.XL, s.MD),
                    background=c.BG_SECONDARY, foreground=c.FG_MUTED,
                    borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", c.BG_TERTIARY), ("!selected", c.BG_SECONDARY)],
              foreground=[("selected", c.ACCENT), ("!selected", c.FG_MUTED)])

    # ---- Treeview ----
    style.configure("Treeview", font=f.BODY, background=c.BG_SECONDARY,
                    foreground=c.FG_PRIMARY, fieldbackground=c.BG_SECONDARY,
                    rowheight=30, borderwidth=0)
    style.configure("Treeview.Heading", font=f.BODY_BOLD, background=c.BG_TERTIARY,
                    foreground=c.ACCENT, borderwidth=0)
    style.map("Treeview",
              background=[("selected", c.ACCENT_SUBTLE), ("!selected", c.BG_SECONDARY)],
              foreground=[("selected", c.ACCENT), ("!selected", c.FG_PRIMARY)])

    # ---- Scrollbar ----
    try:
        style.map("TScrollbar",
                  background=[("active", c.BG_HOVER), ("!active", c.BG_SECONDARY)])
    except Exception:
        pass

    # ---- Progressbar ----
    try:
        style.configure("TProgressbar", background=c.ACCENT, troughcolor=c.BG_SECONDARY,
                        borderwidth=0, thickness=6)
    except Exception:
        pass

    # ---- Separator ----
    style.configure("TSeparator", background=c.BORDER)

    # ---- Checkbutton ----
    style.configure("TCheckbutton", background=c.BG_PRIMARY, foreground=c.FG_PRIMARY, font=f.BODY)
    style.map("TCheckbutton", background=[("active", c.BG_PRIMARY)])

    # ---- Radiobutton ----
    style.configure("TRadiobutton", background=c.BG_PRIMARY, foreground=c.FG_PRIMARY, font=f.BODY)

    # ---- Spinbox ----
    style.configure("TSpinbox", font=f.INPUT, fieldbackground=c.BG_INPUT,
                    foreground=c.FG_PRIMARY, arrowcolor=c.FG_SECONDARY)

    # ---- LabelFrame ----
    style.configure("TLabelframe", background=c.BG_PRIMARY, foreground=c.FG_PRIMARY,
                    bordercolor=c.BORDER, font=f.BODY)
    style.configure("TLabelframe.Label", background=c.BG_PRIMARY,
                    foreground=c.ACCENT, font=f.HEADING)

    # ---- 自定义卡片样式 ----
    style.configure("Card.TLabelframe", background=c.BG_CARD, bordercolor=c.BORDER)
    style.configure("Card.TLabelframe.Label", background=c.BG_CARD,
                    foreground=c.ACCENT, font=f.HEADING)

    return style
