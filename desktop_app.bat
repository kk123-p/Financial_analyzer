@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
echo Starting Financial Analyzer Pro Desktop...
echo.
python desktop_app.py
pause
