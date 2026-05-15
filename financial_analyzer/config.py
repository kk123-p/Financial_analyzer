"""
全局配置模块 - 统一管理字体、路径、常量
"""
import sys
from pathlib import Path

# ============================================================================
# 应用数据目录（打包后也能正确工作）
# ============================================================================
APP_NAME = "FinancialAnalyzer"
APP_VERSION = "9.0.0"

if getattr(sys, 'frozen', False):
    # PyInstaller 打包后
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

# 用户数据目录（配置、缓存、日志）
USER_DATA_DIR = Path.home() / f".{APP_NAME.lower()}"
USER_DATA_DIR.mkdir(exist_ok=True)

CACHE_DIR = USER_DATA_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

LOG_DIR = USER_DATA_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

CONFIG_FILE = USER_DATA_DIR / "config.json"

# 自动保存目录（D盘）
AUTO_SAVE_DIR = Path("D:/FinancialAnalyzerData")
AUTO_SAVE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# 字体配置
# ============================================================================
FONT_FAMILY = "Microsoft YaHei UI"
FONT_TITLE = (FONT_FAMILY, 18, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 13, "bold")
FONT_LABEL = (FONT_FAMILY, 10)
FONT_SMALL = (FONT_FAMILY, 9)
FONT_BUTTON = (FONT_FAMILY, 10)
FONT_RESULT = (FONT_FAMILY, 10)
FONT_STATUS = (FONT_FAMILY, 9)
FONT_CLOCK = (FONT_FAMILY, 11, "bold")
FONT_ENTRY = (FONT_FAMILY, 10)

# ============================================================================
# 分隔线样式
# ============================================================================
SEPARATOR_HEAVY = "=" * 60
SEPARATOR_LIGHT = "-" * 55
SEPARATOR_DASH = "-" * 40

# ============================================================================
# 颜色配置（文本标签用）
# ============================================================================
COLOR_HIGHLIGHT = "#2196F3"
COLOR_WARNING = "#FF9800"
COLOR_SUCCESS = "#4CAF50"
COLOR_DANGER = "#F44336"
COLOR_INFO = "#2196F3"
COLOR_MUTED = "gray"

# ============================================================================
# 数据源配置
# ============================================================================
DEFAULT_DATA_SOURCE = "tushare"
DEFAULT_START_DATE = "20240101"
BATCH_ANALYSIS_LIMIT = 10
TABLE_DISPLAY_ROWS = 100

# ============================================================================
# 缓存配置
# ============================================================================
DEFAULT_CACHE_EXPIRY_HOURS = 24

# ============================================================================
# 分析参数常量
# ============================================================================
TRADING_DAYS_PER_YEAR = 252  # 年化计算用的交易日数

# 均线窗口
MA_SHORT = 5
MA_MEDIUM = 10
MA_LONG = 20
MA_VERY_LONG = 60

# RSI 周期
RSI_PERIOD = 14

# 布林带参数
BB_PERIOD = 20
BB_STD_MULTIPLIER = 2

# MACD 参数
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# 分析窗口（天数）
TREND_WINDOW = 20       # 趋势分析窗口
VOLUME_MA_WINDOW = 5    # 成交量均线窗口
VOLUME_MA_LONG = 10     # 成交量长均线窗口
VOLATILITY_WINDOW = 20  # 波动率滚动窗口

# Yahoo Finance 重试
YFINANCE_MAX_RETRIES = 3
YFINANCE_RETRY_BASE_WAIT = 5  # 秒

# ============================================================================
# PDF 字体配置
# ============================================================================
PDF_FONT_PATHS = [
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simsun.ttc",
]
PDF_FONT_NAME = "SimHei"
