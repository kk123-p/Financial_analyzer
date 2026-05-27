@echo off
chcp 65001 >nul

set "PROJECT_DIR=C:\Users\LK\Desktop\FA\10.6"

echo Switching Claude Code to DIRECT mode...
del "%PROJECT_DIR%\.claude\settings.local.json" >nul 2>&1

echo.
echo [OK] Switched to direct mode (DeepSeek API).
echo.
echo Restart Claude Code for changes to take effect.
pause
