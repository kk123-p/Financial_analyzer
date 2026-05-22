"""Financial Analyzer Pro v9.0 — Entry point."""
import sys
import uvicorn


def main():
    """Launch the FastAPI web server."""
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    uvicorn.run(
        "financial_analyzer.web.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
