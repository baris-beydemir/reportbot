"""Tests for ReportFiller logic."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.report_filler import ReportFiller
from src.models import Business, Review


class TestReportFillerSelections:
    """Tests for the new selections in ReportFiller."""
    
    @pytest.mark.asyncio
    async def test_select_acting_on_behalf_someone_else(self):
        """Should attempt to click 'Someone else' or 'Başka biri'."""
        filler = ReportFiller(headless=True)
        mock_page = AsyncMock()
        
        # Mock radio button
        mock_radio = AsyncMock()
        mock_radio.is_visible = AsyncMock(return_value=True)
        mock_radio.click = AsyncMock()
        
        # Mock locator to return our radio button
        mock_locator = MagicMock()
        mock_locator.first = mock_radio
        mock_page.locator = MagicMock(return_value=mock_locator)
        
        filler._page = mock_page
        
        result = await filler.select_acting_on_behalf(myself=False)
        
        assert result is True
        mock_radio.click.assert_called_once()
        # Verify it tried the correct selectors (at least one of them)
        args = mock_page.locator.call_args_list
        selectors = [arg[0][0] for arg in args]
        assert any("someone_else" in s or "Başka biri" in s or "Someone else" in s for s in selectors)

    @pytest.mark.asyncio
    async def test_select_legal_relationship(self):
        """Should attempt to click the specified legal relationship."""
        filler = ReportFiller(headless=True)
        mock_page = AsyncMock()
        
        mock_radio = AsyncMock()
        mock_radio.is_visible = AsyncMock(return_value=True)
        mock_radio.click = AsyncMock()
        
        mock_locator = MagicMock()
        mock_locator.first = mock_radio
        mock_page.locator = MagicMock(return_value=mock_locator)
        
        filler._page = mock_page
        
        relationship = "Müşteri (ör. avukat veya başka bir yetkili temsilciyim)"
        result = await filler.select_legal_relationship(relationship)
        
        assert result is True
        mock_radio.click.assert_called_once()
        
        # Verify it tried selectors with the relationship text
        args = mock_page.locator.call_args_list
        selectors = [arg[0][0] for arg in args]
        assert any(relationship in s for s in selectors)

    @pytest.mark.asyncio
    async def test_fill_customer_name(self):
        """Should fill the customer name field with business name."""
        filler = ReportFiller(headless=True)
        mock_page = AsyncMock()
        
        mock_field = AsyncMock()
        mock_field.is_visible = AsyncMock(return_value=True)
        mock_field.fill = AsyncMock()
        mock_field.get_attribute = AsyncMock(side_effect=lambda attr: "Müşterinizin adı" if attr == "placeholder" else "")
        
        mock_locator = MagicMock()
        mock_locator.count = AsyncMock(return_value=1)
        mock_locator.nth = MagicMock(return_value=mock_field)
        mock_page.locator = MagicMock(return_value=mock_locator)
        
        filler._page = mock_page
        
        business_name = "Test Business"
        result = await filler.fill_customer_name(business_name)
        
        assert result is True
        mock_field.fill.assert_called_with(business_name)

    @pytest.mark.asyncio
    async def test_fill_form_uses_new_logic(self):
        """Should call the new selection methods during fill_form."""
        filler = ReportFiller(headless=True)
        
        # Mock all the methods we'll call
        filler.navigate_to_form = AsyncMock()
        filler.fill_country_dropdown = AsyncMock()
        filler.fill_legal_name = AsyncMock()
        filler.select_acting_on_behalf = AsyncMock()
        filler.select_legal_relationship = AsyncMock()
        filler.fill_customer_name = AsyncMock()
        filler.fill_multiple_urls = AsyncMock()
        filler.check_confirmation_checkbox = AsyncMock()
        filler.fill_signature = AsyncMock()
        # Mock random reasons to avoid file dependency in this test
        filler._get_random_reasons = MagicMock(return_value=["Random Test Reason"])
        
        mock_page = AsyncMock()
        filler._page = mock_page
        
        business = Business(name="Test Business")
        review = Review(author_name="Tester", rating=1, text="Bad")
        
        await filler.fill_form(business, [review])
        
        # Verify new logic calls
        filler.select_acting_on_behalf.assert_called_with(myself=False)
        filler.select_legal_relationship.assert_called_with("Müşteri (ör. avukat veya başka bir yetkili temsilciyim)")
        filler.fill_customer_name.assert_called_with(business.name)
        
    @pytest.mark.asyncio
    async def test_get_random_reasons_from_csv(self, tmp_path):
        """Should read random unique reasons from the CSV file."""
        # Create a temporary reasons.csv
        reasons_dir = tmp_path / "src"
        reasons_dir.mkdir()
        reasons_file = reasons_dir / "reasons.csv"
        reasons_file.write_text("reason\nReason 1\nReason 2\nReason 3", encoding="utf-8")
        
        filler = ReportFiller(headless=True)
        # Override the REASONS_FILE path for the test
        with patch.object(ReportFiller, 'REASONS_FILE', str(reasons_file)):
            reasons = filler._get_random_reasons(2)
            assert len(reasons) == 2
            assert reasons[0] in ["Reason 1", "Reason 2", "Reason 3"]
            assert reasons[1] in ["Reason 1", "Reason 2", "Reason 3"]
            assert reasons[0] != reasons[1] # Should be unique
