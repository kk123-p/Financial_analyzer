"""Launch Financial Analyzer Pro in web browser."""
import sys
import time
import threading
import webbrowser

API_URL = "http://127.0.0.1:8000"


def start_fastapi():
    import uvicorn
    uvicorn.run(
        "financial_analyzer.web.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
    )


def main():
    # Start server in background
    threading.Thread(target=start_fastapi, daemon=True).start()

    # Wait for server to be ready
    print("Starting server...", end="", flush=True)
    for _ in range(30):
        try:
            import urllib.request
            urllib.request.urlopen(API_URL + "/api/health", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
            print(".", end="", flush=True)
    print(" done.")

    # Open browser
    webbrowser.open(API_URL)
    print(f"Web UI: {API_URL}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    main()
