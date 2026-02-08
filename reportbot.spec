# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

# Playwright browser path
playwright_cache = Path(r"/Users/barisbeydemir/Library/Caches/ms-playwright")
chromium_path = Path(r"/Users/barisbeydemir/Library/Caches/ms-playwright/chromium_headless_shell-1208")

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/reasons.csv', 'src'),
        (str(chromium_path), f'playwright/chromium'),
    ],
    hiddenimports=[
        'playwright',
        'playwright.async_api',
        'playwright._impl',
        'playwright._impl._api_types',
        'asyncio',
        'greenlet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='ReportBot',
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
