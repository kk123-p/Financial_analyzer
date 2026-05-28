"""pytest 配置 - 将项目根目录加入 sys.path"""
import os
import sys
from pathlib import Path

# 禁用量化数据缓存（避免测试间缓存污染）
os.environ["QUANT_CACHE_DISABLED"] = "1"

# 项目根目录 = tests/ 的父目录
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
