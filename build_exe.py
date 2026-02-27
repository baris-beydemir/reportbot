#!/usr/bin/env python3
"""
ReportBot Executable Builder

Bu script, ReportBot'u tek bir executable dosyaya dönüştürür.
Kullanım: python build_exe.py
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

def main():
    print("=" * 60)
    print("ReportBot Executable Builder")
    print("=" * 60)
    
    # 1. PyInstaller yükle
    print("\n[1/4] PyInstaller kontrol ediliyor...")
    try:
        import PyInstaller
        print("  ✓ PyInstaller zaten yüklü")
    except ImportError:
        print("  → PyInstaller yükleniyor...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("  ✓ PyInstaller yüklendi")
    
    # 2. Playwright browser'ları kontrol et
    print("\n[2/4] Playwright browser'ları kontrol ediliyor...")
    
    # Playwright cache konumunu bul
    home = Path.home()
    if sys.platform == "darwin":
        playwright_cache = home / "Library/Caches/ms-playwright"
    elif sys.platform == "win32":
        playwright_cache = home / "AppData/Local/ms-playwright"
    else:
        playwright_cache = home / ".cache/ms-playwright"
    
    if not playwright_cache.exists():
        print("  ⚠️ Playwright browser'ları bulunamadı!")
        print("  → Browser'lar indiriliyor...")
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    
    # Chromium path'ini bul
    chromium_path = None
    if playwright_cache.exists():
        for item in playwright_cache.iterdir():
            if item.name.startswith("chromium"):
                chromium_path = item
                break
    
    if chromium_path:
        print(f"  ✓ Chromium bulundu: {chromium_path}")
    else:
        print("  ❌ Chromium bulunamadı! Lütfen 'playwright install chromium' çalıştırın")
        sys.exit(1)
    
    # 3. Data dosyalarını belirle
    print("\n[3/4] Build konfigürasyonu hazırlanıyor...")
    
    # Spec dosyası oluştur
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

# Playwright browser path
playwright_cache = Path(r"{playwright_cache}")
chromium_path = Path(r"{chromium_path}")

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/reasons.xlsx', 'src'),
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
    hooksconfig={{}},
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
'''
    
    spec_path = Path("reportbot.spec")
    spec_path.write_text(spec_content)
    print(f"  ✓ Spec dosyası oluşturuldu: {spec_path}")
    
    # 4. PyInstaller çalıştır
    print("\n[4/4] Executable oluşturuluyor (bu biraz sürebilir)...")
    
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        str(spec_path)
    ])
    
    # Sonuç
    print("\n" + "=" * 60)
    print("✅ Build tamamlandı!")
    print("=" * 60)
    
    dist_path = Path("dist")
    if sys.platform == "darwin":
        exe_path = dist_path / "ReportBot"
    else:
        exe_path = dist_path / "ReportBot.exe"
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n📦 Executable dosya: {exe_path}")
        print(f"   Boyut: {size_mb:.1f} MB")
        print(f"\n💡 Kullanım:")
        print(f"   {exe_path} --url 'https://maps.app.goo.gl/xxx'")
        print(f"   {exe_path} --csv urls.xlsx")
    else:
        print("\n⚠️ Executable bulunamadı. Lütfen 'dist' klasörünü kontrol edin.")

if __name__ == "__main__":
    main()
