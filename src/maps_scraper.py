"""Google Maps scraper using Playwright."""
import asyncio
import re
from typing import List, Optional
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout

from src.models import Review, Business
from src.browser_utils import get_chromium_launch_options


# Turkish city names (all 81 provinces) for location detection
TURKEY_CITIES = {
    "istanbul", "İstanbul", "ankara", "Ankara", "izmir", "İzmir",
    "bursa", "Bursa", "antalya", "Antalya", "adana", "Adana",
    "konya", "Konya", "gaziantep", "Gaziantep", "mersin", "Mersin",
    "diyarbakır", "Diyarbakır", "kayseri", "Kayseri", "eskişehir", "Eskişehir",
    "samsun", "Samsun", "trabzon", "Trabzon", "denizli", "Denizli",
    "malatya", "Malatya", "erzurum", "Erzurum", "van", "Van",
    "batman", "Batman", "şanlıurfa", "Şanlıurfa", "elazığ", "Elazığ",
    "sakarya", "Sakarya", "kocaeli", "Kocaeli", "aydın", "Aydın",
    "muğla", "Muğla", "tekirdağ", "Tekirdağ", "manisa", "Manisa",
    "hatay", "Hatay", "balıkesir", "Balıkesir", "mardin", "Mardin",
    "kahramanmaraş", "Kahramanmaraş", "afyonkarahisar", "Afyonkarahisar",
    "sivas", "Sivas", "kütahya", "Kütahya", "çorum", "Çorum",
    "tokat", "Tokat", "çanakkale", "Çanakkale", "rize", "Rize",
    "ordu", "Ordu", "edirne", "Edirne", "düzce", "Düzce",
    "isparta", "Isparta", "giresun", "Giresun", "aksaray", "Aksaray",
    "yozgat", "Yozgat", "nevşehir", "Nevşehir", "niğde", "Niğde",
    "kırıkkale", "Kırıkkale", "bolu", "Bolu", "karabük", "Karabük",
    "kırşehir", "Kırşehir", "burdur", "Burdur", "ağrı", "Ağrı",
    "amasya", "Amasya", "artvin", "Artvin", "bartın", "Bartın",
    "bayburt", "Bayburt", "bilecik", "Bilecik", "bingöl", "Bingöl",
    "bitlis", "Bitlis", "çankırı", "Çankırı", "erzincan", "Erzincan",
    "gümüşhane", "Gümüşhane", "hakkari", "Hakkari", "iğdır", "Iğdır",
    "kars", "Kars", "kastamonu", "Kastamonu", "kilis", "Kilis",
    "muş", "Muş", "osmaniye", "Osmaniye", "siirt", "Siirt",
    "sinop", "Sinop", "şırnak", "Şırnak", "tunceli", "Tunceli",
    "uşak", "Uşak", "yalova", "Yalova", "zonguldak", "Zonguldak",
    "ardahan", "Ardahan",
}


def is_turkey_location(address: Optional[str]) -> bool:
    """
    Check if the given address is located in Turkey.
    
    Uses multiple indicators to determine if the address is in Turkey:
    1. Contains 'Türkiye' or 'Turkey'
    2. Contains Turkish city names
    
    Note: We don't rely on postal codes alone since they can overlap with 
    other countries (e.g., US zip codes like 10001).
    
    Args:
        address: The address string to check.
        
    Returns:
        True if the address is in Turkey, False otherwise.
    """
    if not address or not address.strip():
        return False
    
    address_lower = address.lower()
    
    # Check for explicit country name
    if "türkiye" in address_lower or "turkey" in address_lower:
        return True
    
    # Check for Turkish city names (case-insensitive)
    for city in TURKEY_CITIES:
        if city.lower() in address_lower:
            return True
    
    return False


class MapsScraper:
    """Scraper for Google Maps reviews."""
    
    # Multiple possible selectors for search box
    SEARCH_SELECTORS = [
        "#searchboxinput",
        "input[name='q']",
        "input[aria-label*='Search']",
        "input[aria-label*='Ara']",  # Turkish
        "input.searchboxinput",
        "[data-value='Search Google Maps']",
    ]
    
    # Cookie consent button selectors (multiple languages)
    COOKIE_SELECTORS = [
        "button:has-text('Accept all')",
        "button:has-text('Tümünü kabul et')",  # Turkish
        "button:has-text('Kabul et')",
        "button:has-text('Accept')",
        "[aria-label='Accept all']",
        "form[action*='consent'] button",
    ]
    
    def __init__(self, headless: bool = False):
        """
        Initialize the scraper.
        
        Args:
            headless: Whether to run browser in headless mode.
        """
        self.headless = headless
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        playwright = await async_playwright().start()
        self._playwright = playwright
        
        # Get launch options with bundled browser support (for EXE)
        launch_options = get_chromium_launch_options(headless=self.headless)
        self._browser = await playwright.chromium.launch(**launch_options)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="tr-TR",
            permissions=["clipboard-read", "clipboard-write"]
        )
        self._page = await self._context.new_page()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
    
    async def _handle_cookie_consent(self):
        """Handle cookie consent dialogs."""
        for selector in self.COOKIE_SELECTORS:
            try:
                button = self._page.locator(selector).first
                if await button.is_visible(timeout=2000):
                    await button.click()
                    await asyncio.sleep(1)
                    print("  ✓ Cookie consent handled")
                    return True
            except:
                continue
        return False
    
    async def _find_search_box(self):
        """Find the search box using multiple selectors."""
        for selector in self.SEARCH_SELECTORS:
            try:
                search_box = self._page.locator(selector).first
                if await search_box.is_visible(timeout=3000):
                    return search_box
            except:
                continue
        return None
    
    async def search_business(self, business_name: str) -> Optional[Business]:
        """
        Search for a business on Google Maps.
        
        Args:
            business_name: Name of the business to search for.
            
        Returns:
            Business object if found, None otherwise.
        """
        if not self._page:
            raise RuntimeError("Scraper not initialized. Use async with statement.")
        
        # Go to Google Maps
        print("  Loading Google Maps...")
        await self._page.goto("https://www.google.com/maps", wait_until="domcontentloaded")
        await asyncio.sleep(3)  # Wait for JS to load
        
        # Handle cookie consent
        await self._handle_cookie_consent()
        await asyncio.sleep(1)
        
        # Find and use search box
        search_box = await self._find_search_box()
        
        if not search_box:
            # Try direct URL approach as fallback
            print("  Search box not found, trying direct URL...")
            encoded_name = business_name.replace(" ", "+")
            await self._page.goto(
                f"https://www.google.com/maps/search/{encoded_name}",
                wait_until="domcontentloaded"
            )
            await asyncio.sleep(3)
        else:
            print("  Searching...")
            await search_box.click()
            await asyncio.sleep(0.5)
            await search_box.fill(business_name)
            await asyncio.sleep(0.5)
            await search_box.press("Enter")
        
        # Wait for results
        await self._page.wait_for_load_state("networkidle")
        await asyncio.sleep(3)  # Extra wait for dynamic content
        
        # Click on first result if there are multiple (search results page)
        print("  Looking for business in results...")
        try:
            # Multiple selectors for search results
            result_selectors = [
                "[role='feed'] a[href*='/maps/place']",
                ".Nv2PK",  # Result card class
                "[role='article']",
                "a[href*='place']",
            ]
            
            for selector in result_selectors:
                try:
                    first_result = self._page.locator(selector).first
                    if await first_result.is_visible(timeout=3000):
                        await first_result.click()
                        await asyncio.sleep(3)
                        print("  ✓ Clicked on first result")
                        break
                except:
                    continue
        except:
            pass  # Already on a single business page
        
        # Try to get business info from the panel
        try:
            # Wait for the business panel to appear - look for specific business page indicators
            await asyncio.sleep(2)
            
            # Wait for h1 that's not "Sonuçlar" or "Results"
            for _ in range(10):
                name_element = self._page.locator("h1").first
                if await name_element.is_visible(timeout=2000):
                    name = await name_element.text_content()
                    # Skip if it's still showing "Results"
                    if name and name.strip() not in ["Sonuçlar", "Results", "Search results"]:
                        break
                await asyncio.sleep(1)
            
            # Get current URL as maps_url
            maps_url = self._page.url
            
            # Try to get address
            address = None
            try:
                address_element = self._page.locator("[data-item-id='address']")
                if await address_element.is_visible(timeout=2000):
                    address = await address_element.text_content()
            except PlaywrightTimeout:
                pass
            
            final_name = name.strip() if (name and name.strip() not in ["Sonuçlar", "Results"]) else business_name
            
            return Business(
                name=final_name,
                maps_url=maps_url,
                address=address
            )
        except PlaywrightTimeout:
            print("  Could not find business panel")
            return None
    
    async def navigate_to_maps_url(self, maps_url: str) -> Optional[Business]:
        """
        Navigate directly to a Google Maps URL using dual-tab approach.
        
        The Yorumlar (Reviews) tab doesn't appear on first visit, but appears
        when opening the same link in a second tab. So we:
        1. Open first tab with the URL
        2. Wait briefly
        3. Open second tab with the same URL
        4. Close the first tab
        5. Continue on the second tab where Yorumlar is visible
        
        Args:
            maps_url: Direct Google Maps URL (e.g., https://maps.app.goo.gl/xxx)
            
        Returns:
            Business object if navigation successful, None otherwise.
        """
        if not self._page:
            raise RuntimeError("Scraper not initialized. Use async with statement.")
        
        print(f"  Opening Maps URL in first tab: {maps_url}")
        
        # Step 1: Navigate first tab to the URL
        first_page = self._page
        await first_page.goto(maps_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)  # Wait for JS to load
        
        # Handle cookie consent on first tab
        await self._handle_cookie_consent()
        await asyncio.sleep(2)
        
        # Step 2: Open second tab with the same URL
        print("  Opening second tab (Yorumlar sekmesi burada görünecek)...")
        second_page = await self._context.new_page()
        await second_page.goto(maps_url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        
        # Step 3: Close first tab
        print("  Closing first tab...")
        await first_page.close()
        
        # Step 4: Continue on second tab
        self._page = second_page
        await asyncio.sleep(2)
        
        # Get business info from the page
        try:
            # Wait for h1 that contains the business name
            name = None
            for _ in range(10):
                name_element = self._page.locator("h1").first
                if await name_element.is_visible(timeout=2000):
                    name = await name_element.text_content()
                    if name and name.strip() not in ["Sonuçlar", "Results", "Search results"]:
                        break
                await asyncio.sleep(1)
            
            # Get current URL
            current_url = self._page.url
            
            # Try to get address
            address = None
            try:
                address_element = self._page.locator("[data-item-id='address']")
                if await address_element.is_visible(timeout=2000):
                    address = await address_element.text_content()
            except PlaywrightTimeout:
                pass
            
            final_name = name.strip() if name else "Unknown Business"
            
            print(f"  ✓ Navigated to: {final_name}")
            
            return Business(
                name=final_name,
                maps_url=current_url,
                address=address
            )
        except Exception as e:
            print(f"  Could not get business info: {e}")
            return None
    
    async def _click_yorumlar_tab(self):
        """
        Click on the Yorumlar (Reviews) tab that appears under the restaurant name.
        
        This is different from the reviews button in search results.
        The tab is next to: Genel Bakış - Menü - Yorumlar - Hakkında
        """
        if not self._page:
            raise RuntimeError("Scraper not initialized. Use async with statement.")
        
        print("  Clicking on Yorumlar tab...")
        
        # Selectors for the Yorumlar tab under restaurant name
        # These tabs are typically in a tab list under the business name
        yorumlar_tab_selectors = [
            # Tab button with text Yorumlar
            "[role='tablist'] button:has-text('Yorumlar')",
            "[role='tablist'] [role='tab']:has-text('Yorumlar')",
            "button[aria-label*='Yorumlar']",
            # Generic tab selectors
            "[role='tab']:has-text('Yorumlar')",
            "[role='tab']:has-text('Reviews')",
            # Div-based tabs
            "div[role='tablist'] div:has-text('Yorumlar')",
            # Button in header area
            "button:has-text('Yorumlar')",
            "button:has-text('Reviews')",
            # Aria labels
            "[aria-label='Yorumlar']",
            "[aria-label='Reviews']",
        ]
        
        for selector in yorumlar_tab_selectors:
            try:
                tab = self._page.locator(selector).first
                if await tab.is_visible(timeout=2000):
                    await tab.click()
                    print(f"  ✓ Clicked Yorumlar tab with selector: {selector}")
                    await asyncio.sleep(2)
                    return True
            except Exception:
                continue
        
        print("  ⚠ Could not find Yorumlar tab, trying alternative approach...")
        
        # Alternative: Look for any clickable element with "yorum" text
        try:
            yorum_elements = self._page.locator("text=/[Yy]orum/")
            count = await yorum_elements.count()
            print(f"  Found {count} elements with 'Yorum' text")
            
            for i in range(min(count, 5)):
                el = yorum_elements.nth(i)
                try:
                    if await el.is_visible(timeout=500):
                        text = await el.text_content()
                        # Skip if it's a review count like "1.234 yorum"
                        if text and ("yorum" in text.lower() or "review" in text.lower()):
                            await el.click()
                            print(f"  ✓ Clicked element: {text}")
                            await asyncio.sleep(2)
                            return True
                except:
                    continue
        except Exception as e:
            print(f"  Alternative approach failed: {e}")
        
        return False
    
    async def _sort_by_lowest_rating(self):
        """
        Sort reviews by lowest rating.
        Click on the sort dropdown and select lowest rating option.
        """
        if not self._page:
            return False
        
        print("  Sorting by lowest rating...")
        
        try:
            # First, click the sort dropdown button (usually shows "En alakalı" or "Most relevant")
            sort_selectors = [
                "button[aria-label='Sort reviews']",
                "button[aria-label*='Sırala']",
                "button[aria-label*='Yorumları sırala']",
                "button[data-value='Sort']",
                "[aria-label*='sort']",
                "button:has-text('En alakalı')",
                "button:has-text('Most relevant')",
            ]
            
            for selector in sort_selectors:
                try:
                    sort_button = self._page.locator(selector).first
                    if await sort_button.is_visible(timeout=2000):
                        await sort_button.click()
                        print(f"  ✓ Clicked sort button: {selector}")
                        await asyncio.sleep(1)
                        break
                except:
                    continue
            
            # Use the exact locator: get_by_role("menuitemradio", name="En düşük puanlı")
            print("  → 'En düşük puanlı' seçeneği aranıyor...")
            lowest_option = self._page.get_by_role("menuitemradio", name="En düşük puanlı")
            
            if await lowest_option.is_visible(timeout=3000):
                await lowest_option.click()
                print("  ✓ 'En düşük puanlı' seçildi!")
                await asyncio.sleep(2)
                return True
            else:
                # Fallback to English
                lowest_option_en = self._page.get_by_role("menuitemradio", name="Lowest rating")
                if await lowest_option_en.is_visible(timeout=2000):
                    await lowest_option_en.click()
                    print("  ✓ 'Lowest rating' selected!")
                    await asyncio.sleep(2)
                    return True
                    
        except Exception as e:
            print(f"  Could not sort reviews: {e}")
        
        return False
    
    async def get_reviews(self, business: Business, max_reviews: int = 50, get_share_links: bool = True, from_direct_url: bool = False) -> List[Review]:
        """
        Get reviews for a business.
        
        Args:
            business: Business to get reviews for.
            max_reviews: Maximum number of reviews to fetch.
            get_share_links: Whether to get share links for each review.
            from_direct_url: Whether we navigated directly to the Maps URL.
                             If True, uses the Yorumlar tab under restaurant name.
            
        Returns:
            List of Review objects.
        """
        if not self._page:
            raise RuntimeError("Scraper not initialized. Use async with statement.")
        
        reviews = []
        
        # Click on reviews tab - use different approach based on navigation method
        if from_direct_url:
            # Use the Yorumlar tab under restaurant name (next to Genel Bakış, Menü, Hakkında)
            await self._click_yorumlar_tab()
        else:
            # Original approach: Click on reviews button in search results
            print("  Opening reviews...")
            try:
                review_selectors = [
                    "button[aria-label*='Reviews']",
                    "button[aria-label*='Yorum']",
                    "[role='tab']:has-text('Reviews')",
                    "[role='tab']:has-text('Yorumlar')",
                    "button:has-text('reviews')",
                    "button:has-text('yorum')",
                ]
                
                for selector in review_selectors:
                    try:
                        reviews_button = self._page.locator(selector).first
                        if await reviews_button.is_visible(timeout=2000):
                            await reviews_button.click()
                            await asyncio.sleep(2)
                            break
                    except:
                        continue
            except:
                pass  # Reviews might already be visible
        
        # Sort by lowest rating (use dedicated method)
        await self._sort_by_lowest_rating()
        
        # Scroll to load more reviews
        print("  Loading reviews...")
        try:
            # Find scrollable reviews container
            scroll_selectors = [
                "[role='main']",
                ".m6QErb.DxyBCb",
                "[class*='section-scrollbox']",
            ]
            
            for selector in scroll_selectors:
                try:
                    reviews_container = self._page.locator(selector).first
                    if await reviews_container.is_visible(timeout=2000):
                        for _ in range(5):  # Scroll more times
                            await reviews_container.evaluate("el => el.scrollTop = el.scrollHeight")
                            await asyncio.sleep(1)
                        break
                except:
                    continue
        except:
            pass
        
        # Parse reviews
        print("  Parsing reviews...")
        # We want to target only the actual review containers, skipping separators
        # The actual reviews have class 'jftiEf' and 'fontBodyMedium'
        review_selectors = [
            "div.jftiEf.fontBodyMedium",
            "[data-review-id]",
            "[class*='jftiEf']",  # Review container class
            ".gws-localreviews__google-review",
        ]
        
        review_elements = None
        for selector in review_selectors:
            try:
                review_elements = self._page.locator(selector)
                count = await review_elements.count()
                if count > 0:
                    break
            except:
                continue
        
        if not review_elements:
            return reviews
        
        count = await review_elements.count()
        print(f"  Found {count} review elements")
        
        if get_share_links:
            print("  Getting share links for reviews...")
        
        for i in range(min(count, max_reviews)):
            try:
                review_el = review_elements.nth(i)
                
                # Get author name - try multiple selectors
                author_name = "Unknown"
                author_selectors = [
                    "[class*='d4r55']",
                    "[class*='TSUbDb']",
                    ".review-author",
                    "button[data-review-id] > div",
                ]
                for sel in author_selectors:
                    try:
                        author_el = review_el.locator(sel).first
                        if await author_el.is_visible(timeout=500):
                            author_name = await author_el.text_content()
                            break
                    except:
                        continue
                
                # Get rating from stars
                rating = 3
                try:
                    rating_el = review_el.locator("[role='img'][aria-label*='star'], [role='img'][aria-label*='yıldız']").first
                    if await rating_el.is_visible(timeout=500):
                        rating_text = await rating_el.get_attribute("aria-label")
                        rating_match = re.search(r"(\d+)", rating_text or "3")
                        rating = int(rating_match.group(1)) if rating_match else 3
                except:
                    pass
                
                # Get review text
                text = ""
                text_selectors = [
                    "[class*='wiI7pd']",
                    "[class*='review-full-text']",
                    ".review-text",
                    "[data-review-id] span",
                ]
                
                # Try to expand "More" if present
                try:
                    more_button = review_el.locator("button:has-text('More'), button:has-text('Daha fazla')").first
                    if await more_button.is_visible(timeout=300):
                        await more_button.click()
                        await asyncio.sleep(0.3)
                except:
                    pass
                
                for sel in text_selectors:
                    try:
                        text_el = review_el.locator(sel).first
                        if await text_el.is_visible(timeout=500):
                            text = await text_el.text_content()
                            if text and len(text) > 5:
                                break
                    except:
                        continue
                
                # Get date
                date = None
                date_selectors = [
                    "[class*='rsqaWe']",
                    "[class*='review-date']",
                    "span:has-text('ago'), span:has-text('önce')",
                ]
                for sel in date_selectors:
                    try:
                        date_el = review_el.locator(sel).first
                        if await date_el.is_visible(timeout=500):
                            date = await date_el.text_content()
                            break
                    except:
                        continue
                
                # Get share link for this review (only if requested - usually skip this)
                review_url = None
                if get_share_links:
                    review_url = await self._get_share_link_for_element(review_el)
                
                if rating >= 1 and rating <= 5:
                    reviews.append(Review(
                        author_name=author_name.strip() if author_name else "Unknown",
                        rating=rating,
                        text=text.strip() if text else "",
                        date=date.strip() if date else None,
                        review_url=review_url
                    ))
            except Exception as e:
                print(f"  Error parsing review {i}: {e}")
                continue
        
        return reviews
    
    async def get_share_link_for_review_at_index(self, review_index: int) -> Optional[str]:
        """
        Get share link for a specific review at the given index.
        Call this AFTER get_reviews() while still in the same browser context.
        
        Args:
            review_index: The index of the review (0-based, matches the order from get_reviews)
            
        Returns:
            The share URL or None if not found.
        """
        if not self._page:
            raise RuntimeError("Scraper not initialized. Use async with statement.")
        
        print(f"\n  🔗 Getting share link for review at index {review_index}...")

        
        
        # Find review elements again
        # We want to target only the actual review containers, skipping separators
        review_selectors = [
            "div.jftiEf.fontBodyMedium",
            "[data-review-id]",
            "[class*='jftiEf']",
            ".gws-localreviews__google-review",
        ]
        
        review_elements = None
        for selector in review_selectors:
            try:
                review_elements = self._page.locator(selector)
                count = await review_elements.count()
                if count > 0:
                    break
            except:
                continue
        
        if not review_elements:
            print("  ❌ Could not find review elements")
            return None
        
        count = await review_elements.count()
        if review_index >= count:
            print(f"  ❌ Index {review_index} is out of range (only {count} reviews)")
            return None
        
        # Get the specific review element
        review_el = review_elements.nth(review_index)
        
        # Get share link
        share_url = await self._get_share_link_for_element(review_el)
        
        # LOG: Track what URL was retrieved
        print(f"\n  📝 SHARE LINK SONUCU (index={review_index}):")
        print(f"     _get_share_link_for_element() döndürdü: {repr(share_url)}")
        if share_url:
            if share_url.startswith("https://maps.app.goo.gl/"):
                print(f"     ✅ DOĞRU FORMAT: Kısa share link")
            else:
                print(f"     ⚠️ YANLIŞ FORMAT: Bu kısa share link DEĞİL!")
        else:
            print(f"     ❌ URL BOŞ döndü!")
        
        return share_url
    
    async def _get_share_link_for_element(self, review_el) -> Optional[str]:
        """
        Get the share link for a review element.
        
        Flow:
        1. Click the action menu button (three-dot menu)
        2. Click "Yorumu paylaş" in the dropdown
        3. Get the link from the dialog textbox
        
        Args:
            review_el: The Playwright locator for the review element.
            
        Returns:
            The share URL or None if not found.
        """
        final_share_url = None
        
        try:
            # Close any existing dialogs first
            print("    → Mevcut dialoglar kapatılıyor...")
            for _ in range(2):
                await self._page.keyboard.press("Escape")
                await asyncio.sleep(0.2)
            
            # Step 1: Click the action menu button (three-dot menu)
            # Use: get_by_label("Eylem adlı kullanıcının yorumu üzerinde yapılacak işlemler")
            print("    → Eylem menüsü butonu aranıyor...")
            
            # Try to find the action button within the review element
            # The label contains the reviewer's name, so we need a partial match
            action_button = None
            
            # First try: Look for button with aria-label containing "işlemler" (actions)
            try:
                action_button = review_el.locator("button[aria-label*='işlemler']").first
                if not await action_button.is_visible(timeout=1000):
                    action_button = None
            except:
                action_button = None
            
            # Second try: Look for button with aria-label containing "actions"
            if not action_button:
                try:
                    action_button = review_el.locator("button[aria-label*='actions']").first
                    if not await action_button.is_visible(timeout=1000):
                        action_button = None
                except:
                    action_button = None
            
            # Third try: Look for the menu button by class or other attributes
            if not action_button:
                menu_selectors = [
                    "button[data-value='More actions']",
                    "button[aria-label*='More']",
                    "button[aria-label*='Daha fazla']",
                    "[aria-label='İşlem menüsü']",
                    "[aria-label='Action menu']",
                    "button.g88MCb",
                ]
                for selector in menu_selectors:
                    try:
                        btn = review_el.locator(selector).first
                        if await btn.is_visible(timeout=500):
                            action_button = btn
                            break
                    except:
                        continue
            
            if not action_button:
                print("    ⚠ Eylem menüsü butonu bulunamadı!")
                return None
            
            print("    → Eylem menüsü butonuna tıklanıyor...")
            await action_button.click()
            await asyncio.sleep(1)
            
            # Step 2: Click "Yorumu paylaş" in the dropdown
            # Use: get_by_role("menuitemradio", name="Yorumu paylaş")
            print("    → 'Yorumu paylaş' seçeneği aranıyor...")
            
            share_option = self._page.get_by_role("menuitemradio", name="Yorumu paylaş")
            
            try:
                if await share_option.is_visible(timeout=3000):
                    await share_option.click()
                    print("    ✓ 'Yorumu paylaş' tıklandı!")
                    await asyncio.sleep(2)
                else:
                    # Try English version
                    share_option_en = self._page.get_by_role("menuitemradio", name="Share review")
                    if await share_option_en.is_visible(timeout=2000):
                        await share_option_en.click()
                        print("    ✓ 'Share review' clicked!")
                        await asyncio.sleep(2)
                    else:
                        print("    ⚠ 'Yorumu paylaş' seçeneği bulunamadı!")
                        await self._page.keyboard.press("Escape")
                        return None
            except Exception as e:
                print(f"    ❌ 'Yorumu paylaş' tıklanamadı: {e}")
                await self._page.keyboard.press("Escape")
                return None
            
            # Step 3: Get the link by clicking "Bağlantıyı kopyala" button
            # Use: get_by_role("button", name="Bağlantıyı kopyala")
            print("    → 'Bağlantıyı kopyala' butonu aranıyor...")
            
            try:
                copy_button = self._page.get_by_role("button", name="Bağlantıyı kopyala")
                
                if await copy_button.is_visible(timeout=3000):
                    # Click to copy to clipboard
                    await copy_button.click()
                    print("    ✓ 'Bağlantıyı kopyala' tıklandı!")
                    await asyncio.sleep(0.5)
                    
                    # Read from clipboard using JavaScript
                    share_url = await self._page.evaluate("navigator.clipboard.readText()")
                    
                    if share_url and "maps.app.goo.gl" in share_url:
                        final_share_url = share_url.strip()
                        print(f"    ✓ Share link alındı: {final_share_url}")
                    else:
                        print(f"    ⚠ Clipboard'da geçerli link yok: {share_url}")
                else:
                    # Try English version
                    copy_button_en = self._page.get_by_role("button", name="Copy link")
                    if await copy_button_en.is_visible(timeout=2000):
                        await copy_button_en.click()
                        print("    ✓ 'Copy link' clicked!")
                        await asyncio.sleep(0.5)
                        
                        share_url = await self._page.evaluate("navigator.clipboard.readText()")
                        if share_url and "maps.app.goo.gl" in share_url:
                            final_share_url = share_url.strip()
                            print(f"    ✓ Share link alındı: {final_share_url}")
                    else:
                        print("    ⚠ 'Bağlantıyı kopyala' butonu görünmüyor!")
                    
            except Exception as e:
                print(f"    ❌ Link kopyalanamadı: {e}")
            
            # Close the dialog using the Kapat button
            print("    → Dialog kapatılıyor...")
            try:
                close_button = self._page.get_by_role("dialog").get_by_label("Kapat")
                if await close_button.is_visible(timeout=2000):
                    await close_button.click()
                    print("    ✓ Dialog 'Kapat' butonu ile kapatıldı")
                else:
                    # Fallback to Escape
                    await self._page.keyboard.press("Escape")
                    print("    ✓ Dialog Escape ile kapatıldı")
            except Exception as close_err:
                print(f"    ⚠ Kapat butonu tıklanamadı, Escape deneniyor: {close_err}")
                await self._page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
            
            return final_share_url
            
        except Exception as e:
            print(f"    ❌ GENEL HATA: {type(e).__name__}: {e}")
            try:
                # Try to close dialog properly
                close_button = self._page.get_by_role("dialog").get_by_label("Kapat")
                if await close_button.is_visible(timeout=1000):
                    await close_button.click()
                else:
                    await self._page.keyboard.press("Escape")
            except:
                try:
                    await self._page.keyboard.press("Escape")
                except:
                    pass
            return final_share_url
    
async def scrape_lowest_review(business_name: str, headless: bool = False) -> tuple[Business, Review]:
    """
    Convenience function to scrape the lowest rated review for a business.
    
    Args:
        business_name: Name of the business to search for.
        headless: Whether to run browser in headless mode.
        
    Returns:
        Tuple of (Business, Review) for the lowest rated review.
        
    Raises:
        ValueError: If business not found or no reviews available.
    """
    from src.review_finder import find_lowest_rated_review
    
    async with MapsScraper(headless=headless) as scraper:
        business = await scraper.search_business(business_name)
        if not business:
            raise ValueError(f"Business not found: {business_name}")
        
        reviews = await scraper.get_reviews(business)
        if not reviews:
            raise ValueError(f"No reviews found for: {business_name}")
        
        lowest_review = find_lowest_rated_review(reviews)
        return business, lowest_review
