"""
Runtime helper for PyInstaller executable.
Sets up Playwright browser paths when running as bundled executable.
"""

import os
import sys
from pathlib import Path


def setup_playwright_path():
    """
    Configure Playwright to find browsers when running as PyInstaller bundle.
    Call this BEFORE importing playwright.
    """
    # Check if running as PyInstaller bundle
    if getattr(sys, 'frozen', False):
        # Running as bundled executable
        bundle_dir = Path(sys._MEIPASS)
        
        # Set Playwright browser path
        playwright_dir = bundle_dir / "playwright"
        if playwright_dir.exists():
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(playwright_dir)
            
        # Also try to find chromium specifically
        chromium_dir = playwright_dir / "chromium"
        if chromium_dir.exists():
            # Find the actual executable
            for item in chromium_dir.rglob("*"):
                if item.name == "Chromium.app" or item.name == "chrome.exe" or item.name == "chrome":
                    os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH"] = str(item)
                    break


# Auto-setup when module is imported
setup_playwright_path()
