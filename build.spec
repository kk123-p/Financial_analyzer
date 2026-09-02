# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Financial Analyzer Pro
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = Path.cwd()
SITEPK = ROOT / ".venv" / "Lib" / "site-packages"

# --- 自动收集 ML 包的数据文件和动态库 ---
ml_binaries = []
ml_datas = []
for pkg in ("xgboost", "imblearn", "sklearn"):
    ml_binaries += collect_dynamic_libs(pkg)
    ml_datas += collect_data_files(pkg)

# --- 模板文件 ---
template_data = []
templates_dir = ROOT / "financial_analyzer" / "web" / "templates"
if templates_dir.is_dir():
    for f in templates_dir.rglob("*"):
        if f.is_file():
            template_data.append((str(f), str(f.parent.relative_to(ROOT))))

# --- 静态文件 (CSS / JS) ---
static_data = []
static_dir = ROOT / "financial_analyzer" / "web" / "static"
if static_dir.is_dir():
    for f in static_dir.rglob("*"):
        if f.is_file():
            static_data.append((str(f), str(f.parent.relative_to(ROOT))))

# --- 教材数据 ---
textbook_data = []
textbook_dir = ROOT / "financial_analyzer" / "pipeline" / "textbook"
if textbook_dir.is_dir():
    for f in textbook_dir.rglob("*"):
        if f.is_file():
            textbook_data.append((str(f), str(f.parent.relative_to(ROOT))))

# --- akshare 数据文件 ---
akshare_data = []
akshare_fold = SITEPK / "akshare" / "file_fold"
if akshare_fold.is_dir():
    for f in akshare_fold.rglob("*"):
        if f.is_file():
            dest = str(f.parent.relative_to(SITEPK))
            akshare_data.append((str(f), dest))

all_datas = ml_datas + template_data + static_data + textbook_data + akshare_data

a = Analysis(
    ["launcher.py"],
    pathex=[str(ROOT)],
    binaries=ml_binaries,
    datas=all_datas,
    hiddenimports=[
        "financial_analyzer",
        "financial_analyzer.config",
        "financial_analyzer.logging_config",
        "financial_analyzer.web",
        "financial_analyzer.web.main",
        "financial_analyzer.web.dependencies",
        "financial_analyzer.web.services",
        "financial_analyzer.web.services.data_service",
        "financial_analyzer.web.services.analysis_service",
        "financial_analyzer.web.services.result_formatter",
        "financial_analyzer.web.routes",
        "financial_analyzer.web.routes.pages",
        "financial_analyzer.web.routes.data_api",
        "financial_analyzer.web.routes.analysis",
        "financial_analyzer.web.routes.charts_api",
        "financial_analyzer.web.routes.ai_api",
        "financial_analyzer.web.routes.export_api",
        "financial_analyzer.web.routes.settings_api",
        "financial_analyzer.web.routes.api_v1",
        "financial_analyzer.web.routes.quant_api",
        "financial_analyzer.web.routes.backtest_api",
        "financial_analyzer.web.routes.paper_trading_api",
        "financial_analyzer.data_sources",
        "financial_analyzer.data_sources.adapter",
        "financial_analyzer.data_sources.normalizer",
        "financial_analyzer.cache",
        "financial_analyzer.cache.manager",
        "financial_analyzer.services",
        "financial_analyzer.services.analysis",
        "financial_analyzer.ai",
        "financial_analyzer.ai.report_builder",
        "financial_analyzer.deepseek",
        "financial_analyzer.deepseek.client",
        "financial_analyzer.quant",
        "financial_analyzer.quant.scheduler",
        "financial_analyzer.calculator",
        "financial_analyzer.calculator.signals",
        "financial_analyzer.charts",
        "financial_analyzer.pipeline",
        "financial_analyzer.analyzers",
        "financial_analyzer.risk",
        "financial_analyzer.utils",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "websockets",
        "jinja2",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "IPython", "jupyter", "pytest", "sphinx"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FinancialAnalyzerPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
