"""Desktop app launcher using pywebview."""
import sys
import time
import threading
import webview


API_URL = "http://127.0.0.1:8000"


def start_fastapi():
    """Start FastAPI server in background thread."""
    import uvicorn
    from financial_analyzer.web.main import app as fastapi_app
    uvicorn.run(fastapi_app, host="127.0.0.1", port=8000, log_level="warning")


def main():
    serve = "--serve" in sys.argv

    if serve:
        thread = threading.Thread(target=start_fastapi, daemon=True)
        thread.start()
        for _ in range(30):
            try:
                import urllib.request
                urllib.request.urlopen(API_URL + "/api/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)

    window = webview.create_window(
        title="Financial Analyzer Pro",
        url=API_URL,
        width=1200,
        height=800,
        min_size=(960, 600),
        resizable=True,
        fullscreen=False,
    )
    webview.start()


if __name__ == "__main__":
    main()
