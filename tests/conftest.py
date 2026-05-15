"""pytest 配置 - 将项目根目录加入 sys.path"""
import sys
from pathlib import Path

# 项目根目录 = tests/ 的父目录
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
