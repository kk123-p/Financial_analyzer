"""
工具函数模块
"""
import json
import unicodedata
import pandas as pd
from pathlib import Path
from datetime import datetime
from ..config import CONFIG_FILE, DEFAULT_CACHE_EXPIRY_HOURS
from ..logging_config import get_logger

logger = get_logger(__name__)


def cjk_ljust(s, width):
    """左对齐字符串，CJK字符占2个宽度"""
    s = str(s)
    cjk_count = sum(1 for c in s if unicodedata.east_asian_width(c) in ('F', 'W'))
    return s + ' ' * max(0, width - len(s) - cjk_count)


def cjk_rjust(s, width):
    """右对齐字符串，CJK字符占2个宽度"""
    s = str(s)
    cjk_count = sum(1 for c in s if unicodedata.east_asian_width(c) in ('F', 'W'))
    return ' ' * max(0, width - len(s) - cjk_count) + s


def val_from_row(row, keys: list, default=None):
    """从dict/Series中按多个key名取值，返回float或default"""
    if row is None:
        return default
    for k in keys:
        if k in row and row[k] is not None:
            try:
                v = float(row[k])
                if not pd.isna(v):
                    return v
            except (ValueError, TypeError):
                pass
    return default


def load_config() -> dict:
    """加载配置文件"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
    return {}


def save_config(config: dict):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info("配置已保存")
    except Exception as e:
        logger.error(f"保存配置失败: {e}")


def format_datetime(dt: datetime = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """格式化日期时间"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def parse_expiry_to_hours(expiry_str: str) -> int:
    """将过期时间字符串转换为小时数"""
    mapping = {
        "1小时": 1,
        "6小时": 6,
        "12小时": 12,
        "1天": 24,
        "3天": 72,
        "7天": 168,
        "30天": 720,
    }
    return mapping.get(expiry_str, DEFAULT_CACHE_EXPIRY_HOURS)
