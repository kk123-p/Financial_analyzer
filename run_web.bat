@echo off
cd /d "%~dp0"
echo Starting Financial Analyzer Pro Web Server...
echo Visit http://127.0.0.1:8000
echo.
.venv\Scripts\python.exe run_web.py
pause
