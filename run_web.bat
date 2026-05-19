@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
echo Starting Financial Analyzer Pro Web Server...
echo Visit http://127.0.0.1:8000
echo.
python run_web.py
pause
