"""
双击运行此文件即可启动财务分析系统
或命令行: python run.py
"""
import sys
import os

# 修复 Python 3.13 在 Windows 上 Tcl/Tk 路径问题（venv 下 sys.executable 不指向基础 Python）
_base_python = getattr(sys, "base_prefix", sys.prefix)
_tcl_path = os.path.join(_base_python, "tcl")
if os.path.isdir(_tcl_path):
    os.environ.setdefault("TCL_LIBRARY", os.path.join(_tcl_path, "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", os.path.join(_tcl_path, "tk8.6"))

# 将当前目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from financial_analyzer.main import main

if __name__ == "__main__":
    main()
