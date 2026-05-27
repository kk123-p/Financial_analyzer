@echo off
chcp 65001 >nul

set "PROJECT_DIR=C:\Users\LK\Desktop\FA\10.6"

echo Setting Claude Code to PROXY mode...
echo.

(
echo {
echo   "env": {
echo     "ANTHROPIC_BASE_URL": "http://localhost:4002",
echo     "ANTHROPIC_AUTH_TOKEN": "sk-gateway-master-key-2026",
echo     "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-7",
echo     "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro",
echo     "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5-20251001"
echo   }
echo }
) > "%PROJECT_DIR%\.claude\settings.local.json"

echo [OK] Switched to proxy mode (localhost:4002)
echo.
echo   Opus / Sonnet  ->  DeepSeek V4 Pro
echo   Haiku           ->  Mimo V2.5 Pro
echo.
echo Restart Claude Code for changes to take effect.
pause
