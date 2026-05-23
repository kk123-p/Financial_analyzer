"""Launch Financial Analyzer Pro in desktop window (pywebview)."""
import sys
import time
import threading
import webview

API_URL = "http://127.0.0.1:8000/static/frontend/index.html"


def start_fastapi():
    import uvicorn
    uvicorn.run(
        "financial_analyzer.web.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="warning",
    )


def main():
    if "--no-serve" not in sys.argv:
        threading.Thread(target=start_fastapi, daemon=True).start()
        for _ in range(30):
            try:
                import urllib.request
                urllib.request.urlopen(API_URL + "/api/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)

    webview.create_window(
        title="Financial Analyzer Pro",
        url=API_URL,
        width=1200,
        height=800,
        min_size=(960, 600),
        resizable=True,
    )
    webview.start()


if __name__ == "__main__":
    main()
