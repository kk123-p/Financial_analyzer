@echo off
chcp 65001 >nul
set "PROJECT_DIR=C:\Users\LK\Desktop\FA\10.6"

echo Switching to Mimo V2.5 Pro...
echo.

(
echo {
echo   "env": {
echo     "ANTHROPIC_BASE_URL": "https://token-plan-cn.xiaomimimo.com/anthropic",
echo     "ANTHROPIC_AUTH_TOKEN": "tp-cjkvbys5ocjm25eanbxata8l3mcb3b3f0r3tc24o4dueoi2x",
echo     "ANTHROPIC_DEFAULT_OPUS_MODEL": "mimo-v2.5-pro",
echo     "ANTHROPIC_DEFAULT_SONNET_MODEL": "mimo-v2.5-pro",
echo     "ANTHROPIC_DEFAULT_HAIKU_MODEL": "mimo-v2.5-pro"
echo   }
echo }
) > "%PROJECT_DIR%\.claude\settings.local.json"

echo [OK] Switched to Mimo V2.5 Pro.
echo Restart Claude Code to take effect.
pause
