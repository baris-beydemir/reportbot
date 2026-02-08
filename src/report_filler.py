"""Google Report Content form filler using Playwright."""
import asyncio
import os
import subprocess
import time
import socket
import csv
import random
from typing import Optional, List
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
from dotenv import load_dotenv

from src.models import Review, Business
from src.browser_utils import get_bundled_browser_path

# Load environment variables
load_dotenv()


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def launch_chrome_debug_mode(port: int = 9222) -> Optional[subprocess.Popen]:
    """
    Launch Chrome in debug mode if not already running.
    
    Args:
        port: Debug port to use.
        
    Returns:
        Popen object if Chrome was launched, None if already running.
    """
    if is_port_in_use(port):
        print(f"  ✓ Chrome debug mode already running on port {port}")
        return None
    
    # Find Chrome executable
    chrome_paths = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
        "/usr/bin/google-chrome",  # Linux
        "/usr/bin/chromium-browser",  # Linux Chromium
        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",  # Windows
        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",  # Windows 32-bit
    ]
    
    chrome_path = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_path = path
            break
    
    if not chrome_path:
        return None
    
    print(f"  Launching Chrome in debug mode on port {port}...")
    
    # Launch Chrome with remote debugging
    process = subprocess.Popen([
        chrome_path,
        f"--remote-debugging-port={port}",
        "--no-first-run",
        "--no-default-browser-check",
        f"--user-data-dir={os.path.expanduser('~/.reportbot_chrome_profile')}",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for Chrome to start
    for _ in range(30):  # Wait up to 30 seconds
        if is_port_in_use(port):
            print(f"  ✓ Chrome started on port {port}")
            time.sleep(2)  # Give it a moment to fully initialize
            return process
        time.sleep(1)
    
    print("  ⚠ Chrome failed to start")
    return None


class ReportFiller:
    """Filler for Google Report Content form."""
    
    REPORT_URL = "https://reportcontent.google.com/forms/legal_other_geo?ai0&product=geo"
    CDP_PORT = 9222
    REASONS_FILE = os.path.join(os.path.dirname(__file__), "reasons.csv")
    
    def __init__(
        self, 
        headless: bool = False, 
        google_email: str = None, 
        google_password: str = None,
        use_real_chrome: bool = True
    ):
        """
        Initialize the form filler.
        
        Args:
            headless: Whether to run browser in headless mode (ignored if use_real_chrome=True).
            google_email: Google account email for auto-login.
            google_password: Google account password for auto-login.
            use_real_chrome: If True, connect to real Chrome browser via CDP.
        """
        self.headless = headless
        self.google_email = google_email or os.getenv("GOOGLE_EMAIL")
        self.google_password = google_password or os.getenv("GOOGLE_PASSWORD")
        self.use_real_chrome = use_real_chrome
        self._context = None
        self._browser = None
        self._page: Optional[Page] = None
        self._playwright = None
        self._chrome_process = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        playwright = await async_playwright().start()
        self._playwright = playwright
        
        if self.use_real_chrome:
            # Try to connect to real Chrome browser
            self._chrome_process = launch_chrome_debug_mode(self.CDP_PORT)
            
            if is_port_in_use(self.CDP_PORT):
                print("  Connecting to Chrome browser...")
                try:
                    self._browser = await playwright.chromium.connect_over_cdp(
                        f"http://localhost:{self.CDP_PORT}"
                    )
                    
                    # Get existing context or create new one
                    contexts = self._browser.contexts
                    if contexts:
                        self._context = contexts[0]
                        # Use existing page or create new one
                        if self._context.pages:
                            self._page = self._context.pages[0]
                        else:
                            self._page = await self._context.new_page()
                    else:
                        self._context = await self._browser.new_context()
                        self._page = await self._context.new_page()
                    
                    print("  ✓ Connected to Chrome browser")
                    return self
                    
                except Exception as e:
                    print(f"  ⚠ Could not connect to Chrome: {e}")
                    print("  Falling back to Playwright browser...")
            else:
                print("  ⚠ Chrome not available, using Playwright browser...")
        
        # Fallback: Use Playwright's own browser with anti-detection
        user_data_dir = os.path.expanduser("~/.reportbot_browser_data")
        
        # Check for bundled browser (PyInstaller EXE)
        bundled_browser = get_bundled_browser_path()
        
        launch_kwargs = {
            "user_data_dir": user_data_dir,
            "headless": self.headless,
            "viewport": {"width": 1280, "height": 900},
            "locale": "tr-TR",
            "args": [
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu',
            ],
            "ignore_default_args": ['--enable-automation'],
        }
        
        if bundled_browser:
            launch_kwargs["executable_path"] = bundled_browser
            print(f"  🎭 Using bundled browser: {bundled_browser}")
        
        self._context = await playwright.chromium.launch_persistent_context(**launch_kwargs)
        
        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        
        # Hide webdriver property to avoid detection
        await self._page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Overwrite the 'plugins' property
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Overwrite the 'languages' property
            Object.defineProperty(navigator, 'languages', {
                get: () => ['tr-TR', 'tr', 'en-US', 'en']
            });
            
            // Remove automation-related properties
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Don't close the real Chrome browser, just disconnect
        if self.use_real_chrome and self._browser:
            # Just disconnect, don't close the browser
            pass
        elif self._context:
            await self._context.close()
        
        if self._playwright:
            await self._playwright.stop()
    
    async def _type_like_human(self, text: str, delay_min: int = 50, delay_max: int = 150):
        """Type text character by character like a human would."""
        import random
        for char in text:
            await self._page.keyboard.type(char, delay=random.randint(delay_min, delay_max))
            await asyncio.sleep(random.uniform(0.01, 0.05))
    
    async def _handle_google_login(self) -> bool:
        """
        Handle Google login page automatically or guide user.
        
        Returns:
            True if login was successful, False otherwise.
        """
        current_url = self._page.url
        if "accounts.google.com" not in current_url:
            return True
        
        print("\n" + "="*50)
        print("  🔐 GOOGLE LOGIN REQUIRED")
        
        # Try automatic login if credentials are provided
        if self.google_email:
            print("  Attempting automatic login...")
            try:
                # Wait for email input field
                email_selectors = [
                    "input[type='email']",
                    "input[name='identifier']",
                    "#identifierId",
                    "input[autocomplete='username']",
                ]
                
                email_field = None
                for selector in email_selectors:
                    try:
                        field = self._page.locator(selector).first
                        if await field.is_visible(timeout=3000):
                            email_field = field
                            break
                    except:
                        continue
                
                if email_field:
                    # Click on the field first to focus it
                    await email_field.click()
                    await asyncio.sleep(0.5)
                    
                    # Clear any existing text
                    await self._page.keyboard.press("Control+a")
                    await asyncio.sleep(0.1)
                    
                    # Type email like a human
                    print(f"  Entering email: {self.google_email[:3]}***")
                    await self._type_like_human(self.google_email)
                    await asyncio.sleep(0.5)
                    
                    # Press Next button
                    next_selectors = [
                        "button:has-text('Next')",
                        "button:has-text('İleri')",
                        "button:has-text('Sonraki')",
                        "#identifierNext",
                        "button[type='submit']",
                        "[data-idom-class*='nCP5yc']",
                    ]
                    
                    for selector in next_selectors:
                        try:
                            next_btn = self._page.locator(selector).first
                            if await next_btn.is_visible(timeout=2000):
                                await next_btn.click()
                                await asyncio.sleep(3)
                                break
                        except:
                            continue
                    
                    # Wait and check for password field
                    if self.google_password:
                        await asyncio.sleep(2)
                        
                        password_selectors = [
                            "input[type='password']",
                            "input[name='Passwd']",
                            "input[name='password']",
                            "#password input",
                        ]
                        
                        password_field = None
                        for selector in password_selectors:
                            try:
                                field = self._page.locator(selector).first
                                if await field.is_visible(timeout=5000):
                                    password_field = field
                                    break
                            except:
                                continue
                        
                        if password_field:
                            await password_field.click()
                            await asyncio.sleep(0.3)
                            
                            print("  Entering password...")
                            await self._type_like_human(self.google_password)
                            await asyncio.sleep(0.5)
                            
                            # Press login button
                            login_selectors = [
                                "button:has-text('Next')",
                                "button:has-text('İleri')",
                                "button:has-text('Sonraki')",
                                "#passwordNext",
                                "button[type='submit']",
                            ]
                            
                            for selector in login_selectors:
                                try:
                                    login_btn = self._page.locator(selector).first
                                    if await login_btn.is_visible(timeout=2000):
                                        await login_btn.click()
                                        await asyncio.sleep(5)
                                        break
                                except:
                                    continue
                            
                            print("  ✓ Login credentials entered")
                            return True
                    else:
                        print("  ⚠ Email entered. Please enter password manually.")
                        return False
                else:
                    print("  ⚠ Could not find email field")
                    
            except Exception as e:
                print(f"  ⚠ Auto-login failed: {e}")
        
        # Manual login fallback
        print("  Please login manually in the browser window.")
        print("  (Your login will be saved for future use)")
        print("  The script will continue after you login...")
        print("="*50 + "\n")
        return False
    
    async def navigate_to_form(self):
        """Navigate to the report content form."""
        if not self._page:
            raise RuntimeError("Filler not initialized. Use async with statement.")
        
        print("  Loading report form...")
        await self._page.goto(self.REPORT_URL, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # Check if login is required
        max_wait = 180  # 3 minutes for login
        waited = 0
        login_handled = False
        
        while waited < max_wait:
            current_url = self._page.url
            
            # Check if we're on the report form
            if "reportcontent.google.com/forms" in current_url:
                print("  ✓ On report form page")
                break
            
            # Check if on login page
            if "accounts.google.com" in current_url:
                if not login_handled:
                    login_success = await self._handle_google_login()
                    login_handled = True
                    
                    if not login_success:
                        # Wait for manual login
                        await asyncio.sleep(5)
                        waited += 5
                    else:
                        # Wait for redirect after login
                        await asyncio.sleep(5)
                        waited += 5
                else:
                    await asyncio.sleep(3)
                    waited += 3
            else:
                await asyncio.sleep(2)
                waited += 2
        
        # After login, navigate to form again if needed
        if "reportcontent.google.com" not in self._page.url:
            await self._page.goto(self.REPORT_URL, wait_until="domcontentloaded")
            await asyncio.sleep(3)
    
    async def fill_url_field(self, url: str, field_index: int = 0):
        """Fill a URL field (Hak ihlalinde bulunduğu iddia edilen URL).
        
        Args:
            url: The URL to fill.
            field_index: Which URL field to fill (0-based).
        """
        if not self._page:
            return False
        
        url_selectors = [
            # Turkish form specific selectors
            "input[placeholder*='Hak ihlalinde']",
            "input[placeholder*='iddia edilen URL']",
            "input[aria-label*='Hak ihlalinde']",
            "input[aria-label*='iddia edilen']",
            # Generic URL selectors
            "input[type='url']",
            "input[name*='url']",
            "input[placeholder*='URL']",
            "input[placeholder*='url']",
            "input[aria-label*='URL']",
            "input[id*='url']",
            # By position - first text input after "URL 1" label
            "input[type='text']",
        ]
        
        for selector in url_selectors:
            try:
                url_fields = self._page.locator(selector)
                count = await url_fields.count()
                
                if count > field_index:
                    url_field = url_fields.nth(field_index)
                    if await url_field.is_visible(timeout=2000):
                        await url_field.click()
                        await asyncio.sleep(0.2)
                        await url_field.fill(url)
                        print(f"  ✓ URL {field_index + 1} dolduruldu: {url[:50]}...")
                        return True
            except Exception:
                continue
        
        return False
    
    async def click_add_url_button(self) -> bool:
        """Click the '+URL ekle' button to add another URL field.
        
        Returns:
            True if button was clicked successfully.
        """
        if not self._page:
            return False
        
        try:
            # Various selectors for the add URL button
            add_url_selectors = [
                "button:has-text('+URL ekle')",
                "button:has-text('+ URL ekle')",
                "button:has-text('URL ekle')",
                "a:has-text('+URL ekle')",
                "a:has-text('+ URL ekle')",
                "[role='button']:has-text('URL ekle')",
                "material-button:has-text('URL')",
                ".add-url-button",
                "[data-test-id='add-url']",
            ]
            
            for selector in add_url_selectors:
                try:
                    button = self._page.locator(selector).first
                    if await button.is_visible(timeout=2000):
                        await button.click()
                        await asyncio.sleep(0.5)
                        print("  ✓ '+URL ekle' butonuna tıklandı")
                        return True
                except Exception:
                    continue
            
            # Fallback: Try to find any clickable element with "URL" text
            try:
                url_buttons = self._page.locator("text=/\\+.*URL/i")
                if await url_buttons.count() > 0:
                    await url_buttons.first.click()
                    await asyncio.sleep(0.5)
                    print("  ✓ URL ekleme butonuna tıklandı (fallback)")
                    return True
            except Exception:
                pass
            
            print("  ⚠️ '+URL ekle' butonu bulunamadı")
            return False
            
        except Exception as e:
            print(f"  ⚠️ URL ekleme butonu tıklanırken hata: {e}")
            return False
    
    async def fill_multiple_urls(self, urls: list[str], reasons: list[str] = None) -> int:
        """Fill multiple URL fields, clicking '+URL ekle' as needed.
        
        Args:
            urls: List of URLs to fill.
            reasons: Optional list of reasons to fill for each URL.
            
        Returns:
            Number of URLs successfully filled.
        """
        if not self._page or not urls:
            return 0
        
        filled_count = 0
        
        for i, url in enumerate(urls):
            # For first URL, just fill
            # For subsequent URLs, click add button first
            if i > 0:
                success = await self.click_add_url_button()
                if not success:
                    print(f"  ⚠️ URL {i + 1} için alan eklenemedi, durduruluyor")
                    break
                await asyncio.sleep(0.5)
            
            # Fill the URL field
            success = await self.fill_url_field(url, field_index=i)
            if success:
                filled_count += 1
                # If we have a reason for this URL, fill the corresponding textarea
                if reasons and i < len(reasons):
                    await self.fill_textarea_at_index(reasons[i], i)
            else:
                print(f"  ⚠️ URL {i + 1} doldurulamadı")
        
        print(f"  📝 Toplam {filled_count}/{len(urls)} URL dolduruldu")
        return filled_count

    async def fill_textarea_at_index(self, text: str, index: int):
        """Fill the textarea at a specific index."""
        if not self._page:
            return False
        
        textarea_selectors = [
            "textarea",
            "[contenteditable='true']",
            "input[type='text'][name*='description']",
            "input[type='text'][name*='detail']",
            "input[type='text'][name*='comment']",
        ]
        
        for selector in textarea_selectors:
            try:
                fields = self._page.locator(selector)
                if await fields.count() > index:
                    field = fields.nth(index)
                    if await field.is_visible(timeout=2000):
                        await field.fill(text)
                        print(f"  ✓ Filled description field {index + 1}")
                        return True
            except Exception:
                continue
        return False
    
    async def fill_textarea(self, text: str):
        """Fill any textarea field with the description."""
        if not self._page:
            return False
        
        textarea_selectors = [
            "textarea",
            "[contenteditable='true']",
            "input[type='text'][name*='description']",
            "input[type='text'][name*='detail']",
            "input[type='text'][name*='comment']",
        ]
        
        # Find all visible textareas/inputs and fill each with a random reason if requested
        try:
            # We want to find all matching elements
            found_any = False
            for selector in textarea_selectors:
                locators = self._page.locator(selector)
                count = await locators.count()
                for i in range(count):
                    field = locators.nth(i)
                    if await field.is_visible(timeout=1000):
                        # If it's a list of reasons, we'll pick one randomly for each field
                        # but for now, we just fill with the provided text
                        await field.fill(text)
                        found_any = True
            
            if found_any:
                print("  ✓ Filled description field(s)")
                return True
        except Exception as e:
            print(f"  ⚠ Error filling textarea: {e}")
        
        return False

    def _get_random_reasons(self, count: int) -> List[str]:
        """Read reasons from CSV and return a list of random unique reasons."""
        try:
            if not os.path.exists(self.REASONS_FILE):
                return ["Bu içerik Google politikalarını ihlal etmektedir."] * count
            
            all_reasons = []
            with open(self.REASONS_FILE, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('reason'):
                        all_reasons.append(row['reason'])
            
            if not all_reasons:
                return ["Bu içerik Google politikalarını ihlal etmektedir."] * count
            
            # If we have enough unique reasons, pick unique ones, otherwise allow duplicates
            if len(all_reasons) >= count:
                return random.sample(all_reasons, count)
            else:
                return [random.choice(all_reasons) for _ in range(count)]
        except Exception as e:
            print(f"  ⚠ Error reading reasons CSV: {e}")
            return ["Bu içerik Google politikalarını ihlal etmektedir."] * count
    
    async def fill_country_dropdown(self, country: str = "Türkiye"):
        """Fill the country of residence dropdown."""
        if not self._page:
            return False
        
        try:
            # Click on the country dropdown
            dropdown_selectors = [
                "div[role='listbox']",
                "[aria-label*='Country']",
                "[aria-label*='Ülke']",
                "select",
                ".country-select",
                "[data-value='Country of residence']",
                "div:has-text('Country of residence')",
            ]
            
            # First try to find and click the dropdown trigger
            dropdown_trigger_selectors = [
                "[aria-haspopup='listbox']",
                "[role='combobox']",
                "div[aria-expanded]",
                ".dropdown-trigger",
            ]
            
            for selector in dropdown_trigger_selectors:
                try:
                    trigger = self._page.locator(selector).first
                    if await trigger.is_visible(timeout=2000):
                        await trigger.click()
                        await asyncio.sleep(1)
                        break
                except:
                    continue
            
            # Now search for Turkey option
            turkey_selectors = [
                f"[data-value='{country}']",
                f"[role='option']:has-text('{country}')",
                f"li:has-text('{country}')",
                f"option:has-text('{country}')",
                f"div[role='option']:has-text('Turkey')",
                f"div[role='option']:has-text('Türkiye')",
            ]
            
            for selector in turkey_selectors:
                try:
                    option = self._page.locator(selector).first
                    if await option.is_visible(timeout=2000):
                        await option.click()
                        print(f"  ✓ Selected country: {country}")
                        return True
                except:
                    continue
            
            # Try typing in dropdown if it's a searchable dropdown
            try:
                await self._page.keyboard.type(country)
                await asyncio.sleep(0.5)
                await self._page.keyboard.press("Enter")
                print(f"  ✓ Typed country: {country}")
                return True
            except:
                pass
                
        except Exception as e:
            print(f"  ⚠ Could not fill country: {e}")
        
        return False
    
    async def fill_legal_name(self, name: str):
        """Fill the full legal name field."""
        if not self._page:
            return False
        
        try:
            name_selectors = [
                "input[placeholder*='Full legal name']",
                "input[placeholder*='legal name']",
                "input[aria-label*='Full legal name']",
                "input[aria-label*='legal name']",
                "input[name*='name']",
                "input[id*='name']",
                "input[type='text']",
            ]
            
            for selector in name_selectors:
                try:
                    # Find all matching inputs and pick the one for name
                    fields = self._page.locator(selector)
                    count = await fields.count()
                    
                    for i in range(count):
                        field = fields.nth(i)
                        if await field.is_visible(timeout=1000):
                            # Check if this looks like a name field (not URL or other)
                            placeholder = await field.get_attribute("placeholder") or ""
                            aria_label = await field.get_attribute("aria-label") or ""
                            
                            if "name" in placeholder.lower() or "name" in aria_label.lower() or (
                                "url" not in placeholder.lower() and "url" not in aria_label.lower()
                            ):
                                await field.fill(name)
                                print(f"  ✓ Filled legal name: {name}")
                                return True
                except:
                    continue
        except Exception as e:
            print(f"  ⚠ Could not fill legal name: {e}")
        
        return False
    
    async def select_acting_on_behalf(self, myself: bool = True):
        """Select the 'I am acting on behalf of' option."""
        if not self._page:
            return False
        
        try:
            if myself:
                selectors = [
                    "input[type='radio'][value='myself']",
                    "input[type='radio']:near(:text('Myself'))",
                    "input[type='radio']:near(:text('Kendim'))",
                    "label:has-text('Myself') input[type='radio']",
                    "label:has-text('Kendim') input[type='radio']",
                    "[role='radio']:has-text('Myself')",
                    "[role='radio']:has-text('Kendim')",
                    "div:has-text('Myself') input[type='radio']",
                ]
            else:
                selectors = [
                    "input[type='radio'][value='someone_else']",
                    "input[type='radio']:near(:text('Someone else'))",
                    "input[type='radio']:near(:text('Başka biri'))",
                    "label:has-text('Someone else') input[type='radio']",
                    "label:has-text('Başka biri') input[type='radio']",
                    "[role='radio']:has-text('Someone else')",
                    "[role='radio']:has-text('Başka biri')",
                ]
            
            for selector in selectors:
                try:
                    radio = self._page.locator(selector).first
                    if await radio.is_visible(timeout=2000):
                        await radio.click()
                        print(f"  ✓ Selected: {'Myself' if myself else 'Someone else'}")
                        return True
                except:
                    continue
            
            # Try clicking on the label text directly
            try:
                text_to_find = "Myself" if myself else "Someone else"
                alt_text_to_find = "Kendim" if myself else "Başka biri"
                
                label = self._page.locator(f"text={text_to_find}").first
                if not await label.is_visible(timeout=1000):
                    label = self._page.locator(f"text={alt_text_to_find}").first
                
                if await label.is_visible(timeout=1000):
                    await label.click()
                    print(f"  ✓ Selected: {text_to_find} (label click)")
                    return True
            except:
                pass
                
        except Exception as e:
            print(f"  ⚠ Could not select acting on behalf: {e}")
        
        return False

    async def select_legal_relationship(self, relationship_text: str = "Müşteri (ör. avukat veya başka bir yetkili temsilciyim)"):
        """Select the legal relationship from the dropdown or radio buttons."""
        if not self._page:
            return False
        
        print(f"  Selecting legal relationship: {relationship_text}")
        
        try:
            # Try finding radio button with this text
            selectors = [
                f"label:has-text('{relationship_text}') input[type='radio']",
                f"input[type='radio']:near(:text('{relationship_text}'))",
                f"[role='radio']:has-text('{relationship_text}')",
            ]
            
            for selector in selectors:
                try:
                    radio = self._page.locator(selector).first
                    if await radio.is_visible(timeout=2000):
                        await radio.click()
                        print(f"  ✓ Selected legal relationship: {relationship_text}")
                        return True
                except:
                    continue
            
            # Try clicking on the text directly
            try:
                label = self._page.locator(f"text={relationship_text}").first
                if await label.is_visible(timeout=2000):
                    await label.click()
                    print(f"  ✓ Selected legal relationship (text click): {relationship_text}")
                    return True
            except:
                pass
                
        except Exception as e:
            print(f"  ⚠ Could not select legal relationship: {e}")
        
        return False

    async def fill_customer_name(self, customer_name: str):
        """Fill the 'Customer name' (Müşterinizin adı) field."""
        if not self._page:
            return False
        
        try:
            selectors = [
                "input[placeholder*='Müşterinizin adı']",
                "input[aria-label*='Müşterinizin adı']",
                "input[placeholder*='Customer name']",
                "input[aria-label*='Customer name']",
                # Generic fallback: first text input after legal relationship
                "input[type='text']",
            ]
            
            for selector in selectors:
                try:
                    fields = self._page.locator(selector)
                    count = await fields.count()
                    for i in range(count):
                        field = fields.nth(i)
                        if await field.is_visible(timeout=2000):
                            # Check if it's empty or has relevant placeholder
                            placeholder = await field.get_attribute("placeholder") or ""
                            aria_label = await field.get_attribute("aria-label") or ""
                            
                            if any(x in placeholder.lower() or x in aria_label.lower() 
                                   for x in ["müşteri", "customer", "adı", "name"]):
                                await field.fill(customer_name)
                                print(f"  ✓ Filled customer name: {customer_name}")
                                return True
                except:
                    continue
        except Exception as e:
            print(f"  ⚠ Could not fill customer name: {e}")
        
        return False
    
    async def uncheck_other_than_review(self):
        """Uncheck the 'Is this submission related to something other than a review?' checkbox."""
        if not self._page:
            return False
        
        try:
            checkbox_selectors = [
                "input[type='checkbox']:near(:text('other than a review'))",
                "input[type='checkbox'][aria-label*='other than']",
                "[role='checkbox']:near(:text('other than a review'))",
            ]
            
            for selector in checkbox_selectors:
                try:
                    checkbox = self._page.locator(selector).first
                    if await checkbox.is_visible(timeout=2000):
                        # Check if it's checked and uncheck it
                        is_checked = await checkbox.is_checked()
                        if is_checked:
                            await checkbox.click()
                            print("  ✓ Unchecked 'other than a review' checkbox")
                        return True
                except:
                    continue
            
            # Try finding checkbox near the text
            try:
                text_element = self._page.locator("text=Is this submission related to something other than a review").first
                if await text_element.is_visible(timeout=2000):
                    # Find checkbox near this text
                    checkbox = self._page.locator("input[type='checkbox']").first
                    if await checkbox.is_visible(timeout=1000):
                        is_checked = await checkbox.is_checked()
                        if is_checked:
                            await checkbox.click()
                            print("  ✓ Unchecked 'other than a review' checkbox")
                        return True
            except:
                pass
                
        except Exception as e:
            print(f"  ⚠ Could not handle checkbox: {e}")
        
        return False
    
    async def check_confirmation_checkbox(self):
        """Check the confirmation checkbox (Lütfen onaylamak için işaretleyin)."""
        if not self._page:
            return False
        
        try:
            # Method 1: Find the gdf-container that contains "Lütfen onaylamak için işaretleyin" text
            # and click on its material-checkbox
            try:
                # Find container with the confirmation text
                confirmation_container = self._page.locator("gdf-container:has-text('Lütfen onaylamak için işaretleyin')").last
                if await confirmation_container.is_visible(timeout=3000):
                    # Click on the material-checkbox inside this container
                    checkbox = confirmation_container.locator("material-checkbox").first
                    if await checkbox.is_visible(timeout=2000):
                        await checkbox.click()
                        print("  ✓ Onay checkbox'ı işaretlendi (material-checkbox)")
                        return True
            except Exception as e:
                print(f"  Method 1 failed: {e}")
            
            # Method 2: Try clicking on the gdf-checkbox component directly
            try:
                gdf_checkboxes = self._page.locator("gdf-checkbox")
                count = await gdf_checkboxes.count()
                
                for i in range(count):
                    gdf_cb = gdf_checkboxes.nth(i)
                    if await gdf_cb.is_visible(timeout=1000):
                        # Get parent container text to check which checkbox this is
                        parent_container = gdf_cb.locator("xpath=ancestor::gdf-container[1]")
                        parent_text = ""
                        try:
                            parent_text = await parent_container.text_content() or ""
                        except:
                            pass
                        
                        # Skip "yorum dışında" checkbox
                        if "yorum dışında" in parent_text.lower():
                            continue
                        
                        # Check if this is the confirmation checkbox
                        if "onaylamak" in parent_text.lower() or "işaretleyin" in parent_text.lower():
                            material_cb = gdf_cb.locator("material-checkbox").first
                            if await material_cb.is_visible(timeout=1000):
                                await material_cb.click()
                                print("  ✓ Onay checkbox'ı işaretlendi (gdf-checkbox)")
                                return True
            except Exception as e:
                print(f"  Method 2 failed: {e}")
            
            # Method 3: Click directly on material-checkbox components, find the right one
            try:
                material_checkboxes = self._page.locator("material-checkbox")
                count = await material_checkboxes.count()
                
                for i in range(count):
                    mcb = material_checkboxes.nth(i)
                    if await mcb.is_visible(timeout=1000):
                        # Check the surrounding text
                        parent = mcb.locator("xpath=ancestor::gdf-single-container[1]")
                        parent_text = ""
                        try:
                            parent_text = await parent.text_content() or ""
                        except:
                            pass
                        
                        # Skip "yorum dışında" checkbox
                        if "yorum dışında" in parent_text.lower():
                            continue
                        
                        # Click on confirmation checkbox
                        if "onaylamak" in parent_text.lower() or "işaretleyin" in parent_text.lower():
                            await mcb.click()
                            print("  ✓ Onay checkbox'ı işaretlendi (material-checkbox direct)")
                            return True
            except Exception as e:
                print(f"  Method 3 failed: {e}")
            
            # Method 4: Use XPath to find the last material-checkbox (confirmation is usually last)
            try:
                # The confirmation checkbox is typically the last gdf-checkbox on the form
                last_checkbox_xpath = "//gdf-container[contains(., 'onaylamak')]//material-checkbox"
                checkbox = self._page.locator(f"xpath={last_checkbox_xpath}").first
                if await checkbox.is_visible(timeout=2000):
                    await checkbox.click()
                    print("  ✓ Onay checkbox'ı işaretlendi (xpath)")
                    return True
            except Exception as e:
                print(f"  Method 4 failed: {e}")
            
            # Method 5: Click on the label text directly
            try:
                label = self._page.locator("text=Lütfen onaylamak için işaretleyin").first
                if await label.is_visible(timeout=2000):
                    await label.click()
                    print("  ✓ Onay checkbox'ı işaretlendi (label click)")
                    return True
            except Exception as e:
                print(f"  Method 5 failed: {e}")
                
        except Exception as e:
            print(f"  ⚠ Could not check confirmation checkbox: {e}")
        
        return False
    
    async def fill_signature(self, signature: str):
        """Fill the signature field (İmza)."""
        if not self._page:
            return False
        
        try:
            signature_selectors = [
                "input[placeholder*='İmza']",
                "input[aria-label*='İmza']",
                "input[name*='signature']",
                "input[id*='signature']",
                "input[placeholder*='Signature']",
                # Generic - find input near "İmza" text
                "label:has-text('İmza') + input",
                "label:has-text('İmza') input",
            ]
            
            for selector in signature_selectors:
                try:
                    field = self._page.locator(selector).first
                    if await field.is_visible(timeout=1000):
                        await field.fill(signature)
                        print(f"  ✓ İmza alanı dolduruldu: {signature}")
                        return True
                except:
                    continue
            
            # Fallback: Find all text inputs and look for one near "İmza" section
            try:
                # Look for input after "İmza" heading
                imza_section = self._page.locator("text=İmza").first
                if await imza_section.is_visible(timeout=1000):
                    # Find the nearest input field
                    inputs = self._page.locator("input[type='text']")
                    count = await inputs.count()
                    
                    # Try the last few inputs (signature is usually at the bottom)
                    for i in range(max(0, count - 3), count):
                        inp = inputs.nth(i)
                        if await inp.is_visible(timeout=500):
                            # Check if it's empty or placeholder suggests signature
                            placeholder = await inp.get_attribute("placeholder") or ""
                            value = await inp.input_value()
                            if not value and ("imza" in placeholder.lower() or "signature" in placeholder.lower() or placeholder == "İmza*"):
                                await inp.fill(signature)
                                print(f"  ✓ İmza alanı dolduruldu (fallback): {signature}")
                                return True
            except:
                pass
                
        except Exception as e:
            print(f"  ⚠ Could not fill signature: {e}")
        
        return False
    
    async def fill_form(
        self,
        business: Business,
        reviews: list[Review],
        report_reason: str = "Spam or fake content",
        additional_info: str = "",
        country: str = "Türkiye",
        legal_name: str = "Doğukan Öztürk"
    ) -> bool:
        """
        Fill the report form with review information.
        
        Args:
            business: The business the review belongs to.
            reviews: List of reviews to report (supports multiple reviews).
            report_reason: Reason for reporting (e.g., "Spam", "Harassment").
            additional_info: Additional context for the report.
            country: Country of residence.
            legal_name: Full legal name for the form.
            
        Returns:
            True if form was filled successfully, False otherwise.
        """
        if not self._page:
            raise RuntimeError("Filler not initialized. Use async with statement.")
        
        # Handle single review for backwards compatibility
        if isinstance(reviews, Review):
            reviews = [reviews]
        
        if not reviews:
            print("❌ No reviews provided")
            return False
        
        await self.navigate_to_form()
        await asyncio.sleep(2)
        
        # Fill "Your information" section
        print("  Filling personal information...")
        
        # Fill country dropdown
        await self.fill_country_dropdown(country)
        await asyncio.sleep(0.5)
        
        # Fill legal name
        await self.fill_legal_name(legal_name)
        await asyncio.sleep(0.5)
        
        # Select "Someone else" for acting on behalf
        await self.select_acting_on_behalf(myself=False)
        await asyncio.sleep(1)
        
        # Select legal relationship: "Müşteri (ör. avukat veya başka bir yetkili temsilciyim)"
        await self.select_legal_relationship("Müşteri (ör. avukat veya başka bir yetkili temsilciyim)")
        await asyncio.sleep(1)
        
        # Fill customer name with business name
        await self.fill_customer_name(business.name)
        await asyncio.sleep(0.5)
        
        # NOT clicking on "Bu gönderim, yorum dışında bir konuyla mı ilgili?" checkbox
        # We leave it unchecked/untouched
        
        # Collect URLs from reviews
        urls_to_fill = []
        print("\n" + "="*60)
        print(f"🔍 URL'LER - {len(reviews)} yorum için:")
        
        for i, review in enumerate(reviews):
            if review.review_url:
                url = review.review_url
                print(f"  [{i+1}] ✅ {review.author_name} ({review.rating}⭐): {url[:50]}...")
            elif business.maps_url:
                url = business.maps_url
                print(f"  [{i+1}] ⚠️ {review.author_name} ({review.rating}⭐): business URL kullanılıyor")
            else:
                url = f"https://www.google.com/maps/search/{business.name}"
                print(f"  [{i+1}] ❌ {review.author_name} ({review.rating}⭐): fallback URL")
            urls_to_fill.append(url)
        
        print("="*60 + "\n")
        
        # Prepare unique random reasons for each URL
        random_reasons = self._get_random_reasons(len(urls_to_fill))
        
        # Fill multiple URLs and their corresponding reasons
        filled_count = await self.fill_multiple_urls(urls_to_fill, reasons=random_reasons)
        await asyncio.sleep(1)
        
        # Check confirmation checkbox
        print("  Filling confirmation section...")
        await self.check_confirmation_checkbox()
        await asyncio.sleep(0.5)
        
        # Fill signature field
        await self.fill_signature(legal_name)
        await asyncio.sleep(0.5)
        
        # Print summary for user
        print("\n" + "="*60)
        print("✓ Form dolduruldu! Detaylar:")
        print(f"  İşletme: {business.name}")
        print(f"  Raporlanan Yorum Sayısı: {len(reviews)}")
        for i, review in enumerate(reviews, 1):
            print(f"  [{i}] {review.author_name} - {'⭐' * review.rating} ({review.rating}/5)")
            print(f"      {review.text[:80]}{'...' if len(review.text) > 80 else ''}")
        print(f"  Doldurulan URL Sayısı: {filled_count}")
        print(f"  Ülke: {country}")
        print(f"  İsim: {legal_name}")
        print("="*60)
        print("\n⚠️  Lütfen formu manuel tamamlayın:")
        print("  1. Doldurulan alanları kontrol edin")
        print("  2. Uygun şikayet nedenini seçin")
        print("  3. CAPTCHA'yı tamamlayın")
        print("  4. Formu gönderin")
        print("="*60 + "\n")
        
        return True
    
    async def wait_for_user(self, timeout_seconds: int = 300) -> Optional[str]:
        """
        Wait for user to complete CAPTCHA and submit, then extract report ID.
        
        Args:
            timeout_seconds: How long to wait before timing out.
            
        Returns:
            Report ID if found, None otherwise.
        """
        if not self._page:
            raise RuntimeError("Filler not initialized. Use async with statement.")
        
        print(f"\n⏳ Formu manuel olarak gönderdikten sonra Raporlama Kimliği alınacak...")
        print(f"   (Maksimum bekleme süresi: {timeout_seconds} saniye)")
        print("   CAPTCHA'yı tamamlayın ve formu gönderin.\n")
        
        report_id = None
        
        try:
            # Wait for the report ID element to appear after form submission
            report_id_selector = '[data-test-id="report-id"]'
            
            # Poll for the report ID element
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < timeout_seconds:
                try:
                    # Check if report ID element is visible
                    report_id_element = self._page.locator(report_id_selector)
                    if await report_id_element.is_visible(timeout=2000):
                        # Extract the report ID from the text
                        text = await report_id_element.text_content()
                        if text and "Raporlama Kimliği:" in text:
                            # Extract the ID part: "Raporlama Kimliği: 9-2751000040847" -> "9-2751000040847"
                            report_id = text.replace("Raporlama Kimliği:", "").strip()
                            print(f"\n{'='*60}")
                            print(f"✅ RAPORLAMA KİMLİĞİ ALINDI: {report_id}")
                            print(f"{'='*60}\n")
                            return report_id
                except Exception:
                    pass
                
                # Wait a bit before checking again
                await asyncio.sleep(2)
            
            print("\n⚠️ Zaman aşımı: Raporlama Kimliği bulunamadı.")
            print("   Form gönderilmemiş olabilir veya sayfa değişmemiş olabilir.\n")
            
        except asyncio.CancelledError:
            print("Wait cancelled.")
        except Exception as e:
            print(f"⚠️ Raporlama Kimliği alınırken hata: {e}")
        
        return report_id


async def fill_report_form(
    business: Business,
    review: Review,
    report_reason: str = "Spam or fake content",
    additional_info: str = "",
    headless: bool = False,
    wait_for_captcha: bool = True,
    google_email: str = None,
    google_password: str = None,
    use_real_chrome: bool = True
) -> bool:
    """
    Convenience function to fill the report form.
    """
    async with ReportFiller(
        headless=headless,
        google_email=google_email,
        google_password=google_password,
        use_real_chrome=use_real_chrome
    ) as filler:
        success = await filler.fill_form(business, review, report_reason, additional_info)
        
        if success and wait_for_captcha:
            await filler.wait_for_user()
        
        return success
