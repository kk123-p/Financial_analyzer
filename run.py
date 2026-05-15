"""
双击运行此文件即可启动财务分析系统
或命令行: python run.py
"""
import sys
import os

# 将当前目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from financial_analyzer.main import main

if __name__ == "__main__":
    main()
