"""
商务深色主题配置 - Financial Dashboard 风格
基于 UI/UX Pro Max 设计规范：
  - 配色: Financial Dashboard (#0F172A deep navy + #22C55E green)
  - 风格: Dark Mode OLED + Data-Dense Dashboard
  - 交互: 微交互 150-200ms + 状态反馈
  - 无障碍: WCAG AA 对比度 4.5:1+
"""

# ============================================================================
# 颜色体系 - Financial Dashboard 色板
# ============================================================================
class Colors:
    """深色金融仪表盘色板"""
    # 背景色 - 深蓝黑层级
    BG_PRIMARY = "#0B0F1A"       # 最深背景（页面底色）
    BG_SECONDARY = "#111827"     # 侧边栏/次级面板
    BG_TERTIARY = "#1E293B"      # 卡片/选中态
    BG_INPUT = "#0F172A"         # 输入框
    BG_CARD = "#151D2E"          # 卡片背景
    BG_HOVER = "#1E3A5F"         # 悬停态
    BG_MODAL = "#0D1321"         # 弹窗背景

    # 前景色 - 高对比度
    FG_PRIMARY = "#F1F5F9"       # 主文字 (对比度 15.4:1 on #0B0F1A)
    FG_SECONDARY = "#94A3B8"     # 次要文字 (对比度 7.1:1)
    FG_MUTED = "#475569"         # 弱化文字
    FG_INVERSE = "#0B0F1A"       # 反色文字

    # 功能色 - 金融语义
    ACCENT = "#3B82F6"           # 主强调色（信任蓝）
    ACCENT_HOVER = "#2563EB"     # 强调色悬停
    ACCENT_SUBTLE = "#1E3A5F"    # 强调色底衬

    SUCCESS = "#22C55E"          # 上涨/成功/正面
    SUCCESS_BG = "rgba(34,197,94,0.12)"
    DANGER = "#EF4444"           # 下跌/危险/负面
    DANGER_BG = "rgba(239,68,68,0.12)"
    WARNING = "#F59E0B"          # 警告
    WARNING_BG = "rgba(245,158,11,0.12)"
    INFO = "#38BDF8"             # 信息
    INFO_BG = "rgba(56,189,248,0.12)"

    # 图表色 - 6色系（数据可视化最佳实践）
    CHART_1 = "#3B82F6"          # 蓝
    CHART_2 = "#22C55E"          # 绿
    CHART_3 = "#F59E0B"          # 琥珀
    CHART_4 = "#EF4444"          # 红
    CHART_5 = "#A78BFA"          # 紫
    CHART_6 = "#06B6D4"          # 青
    CHART_GREEN = "#22C55E"      # K线涨
    CHART_RED = "#EF4444"        # K线跌
    CHART_GRID = "#1E293B"       # 网格线

    # 边框
    BORDER = "#1E293B"           # 默认边框
    BORDER_LIGHT = "#334155"     # 亮边框
    BORDER_FOCUS = "#3B82F6"     # 聚焦边框

    # 状态
    STATUS_ONLINE = "#22C55E"
    STATUS_OFFLINE = "#EF4444"
    STATUS_WARNING = "#F59E0B"

    # Sparkline
    SPARKLINE_UP = "#22C55E"
    SPARKLINE_DOWN = "#EF4444"
    SPARKLINE_AREA_UP = "rgba(34,197,94,0.15)"
    SPARKLINE_AREA_DOWN = "rgba(239,68,68,0.15)"


# ============================================================================
# 字体配置 - 清晰层级
# ============================================================================
class Fonts:
    """字体定义 - 金融数据可读性优先"""
    FAMILY = "Microsoft YaHei UI"
    FAMILY_MONO = "Consolas"

    # 标题层级
    TITLE = (FAMILY, 22, "bold")       # 页面标题
    SUBTITLE = (FAMILY, 14, "bold")    # 区块标题
    HEADING = (FAMILY, 12, "bold")     # 卡片标题

    # 正文
    BODY = (FAMILY, 10)
    BODY_BOLD = (FAMILY, 10, "bold")
    SMALL = (FAMILY, 9)
    TINY = (FAMILY, 8)

    # 功能字体
    BUTTON = (FAMILY, 10, "bold")
    INPUT = (FAMILY, 10)
    RESULT = (FAMILY_MONO, 10)         # 分析结果用等宽
    STATUS = (FAMILY, 9)
    CLOCK = (FAMILY_MONO, 10, "bold")  # 时钟用等宽
    SIDEBAR_ITEM = (FAMILY, 10)
    SIDEBAR_ACTIVE = (FAMILY, 10, "bold")
    TAB = (FAMILY, 10)
    TAB_ACTIVE = (FAMILY, 10, "bold")

    # 数据字体（KPI/数字）
    KPI_VALUE = (FAMILY_MONO, 20, "bold")
    KPI_LABEL = (FAMILY, 9)
    KPI_CHANGE = (FAMILY_MONO, 10, "bold")


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
    KPI_CARD_H = 100

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
    """在 ttkbootstrap darkly 主题上叠加金融仪表盘自定义样式"""
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
    style.configure("Accent.TButton", background=c.ACCENT, foreground=c.FG_INVERSE, font=f.BUTTON)
    style.map("Accent.TButton",
              background=[("active", c.ACCENT_HOVER), ("disabled", c.BG_TERTIARY)])

    style.configure("Sidebar.TButton", font=f.SIDEBAR_ITEM, anchor="w", padding=(s.MD, s.SM),
                    background=c.BG_SECONDARY, foreground=c.FG_SECONDARY, borderwidth=0)
    style.map("Sidebar.TButton",
              background=[("active", c.BG_HOVER), ("!active", c.BG_SECONDARY)],
              foreground=[("active", c.ACCENT), ("!active", c.FG_SECONDARY)])

    style.configure("SidebarActive.TButton", font=f.SIDEBAR_ACTIVE, anchor="w", padding=(s.MD, s.SM),
                    background=c.ACCENT_SUBTLE, foreground=c.ACCENT, borderwidth=0)

    # ---- TEntry ----
    style.configure("TEntry", font=f.INPUT, fieldbackground=c.BG_INPUT, foreground=c.FG_PRIMARY,
                    insertcolor=c.ACCENT, borderwidth=1)
    style.map("TEntry",
              fieldbackground=[("focus", c.BG_INPUT), ("!focus", c.BG_INPUT)],
              bordercolor=[("focus", c.BORDER_FOCUS), ("!focus", c.BORDER)])

    # ---- TCombobox ----
    style.configure("TCombobox", font=f.INPUT, fieldbackground=c.BG_INPUT, foreground=c.FG_PRIMARY,
                    arrowcolor=c.FG_SECONDARY)
    style.map("TCombobox",
              fieldbackground=[("readonly", c.BG_INPUT)],
              foreground=[("readonly", c.FG_PRIMARY)])

    # ---- TNotebook ----
    style.configure("TNotebook", background=c.BG_PRIMARY, borderwidth=0)
    style.configure("TNotebook.Tab", font=f.TAB, padding=(s.LG, s.SM),
                    background=c.BG_SECONDARY, foreground=c.FG_MUTED)
    style.map("TNotebook.Tab",
              background=[("selected", c.BG_TERTIARY), ("!selected", c.BG_SECONDARY)],
              foreground=[("selected", c.ACCENT), ("!selected", c.FG_MUTED)])

    # ---- Treeview ----
    style.configure("Treeview", font=f.BODY, background=c.BG_SECONDARY, foreground=c.FG_PRIMARY,
                    fieldbackground=c.BG_SECONDARY, rowheight=28, borderwidth=0)
    style.configure("Treeview.Heading", font=f.BODY_BOLD, background=c.BG_TERTIARY,
                    foreground=c.ACCENT, borderwidth=0)
    style.map("Treeview",
              background=[("selected", c.ACCENT_SUBTLE), ("!selected", c.BG_SECONDARY)],
              foreground=[("selected", c.ACCENT), ("!selected", c.FG_PRIMARY)])

    # ---- Scrollbar (ttkbootstrap 已管理元素，只改颜色映射) ----
    try:
        style.map("TScrollbar",
                  background=[("active", c.BG_HOVER), ("!active", c.BG_SECONDARY)])
    except Exception:
        pass

    # ---- Progressbar (避免与 ttkbootstrap 冲突) ----
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
    style.configure("TSpinbox", font=f.INPUT, fieldbackground=c.BG_INPUT, foreground=c.FG_PRIMARY,
                    arrowcolor=c.FG_SECONDARY)

    # ---- LabelFrame ----
    style.configure("TLabelframe", background=c.BG_PRIMARY, foreground=c.FG_PRIMARY,
                    bordercolor=c.BORDER, font=f.BODY)
    style.configure("TLabelframe.Label", background=c.BG_PRIMARY, foreground=c.ACCENT, font=f.HEADING)

    # ---- 自定义卡片样式 ----
    style.configure("Card.TLabelframe", background=c.BG_CARD, bordercolor=c.BORDER)
    style.configure("Card.TLabelframe.Label", background=c.BG_CARD, foreground=c.ACCENT, font=f.HEADING)

    return style
