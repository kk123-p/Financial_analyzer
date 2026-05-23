@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
echo Starting JS Diagnostic Test in Desktop Window...
echo.
python -c "import webview; webview.create_window('JS Test', 'http://127.0.0.1:8000/static/frontend/test.html', width=800, height=600); webview.start()"
pause
