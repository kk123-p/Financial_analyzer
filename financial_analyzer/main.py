"""
Financial Analyzer Pro v9.0 - Entry Point
"""
import sys
from .logging_config import setup_logging
from .config import APP_VERSION


def main():
    """Main entry point"""
    setup_logging()

    import tkinter as tk
    from .ui.app import FinancialAnalyzerApp

    try:
        import ttkbootstrap as ttk
        root = ttk.Window(themename="darkly")
    except ImportError:
        root = tk.Tk()

    root.title("财务分析系统 v9.0")
    app = FinancialAnalyzerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
