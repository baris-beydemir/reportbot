"""Tests for Maps scraper with direct URL navigation."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.maps_scraper import MapsScraper, is_turkey_location
from src.models import Business


class TestNavigateToMapsUrl:
    """Tests for navigating directly to a Maps URL."""
    
    @pytest.mark.asyncio
    async def test_navigate_to_maps_url_opens_two_tabs(self):
        """Should open two tabs - first one triggers the reviews tab visibility on second."""
        scraper = MapsScraper(headless=True)
        
        # Create mock for first page (already exists)
        mock_page1 = AsyncMock()
        mock_page1.goto = AsyncMock()
        mock_page1.close = AsyncMock()
        
        # Create mock for second page
        mock_page2 = AsyncMock()
        mock_page2.goto = AsyncMock()
        mock_page2.url = "https://www.google.com/maps/place/Konyali+Restaurant"
        
        # Mock h1 locator for business name
        mock_h1 = AsyncMock()
        mock_h1.is_visible = AsyncMock(return_value=True)
        mock_h1.text_content = AsyncMock(return_value="Konyali Restaurant")
        
        # Mock address locator
        mock_address = AsyncMock()
        mock_address.is_visible = AsyncMock(return_value=False)
        
        def locator_side_effect(selector):
            if selector == "h1":
                return MagicMock(first=mock_h1)
            elif selector == "[data-item-id='address']":
                return mock_address
            return MagicMock(first=AsyncMock(is_visible=AsyncMock(return_value=False)))
        
        mock_page2.locator = locator_side_effect
        
        # Setup context mock
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page2)
        
        scraper._browser = AsyncMock()
        scraper._context = mock_context
        scraper._page = mock_page1
        scraper._handle_cookie_consent = AsyncMock()
        
        maps_url = "https://maps.app.goo.gl/8hhn6aYo7Cy78HjK7"
        
        await scraper.navigate_to_maps_url(maps_url)
        
        # Verify first tab was navigated to
        mock_page1.goto.assert_called_once()
        assert maps_url in str(mock_page1.goto.call_args)
        
        # Verify second tab was created and navigated
        mock_context.new_page.assert_called_once()
        mock_page2.goto.assert_called_once()
        
        # Verify first tab was closed
        mock_page1.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_navigate_to_maps_url_returns_business(self):
        """Should return Business object with info from the page."""
        scraper = MapsScraper(headless=True)
        
        # Create mock for first page
        mock_page1 = AsyncMock()
        mock_page1.goto = AsyncMock()
        mock_page1.close = AsyncMock()
        
        # Create mock for second page
        mock_page2 = AsyncMock()
        mock_page2.goto = AsyncMock()
        mock_page2.url = "https://www.google.com/maps/place/Konyali+Restaurant"
        
        # Mock h1 locator for business name
        mock_h1 = AsyncMock()
        mock_h1.is_visible = AsyncMock(return_value=True)
        mock_h1.text_content = AsyncMock(return_value="Konyali Restaurant")
        
        # Mock address locator
        mock_address = AsyncMock()
        mock_address.is_visible = AsyncMock(return_value=False)
        
        def locator_side_effect(selector):
            if selector == "h1":
                return MagicMock(first=mock_h1)
            elif selector == "[data-item-id='address']":
                return mock_address
            return MagicMock(first=AsyncMock(is_visible=AsyncMock(return_value=False)))
        
        mock_page2.locator = locator_side_effect
        
        # Setup context mock
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page2)
        
        scraper._browser = AsyncMock()
        scraper._context = mock_context
        scraper._page = mock_page1
        scraper._handle_cookie_consent = AsyncMock()
        
        business = await scraper.navigate_to_maps_url("https://maps.app.goo.gl/8hhn6aYo7Cy78HjK7")
        
        assert business is not None
        assert business.name == "Konyali Restaurant"
        assert business.maps_url == "https://www.google.com/maps/place/Konyali+Restaurant"


class TestClickYorumlarTab:
    """Tests for clicking the Yorumlar (Reviews) tab under restaurant name."""
    
    @pytest.mark.asyncio
    async def test_click_yorumlar_tab_finds_correct_button(self):
        """Should click on Yorumlar tab that's next to Genel Bakış, Menü, Hakkında."""
        scraper = MapsScraper(headless=True)
        
        mock_page = AsyncMock()
        
        # Mock the tab button
        mock_tab = AsyncMock()
        mock_tab.is_visible = AsyncMock(return_value=True)
        mock_tab.click = AsyncMock()
        
        def locator_side_effect(selector):
            return MagicMock(first=mock_tab)
        
        mock_page.locator = locator_side_effect
        scraper._page = mock_page
        
        result = await scraper._click_yorumlar_tab()
        
        # Verify click was called
        assert mock_tab.click.called
        assert result is True


class TestGetReviewsFromDirectUrl:
    """Tests for getting reviews when navigating directly to Maps URL."""
    
    @pytest.mark.asyncio
    async def test_get_reviews_with_direct_url_uses_yorumlar_tab(self):
        """Should use _click_yorumlar_tab when from_direct_url=True."""
        scraper = MapsScraper(headless=True)
        
        mock_page = AsyncMock()
        scraper._page = mock_page
        
        # Mock _click_yorumlar_tab
        scraper._click_yorumlar_tab = AsyncMock()
        scraper._sort_by_lowest_rating = AsyncMock()
        
        # Mock review elements (empty for simplicity)
        mock_element = AsyncMock()
        mock_element.count = AsyncMock(return_value=0)
        mock_element.is_visible = AsyncMock(return_value=False)
        mock_element.evaluate = AsyncMock()
        
        mock_page.locator = MagicMock(return_value=mock_element)
        
        business = Business(name="Test Restaurant", maps_url="https://maps.app.goo.gl/test")
        
        # Call with from_direct_url=True
        await scraper.get_reviews(business, max_reviews=10, get_share_links=False, from_direct_url=True)
        
        # Should have called _click_yorumlar_tab
        scraper._click_yorumlar_tab.assert_called_once()
        scraper._sort_by_lowest_rating.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_reviews_without_direct_url_uses_original_approach(self):
        """Should use original button selectors when from_direct_url=False."""
        scraper = MapsScraper(headless=True)
        
        mock_page = AsyncMock()
        scraper._page = mock_page
        
        # Mock _click_yorumlar_tab - should NOT be called
        scraper._click_yorumlar_tab = AsyncMock()
        scraper._sort_by_lowest_rating = AsyncMock()
        
        # Mock review elements
        mock_element = AsyncMock()
        mock_element.count = AsyncMock(return_value=0)
        mock_element.is_visible = AsyncMock(return_value=False)
        mock_element.evaluate = AsyncMock()
        
        mock_page.locator = MagicMock(return_value=mock_element)
        
        business = Business(name="Test Restaurant", maps_url="https://maps.app.goo.gl/test")
        
        # Call without from_direct_url (default False)
        await scraper.get_reviews(business, max_reviews=10, get_share_links=False, from_direct_url=False)
        
        # Should NOT have called _click_yorumlar_tab
        scraper._click_yorumlar_tab.assert_not_called()
        # But should have called _sort_by_lowest_rating
        scraper._sort_by_lowest_rating.assert_called_once()


class TestIsTurkeyLocation:
    """Tests for is_turkey_location function that checks if an address is in Turkey."""
    
    def test_returns_true_for_turkiye_in_address(self):
        """Should return True when address contains 'Türkiye'."""
        address = "Cankurtaran, Kennedy Cd. No:1, 34122 Fatih/İstanbul, Türkiye"
        assert is_turkey_location(address) is True
    
    def test_returns_true_for_turkey_in_address(self):
        """Should return True when address contains 'Turkey'."""
        address = "Cankurtaran, Kennedy Cd. No:1, 34122 Fatih/Istanbul, Turkey"
        assert is_turkey_location(address) is True
    
    def test_returns_true_for_lowercase_turkey(self):
        """Should return True when address contains 'turkey' in lowercase."""
        address = "Istiklal Street, Istanbul, turkey"
        assert is_turkey_location(address) is True
    
    def test_returns_true_for_lowercase_turkiye(self):
        """Should return True when address contains 'türkiye' in lowercase."""
        address = "Cankurtaran Mah., 34122 Fatih/İstanbul, türkiye"
        assert is_turkey_location(address) is True
    
    def test_returns_false_for_foreign_address(self):
        """Should return False when address is from another country."""
        address = "123 Main Street, New York, NY 10001, United States"
        assert is_turkey_location(address) is False
    
    def test_returns_false_for_germany_address(self):
        """Should return False when address is from Germany."""
        address = "Friedrichstraße 123, 10117 Berlin, Germany"
        assert is_turkey_location(address) is False
    
    def test_returns_false_for_greece_address(self):
        """Should return False when address is from Greece."""
        address = "Monastiraki Square, Athens 105 55, Greece"
        assert is_turkey_location(address) is False
    
    def test_returns_false_for_none_address(self):
        """Should return False when address is None."""
        assert is_turkey_location(None) is False
    
    def test_returns_false_for_empty_address(self):
        """Should return False when address is empty string."""
        assert is_turkey_location("") is False
    
    def test_returns_false_for_whitespace_address(self):
        """Should return False when address is only whitespace."""
        assert is_turkey_location("   ") is False
    
    def test_returns_true_for_istanbul_without_country(self):
        """Should return True when address contains İstanbul."""
        address = "Cankurtaran Mah., Fatih/İstanbul"
        assert is_turkey_location(address) is True
    
    def test_returns_true_for_ankara_without_country(self):
        """Should return True when address contains Ankara."""
        address = "Kızılay, Çankaya/Ankara"
        assert is_turkey_location(address) is True
    
    def test_returns_true_for_izmir_without_country(self):
        """Should return True when address contains İzmir."""
        address = "Alsancak, Konak/İzmir"
        assert is_turkey_location(address) is True
