# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Financial Analyzer Pro
"""

import os
from pathlib import Path
from PyInstaller.building.datastruct import Tree

ROOT = Path(os.getcwd())
SITEPK = ROOT / ".venv" / "Lib" / "site-packages"

# --- project data files ---

frontend_data = []
for f in (ROOT / "frontend").rglob("*"):
    if f.is_file():
        frontend_data.append((str(f), str(f.parent.relative_to(ROOT))))

template_data = []
for f in (ROOT / "financial_analyzer" / "web" / "templates").rglob("*"):
    if f.is_file():
        template_data.append((str(f), str(f.parent.relative_to(ROOT))))

static_data = []
for f in (ROOT / "financial_analyzer" / "web" / "static").rglob("*"):
    if f.is_file():
        static_data.append((str(f), str(f.parent.relative_to(ROOT))))

textbook_data = []
for f in (ROOT / "financial_analyzer" / "pipeline" / "textbook").rglob("*"):
    if f.is_file():
        textbook_data.append((str(f), str(f.parent.relative_to(ROOT))))

# --- third-party package data files ---

akshare_data = []
akshare_fold = SITEPK / "akshare" / "file_fold"
if akshare_fold.is_dir():
    for f in akshare_fold.rglob("*"):
        if f.is_file():
            dest = str(f.parent.relative_to(SITEPK))
            akshare_data.append((str(f), dest))

all_datas = frontend_data + template_data + static_data + textbook_data + akshare_data

a = Analysis(
    ["launcher.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=all_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "IPython", "jupyter", "pytest", "unittest", "sphinx"],
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
