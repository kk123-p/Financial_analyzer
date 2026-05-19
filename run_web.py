"""财务分析系统 Web 版 — 启动入口"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "financial_analyzer.web.main:create_app",
        host="127.0.0.1",
        port=8000,
        factory=True,
    )
