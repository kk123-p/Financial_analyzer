@echo off
chcp 65001 >nul
echo ============================================
echo   Financial Analyzer Pro — 打包构建
echo ============================================
echo.

REM 激活虚拟环境
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [警告] 未找到虚拟环境 .venv，使用系统 Python
)

REM 确保 PyInstaller 已安装
pip install pyinstaller 2>nul

echo [1/3] 清理旧构建...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo [2/3] 运行 PyInstaller...
pyinstaller build.spec --clean --noconfirm

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 构建失败！
    pause
    exit /b 1
)

echo.
echo [3/3] 打包为 ZIP...
powershell -Command "Compress-Archive -Path 'dist\FinancialAnalyzerPro\*' -DestinationPath 'FinancialAnalyzerPro.zip' -Force"

echo.
echo ============================================
echo   构建完成！
echo   输出: dist\FinancialAnalyzerPro\
echo   ZIP:  FinancialAnalyzerPro.zip
echo ============================================
echo.
echo 将 FinancialAnalyzerPro.zip 发送给朋友即可。
echo 解压后双击 FinancialAnalyzerPro.exe 运行。
echo.
pause
