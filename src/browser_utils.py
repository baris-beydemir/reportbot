"""Browser utilities for PyInstaller compatibility."""
import os
import sys
import glob
from typing import Optional

from src.logger import logger


def get_bundled_browser_path() -> Optional[str]:
    """
    Get the path to the bundled Chromium browser executable.
    
    When running as a PyInstaller EXE, Playwright browsers are bundled
    inside the executable and extracted to a temp folder (_MEIXXXXXX).
    This function finds that path.
    
    Returns:
        Path to chrome executable if found, None otherwise.
    """
    # Check if running as PyInstaller bundle
    if not getattr(sys, 'frozen', False):
        # Not running as EXE, use default Playwright browser
        return None
    
    # Get the base path where PyInstaller extracts files
    # sys._MEIPASS is the temp folder where EXE contents are extracted
    base_path = getattr(sys, '_MEIPASS', None)
    if not base_path:
        return None
    
    logger.debug(f"🔍 PyInstaller base path: {base_path}")
    
    # Look for Chromium in the bundled location
    # The workflow adds chrome-win folder as: --add-data "chrome_win_path;chromium"
    possible_paths = [
        # Primary location - our bundled chromium folder
        os.path.join(base_path, "chromium", "chrome.exe"),
        # Windows paths (legacy/alternative locations)
        os.path.join(base_path, "playwright", "chromium", "chrome-win", "chrome.exe"),
        os.path.join(base_path, "playwright", "chromium", "chrome.exe"),
        os.path.join(base_path, "playwright-win", "chrome.exe"),
        os.path.join(base_path, "chrome-win", "chrome.exe"),
    ]
    
    # Try glob patterns for flexible matching
    glob_patterns = [
        os.path.join(base_path, "chromium*", "chrome.exe"),
        os.path.join(base_path, "chrome*", "chrome.exe"),
        os.path.join(base_path, "playwright", "chromium*", "chrome-win", "chrome.exe"),
        os.path.join(base_path, "playwright", "chromium*", "chrome.exe"),
        os.path.join(base_path, "playwright*", "chrome-win", "chrome.exe"),
        os.path.join(base_path, "playwright*", "chrome.exe"),
        os.path.join(base_path, "**", "chrome.exe"),  # Deep search
    ]
    
    # Check direct paths first
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"✅ Bundled browser found: {path}")
            return path
    
    # Try glob patterns
    for pattern in glob_patterns:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            logger.info(f"✅ Bundled browser found via glob: {matches[0]}")
            return matches[0]
    
    # List what's actually in the base path for debugging
    logger.warning(f"⚠️ Bundled browser not found in {base_path}")
    try:
        # List top-level directories
        contents = os.listdir(base_path)
        playwright_dirs = [d for d in contents if 'playwright' in d.lower() or 'chrom' in d.lower()]
        if playwright_dirs:
            logger.debug(f"   Found related dirs: {playwright_dirs}")
            for pdir in playwright_dirs:
                subpath = os.path.join(base_path, pdir)
                if os.path.isdir(subpath):
                    subcontent = os.listdir(subpath)
                    logger.debug(f"   Contents of {pdir}: {subcontent[:10]}...")
    except Exception as e:
        logger.debug(f"   Could not list directory: {e}")
    
    return None


def get_chromium_launch_options(headless: bool = False, extra_args: list = None) -> dict:
    """
    Get Playwright chromium.launch() options with bundled browser support.
    
    Args:
        headless: Whether to run in headless mode.
        extra_args: Additional browser arguments.
        
    Returns:
        Dictionary of options to pass to playwright.chromium.launch()
    """
    options = {
        "headless": headless,
        "args": extra_args or ['--disable-blink-features=AutomationControlled']
    }
    
    # Check for bundled browser
    bundled_path = get_bundled_browser_path()
    if bundled_path:
        options["executable_path"] = bundled_path
        logger.info(f"🎭 Using bundled browser: {bundled_path}")
    else:
        if getattr(sys, 'frozen', False):
            # Running as EXE but browser not found - this is a problem
            logger.warning("⚠️ Running as EXE but bundled browser not found!")
            logger.warning("   Playwright will try to use system browser...")
    
    return options


def is_running_as_exe() -> bool:
    """Check if the application is running as a PyInstaller EXE."""
    return getattr(sys, 'frozen', False)
