"""Tests for review finder logic."""
import pytest
from src.models import Review
from src.review_finder import (
    find_lowest_rated_review,
    find_lowest_rated_reviews,
    filter_already_reported_reviews,
)


class TestFindLowestRatedReviews:
    """Tests for finding multiple lowest rated reviews."""
    
    def test_find_n_lowest_reviews(self):
        """Should find n lowest rated reviews sorted by rating."""
        reviews = [
            Review(author_name="User1", rating=5, text="Great!"),
            Review(author_name="User2", rating=2, text="Not good"),
            Review(author_name="User3", rating=4, text="Pretty good"),
            Review(author_name="User4", rating=1, text="Terrible!"),
            Review(author_name="User5", rating=3, text="Average"),
        ]
        
        lowest_3 = find_lowest_rated_reviews(reviews, count=3)
        
        assert len(lowest_3) == 3
        assert lowest_3[0].rating == 1  # User4
        assert lowest_3[1].rating == 2  # User2
        assert lowest_3[2].rating == 3  # User5
    
    def test_returns_all_if_count_exceeds_reviews(self):
        """Should return all reviews if count > len(reviews)."""
        reviews = [
            Review(author_name="User1", rating=5, text="Great!"),
            Review(author_name="User2", rating=2, text="Not good"),
        ]
        
        result = find_lowest_rated_reviews(reviews, count=10)
        
        assert len(result) == 2
        assert result[0].rating == 2
        assert result[1].rating == 5
    
    def test_count_of_1_returns_single_review(self):
        """Should return single review when count=1."""
        reviews = [
            Review(author_name="User1", rating=5, text="Great!"),
            Review(author_name="User2", rating=1, text="Bad"),
        ]
        
        result = find_lowest_rated_reviews(reviews, count=1)
        
        assert len(result) == 1
        assert result[0].rating == 1
    
    def test_empty_reviews_raises_error(self):
        """Should raise error when no reviews provided."""
        with pytest.raises(ValueError, match="No reviews provided"):
            find_lowest_rated_reviews([], count=3)
    
    def test_preserves_original_indices(self):
        """Should return reviews with their original indices."""
        reviews = [
            Review(author_name="User1", rating=5, text="Great!"),
            Review(author_name="User2", rating=1, text="Bad"),
            Review(author_name="User3", rating=3, text="Ok"),
        ]
        
        result = find_lowest_rated_reviews(reviews, count=2)
        
        # Check that we can find original indices
        assert reviews.index(result[0]) == 1  # User2 was at index 1
        assert reviews.index(result[1]) == 2  # User3 was at index 2


class TestFindLowestRatedReview:
    """Tests for finding the lowest rated review."""
    
    def test_find_lowest_from_multiple_reviews(self):
        """Should find the review with lowest rating."""
        reviews = [
            Review(author_name="User1", rating=5, text="Great!"),
            Review(author_name="User2", rating=2, text="Not good"),
            Review(author_name="User3", rating=4, text="Pretty good"),
            Review(author_name="User4", rating=1, text="Terrible!"),
            Review(author_name="User5", rating=3, text="Average"),
        ]
        
        lowest = find_lowest_rated_review(reviews)
        
        assert lowest.rating == 1
        assert lowest.author_name == "User4"
        assert lowest.text == "Terrible!"
    
    def test_find_lowest_with_same_ratings(self):
        """Should return first review when multiple have same lowest rating."""
        reviews = [
            Review(author_name="User1", rating=2, text="Bad"),
            Review(author_name="User2", rating=2, text="Also bad"),
            Review(author_name="User3", rating=5, text="Great!"),
        ]
        
        lowest = find_lowest_rated_review(reviews)
        
        assert lowest.rating == 2
        assert lowest.author_name == "User1"  # First one with lowest rating
    
    def test_find_lowest_single_review(self):
        """Should return the only review when there's just one."""
        reviews = [
            Review(author_name="User1", rating=3, text="Ok"),
        ]
        
        lowest = find_lowest_rated_review(reviews)
        
        assert lowest.rating == 3
        assert lowest.author_name == "User1"
    
    def test_empty_reviews_raises_error(self):
        """Should raise error when no reviews provided."""
        with pytest.raises(ValueError, match="No reviews provided"):
            find_lowest_rated_review([])
    
    def test_all_five_star_reviews(self):
        """Should return first review when all are 5 stars."""
        reviews = [
            Review(author_name="User1", rating=5, text="Amazing!"),
            Review(author_name="User2", rating=5, text="Perfect!"),
        ]
        
        lowest = find_lowest_rated_review(reviews)
        
        assert lowest.rating == 5


class TestFilterAlreadyReportedReviews:
    """Tests for filtering already reported reviews."""
    
    def test_filters_matching_reviews_by_text_prefix(self):
        """Should filter reviews that match by first 25 chars of text."""
        reviews = [
            Review(author_name="User1", rating=1, text="This is a bad review that should be filtered out"),
            Review(author_name="User2", rating=2, text="Another review that is okay"),
            Review(author_name="User3", rating=1, text="New review not reported yet"),
        ]
        
        # Already reported reviews (first 25 chars, must be exact)
        reported_prefixes = {
            "this is a bad review that",  # Matches User1 (first 25 chars, lowercase)
        }
        
        filtered = filter_already_reported_reviews(reviews, reported_prefixes)
        
        assert len(filtered) == 2
        assert filtered[0].author_name == "User2"
        assert filtered[1].author_name == "User3"
    
    def test_returns_all_when_no_matches(self):
        """Should return all reviews when none match reported prefixes."""
        reviews = [
            Review(author_name="User1", rating=1, text="First review text here"),
            Review(author_name="User2", rating=2, text="Second review text here"),
        ]
        
        reported_prefixes = {"Some other review text"}
        
        filtered = filter_already_reported_reviews(reviews, reported_prefixes)
        
        assert len(filtered) == 2
    
    def test_returns_all_when_reported_set_empty(self):
        """Should return all reviews when reported set is empty."""
        reviews = [
            Review(author_name="User1", rating=1, text="Review one"),
            Review(author_name="User2", rating=2, text="Review two"),
        ]
        
        filtered = filter_already_reported_reviews(reviews, set())
        
        assert len(filtered) == 2
    
    def test_filters_all_when_all_reported(self):
        """Should return empty list when all reviews are already reported."""
        reviews = [
            Review(author_name="User1", rating=1, text="First bad review"),
            Review(author_name="User2", rating=2, text="Second bad review"),
        ]
        
        reported_prefixes = {
            "First bad review",
            "Second bad review",
        }
        
        filtered = filter_already_reported_reviews(reviews, reported_prefixes)
        
        assert len(filtered) == 0
    
    def test_handles_short_review_text(self):
        """Should handle reviews with text shorter than 25 chars."""
        reviews = [
            Review(author_name="User1", rating=1, text="Short"),
            Review(author_name="User2", rating=2, text="Another short text"),
        ]
        
        reported_prefixes = {"Short"}  # Exact match for short text
        
        filtered = filter_already_reported_reviews(reviews, reported_prefixes)
        
        assert len(filtered) == 1
        assert filtered[0].author_name == "User2"
    
    def test_handles_empty_reviews_list(self):
        """Should return empty list when reviews list is empty."""
        filtered = filter_already_reported_reviews([], {"some prefix"})
        assert len(filtered) == 0
    
    def test_preserves_order(self):
        """Should preserve original order of non-filtered reviews."""
        reviews = [
            Review(author_name="User1", rating=1, text="Keep this one first"),
            Review(author_name="User2", rating=2, text="Filter this out completely"),
            Review(author_name="User3", rating=3, text="Keep this one second"),
            Review(author_name="User4", rating=4, text="Keep this one third"),
        ]
        
        # First 25 chars of "Filter this out completely" is "Filter this out completel"
        reported_prefixes = {"filter this out completel"}  # lowercase, 25 chars
        
        filtered = filter_already_reported_reviews(reviews, reported_prefixes)
        
        assert len(filtered) == 3
        assert filtered[0].author_name == "User1"
        assert filtered[1].author_name == "User3"
        assert filtered[2].author_name == "User4"
    
    def test_case_insensitive_matching(self):
        """Should match reviews case-insensitively."""
        reviews = [
            Review(author_name="User1", rating=1, text="THIS IS ALL CAPS REVIEW"),
            Review(author_name="User2", rating=2, text="this is lowercase review"),
        ]
        
        # Lowercase prefix should match uppercase text
        reported_prefixes = {"this is all caps review"}
        
        filtered = filter_already_reported_reviews(reviews, reported_prefixes)
        
        assert len(filtered) == 1
        assert filtered[0].author_name == "User2"
    
    def test_handles_none_text(self):
        """Should handle reviews with None or empty text."""
        reviews = [
            Review(author_name="User1", rating=1, text=""),
            Review(author_name="User2", rating=2, text="Valid review text here"),
        ]
        
        reported_prefixes = set()
        
        filtered = filter_already_reported_reviews(reviews, reported_prefixes)
        
        assert len(filtered) == 2
