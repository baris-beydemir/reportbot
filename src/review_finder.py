"""Logic for finding reviews."""
from typing import List, Set
from src.models import Review


def filter_already_reported_reviews(
    reviews: List[Review], 
    reported_prefixes: Set[str],
    prefix_length: int = 25
) -> List[Review]:
    """Filter out reviews that have already been reported.
    
    Compares the first N characters of each review's text against
    a set of previously reported review prefixes.
    
    Args:
        reviews: List of Review objects to filter.
        reported_prefixes: Set of review text prefixes (lowercase) to exclude.
        prefix_length: Number of characters to use for matching (default: 25).
        
    Returns:
        List of reviews that haven't been reported yet.
    """
    if not reviews:
        return []
    
    if not reported_prefixes:
        return reviews
    
    # Normalize reported prefixes to lowercase for comparison
    normalized_prefixes = {p.lower() for p in reported_prefixes}
    
    filtered = []
    for review in reviews:
        review_text = (review.text or '').strip()
        if not review_text:
            # Keep reviews with empty text (they can't match any prefix)
            filtered.append(review)
            continue
        
        # Get prefix and normalize
        prefix = review_text[:prefix_length].lower()
        
        # Check if this review's prefix matches any reported prefix
        if prefix not in normalized_prefixes:
            filtered.append(review)
    
    return filtered


def find_lowest_rated_review(reviews: List[Review]) -> Review:
    """
    Find the review with the lowest rating from a list of reviews.
    
    Args:
        reviews: List of Review objects to search through.
        
    Returns:
        The Review with the lowest rating. If multiple reviews have
        the same lowest rating, returns the first one found.
        
    Raises:
        ValueError: If the reviews list is empty.
    """
    if not reviews:
        raise ValueError("No reviews provided")
    
    return min(reviews, key=lambda r: r.rating)
 

def find_lowest_rated_reviews(reviews: List[Review], count: int = 1) -> List[Review]:
    """
    Find the n lowest rated reviews from a list of reviews.
    
    Args:
        reviews: List of Review objects to search through.
        count: Number of lowest rated reviews to return.
        
    Returns:
        List of Reviews sorted by rating (lowest first).
        If count exceeds the number of reviews, returns all reviews sorted.
        
    Raises:
        ValueError: If the reviews list is empty.
    """
    if not reviews:
        raise ValueError("No reviews provided")
    
    # Sort by rating and return the first 'count' reviews
    sorted_reviews = sorted(reviews, key=lambda r: r.rating)
    return sorted_reviews[:count]
