"""Tests for data models."""
import pytest
from src.models import Review, Business


class TestReview:
    """Tests for Review model."""
    
    def test_create_valid_review(self):
        """Should create a review with valid data."""
        review = Review(
            author_name="Test User",
            rating=3,
            text="This is a test review"
        )
        assert review.author_name == "Test User"
        assert review.rating == 3
        assert review.text == "This is a test review"
    
    def test_create_review_with_all_fields(self):
        """Should create a review with all optional fields."""
        review = Review(
            author_name="Test User",
            rating=1,
            text="Bad experience",
            review_url="https://maps.google.com/review/123",
            date="2 weeks ago"
        )
        assert review.review_url == "https://maps.google.com/review/123"
        assert review.date == "2 weeks ago"
    
    def test_invalid_rating_too_low(self):
        """Should raise error for rating below 1."""
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            Review(author_name="Test", rating=0, text="Test")
    
    def test_invalid_rating_too_high(self):
        """Should raise error for rating above 5."""
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            Review(author_name="Test", rating=6, text="Test")


class TestBusiness:
    """Tests for Business model."""
    
    def test_create_business_minimal(self):
        """Should create a business with just name."""
        business = Business(name="Test Restaurant")
        assert business.name == "Test Restaurant"
        assert business.place_id is None
    
    def test_create_business_full(self):
        """Should create a business with all fields."""
        business = Business(
            name="Test Restaurant",
            place_id="ChIJ123",
            address="123 Test St",
            maps_url="https://maps.google.com/place/123"
        )
        assert business.place_id == "ChIJ123"
        assert business.address == "123 Test St"
