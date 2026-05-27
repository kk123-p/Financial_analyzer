@echo off
title Claude Code Routing Proxy

set "PROJECT_DIR=C:\Users\LK\Desktop\FA\10.6"

echo ========================================
echo   Claude Code Agent Teams Routing Proxy
echo ========================================
echo   Opus / Sonnet  -^>  DeepSeek V4 Pro
echo   Haiku           -^>  Mimo V2.5 Pro
echo ========================================
echo.

:: Check if proxy is already running
curl -s http://localhost:4002/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Proxy is already running on port 4002.
    echo.
    curl -s http://localhost:4002/health
    echo.
    echo No action needed. Close this window.
    pause
    exit /b 0
)

:: Kill any stale listener on port 4002
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":4002.*LISTENING" 2^>nul') do (
    echo [INFO] Clearing stale listener (PID: %%a^)...
    taskkill /PID %%a /F >nul 2>&1
)

echo [INFO] Starting proxy on port 4002...
echo.
"%PROJECT_DIR%\.venv\Scripts\python.exe" "%PROJECT_DIR%\代理模式\routing_proxy.py"

pause
