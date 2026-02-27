#!/usr/bin/env python3
"""
ReportBot Windows Executable Builder

Bu script, ReportBot'u Windows için tek bir .exe dosyasına dönüştürür.
Kullanım: python build_windows.py
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    print("=" * 60)
    print("ReportBot Windows Executable Builder")
    print("=" * 60)
    
    # 1. PyInstaller yükle
    print("\n[1/4] PyInstaller kontrol ediliyor...")
    try:
        import PyInstaller
        print("  ✓ PyInstaller zaten yuklu")
    except ImportError:
        print("  -> PyInstaller yukleniyor...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("  ✓ PyInstaller yuklendi")
    
    # 2. Playwright browser'ları kontrol et
    print("\n[2/4] Playwright browser'lari kontrol ediliyor...")
    
    # Windows'ta Playwright cache konumu
    home = Path.home()
    playwright_cache = home / "AppData" / "Local" / "ms-playwright"
    
    if not playwright_cache.exists():
        print("  ! Playwright browser'lari bulunamadi!")
        print("  -> Browser'lar indiriliyor...")
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
        print("  X Chromium bulunamadi!")
        print("  Lutfen 'playwright install chromium' calistirin")
        sys.exit(1)
    
    # 3. PyInstaller ile build
    print("\n[3/4] Build konfigurasyonu hazirlaniyor...")
    
    # Data dosyalarını hazırla
    datas = [
        f"src/reasons.xlsx;src",
        f"{chromium_path};playwright/chromium",
    ]
    
    # 4. PyInstaller çalıştır
    print("\n[4/4] Executable olusturuluyor (bu biraz surebilir)...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", "ReportBot",
        "--clean",
        "--noconfirm",
    ]
    
    # Data dosyalarını ekle
    for data in datas:
        cmd.extend(["--add-data", data])
    
    # Hidden imports
    hidden_imports = [
        "playwright",
        "playwright.async_api",
        "playwright._impl",
        "asyncio",
        "greenlet",
    ]
    for hi in hidden_imports:
        cmd.extend(["--hidden-import", hi])
    
    cmd.append("run.py")
    
    print(f"  Komut: {' '.join(cmd[:10])}...")
    subprocess.check_call(cmd)
    
    # Sonuç
    print("\n" + "=" * 60)
    print("✓ Build tamamlandi!")
    print("=" * 60)
    
    exe_path = Path("dist") / "ReportBot.exe"
    
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n Executable dosya: {exe_path}")
        print(f"   Boyut: {size_mb:.1f} MB")
        print(f"\n Kullanim:")
        print(f"   ReportBot.exe --url \"https://maps.app.goo.gl/xxx\"")
        print(f"   ReportBot.exe --csv urls.xlsx")
    else:
        print("\n! Executable bulunamadi. Lutfen 'dist' klasorunu kontrol edin.")

if __name__ == "__main__":
    main()
