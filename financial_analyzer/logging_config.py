"""
日志配置模块 - 统一日志管理
"""
import logging
import sys
from pathlib import Path
from .config import LOG_DIR, APP_NAME


def setup_logging(level=logging.INFO, log_to_file=True):
    """
    配置全局日志

    Args:
        level: 日志级别
        log_to_file: 是否同时输出到文件
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清除已有 handler（避免重复）
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件输出
    if log_to_file:
        log_file = LOG_DIR / f"{APP_NAME.lower()}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """获取模块级 logger"""
    return logging.getLogger(name)
