"""Financial Analyzer Pro — 打包版启动器

启动 FastAPI 服务器，并在默认浏览器中打开 Web 界面。
"""

import os
import sys
import time
import threading
import webbrowser

# ⚠️ 必须在 uvicorn.run() 之前显式 import，否则 PyInstaller 无法追踪依赖
import financial_analyzer
import financial_analyzer.config
import financial_analyzer.logging_config
import financial_analyzer.web.main
import financial_analyzer.web.dependencies
import financial_analyzer.web.services.data_service
import financial_analyzer.web.services.analysis_service
import financial_analyzer.web.services.result_formatter
import financial_analyzer.web.routes.pages
import financial_analyzer.web.routes.data_api
import financial_analyzer.web.routes.analysis
import financial_analyzer.web.routes.charts_api
import financial_analyzer.web.routes.ai_api
import financial_analyzer.web.routes.export_api
import financial_analyzer.web.routes.settings_api
import financial_analyzer.web.routes.api_v1
import financial_analyzer.data_sources.adapter
import financial_analyzer.data_sources.normalizer
import financial_analyzer.cache.manager
import financial_analyzer.services.analysis
import financial_analyzer.ai.report_builder
import financial_analyzer.deepseek.client

APP_URL = "http://127.0.0.1:8000"
HEALTH_URL = "http://127.0.0.1:8000/api/health"


def start_server():
    import uvicorn
    from financial_analyzer.web.main import app
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        ws="wsproto",
        ws_ping_interval=60,
        ws_ping_timeout=60,
        log_level="warning",
    )


def main():
    print("=" * 50)
    print("  Financial Analyzer Pro v10.0")
    print("=" * 50)

    # 启动后端服务器
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    # 等待服务器就绪
    print("\n正在启动服务...", end="", flush=True)
    import urllib.request

    for _ in range(40):
        try:
            urllib.request.urlopen(HEALTH_URL, timeout=1)
            break
        except Exception:
            time.sleep(0.5)
            print(".", end="", flush=True)
    print(" 完成！")

    # 打开浏览器 — 传统 Jinja2/htmx Web UI
    print(f"\nWeb 界面: {APP_URL}")
    webbrowser.open(APP_URL)

    print("\n提示：首次使用请点击右上角设置按钮配置 Tushare Token")
    print("按 Ctrl+C 或关闭此窗口退出程序\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭...")
        sys.exit(0)


if __name__ == "__main__":
    main()
