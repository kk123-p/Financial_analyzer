@echo off
chcp 65001 >nul
set "PROJECT_DIR=C:\Users\LK\Desktop\FA\10.6"

echo Switching to DeepSeek V4 Pro...
echo.

(
echo {
echo   "env": {
echo     "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
echo     "ANTHROPIC_AUTH_TOKEN": "sk-d99fc231908a40c9bac5dc04601b4857",
echo     "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro",
echo     "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro",
echo     "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash"
echo   }
echo }
) > "%PROJECT_DIR%\.claude\settings.local.json"

echo [OK] Switched to DeepSeek V4 Pro.
echo Restart Claude Code to take effect.
pause
