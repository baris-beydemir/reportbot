"""Tests for CSV URL reader and writer functionality."""
import pytest
import tempfile
import os
from pathlib import Path
from src.models import Review, Business


class TestReadUrlsWithCountFromCsv:
    """Tests for read_urls_with_count_from_csv function."""
    
    def test_reads_urls_and_counts_with_header(self, tmp_path):
        """Should read URLs and counts from CSV with headers."""
        csv_content = "url;count\nhttps://maps.app.goo.gl/abc123;3\nhttps://maps.app.goo.gl/def456;5"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import read_urls_with_count_from_csv
        data = read_urls_with_count_from_csv(str(csv_file))
        
        assert len(data) == 2
        assert data[0] == ("https://maps.app.goo.gl/abc123", 3)
        assert data[1] == ("https://maps.app.goo.gl/def456", 5)
    
    def test_defaults_count_to_1_if_missing(self, tmp_path):
        """Should default count to 1 if not provided."""
        csv_content = "url\nhttps://maps.app.goo.gl/abc123\nhttps://maps.app.goo.gl/def456"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import read_urls_with_count_from_csv
        data = read_urls_with_count_from_csv(str(csv_file))
        
        assert len(data) == 2
        assert data[0] == ("https://maps.app.goo.gl/abc123", 1)
        assert data[1] == ("https://maps.app.goo.gl/def456", 1)
    
    def test_handles_empty_count(self, tmp_path):
        """Should default to 1 if count is empty."""
        csv_content = "url;count\nhttps://maps.app.goo.gl/abc123;\nhttps://maps.app.goo.gl/def456;2"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import read_urls_with_count_from_csv
        data = read_urls_with_count_from_csv(str(csv_file))
        
        assert data[0] == ("https://maps.app.goo.gl/abc123", 1)
        assert data[1] == ("https://maps.app.goo.gl/def456", 2)
    
    def test_handles_invalid_count(self, tmp_path):
        """Should default to 1 if count is not a valid number."""
        csv_content = "url;count\nhttps://maps.app.goo.gl/abc123;abc\nhttps://maps.app.goo.gl/def456;5"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import read_urls_with_count_from_csv
        data = read_urls_with_count_from_csv(str(csv_file))
        
        assert data[0] == ("https://maps.app.goo.gl/abc123", 1)
        assert data[1] == ("https://maps.app.goo.gl/def456", 5)


class TestReadUrlsFromCsv:
    """Tests for read_urls_from_csv function."""
    
    def test_reads_urls_with_header(self, tmp_path):
        """Should read URLs from CSV with 'url' header."""
        csv_content = "url\nhttps://maps.app.goo.gl/abc123\nhttps://maps.app.goo.gl/def456"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import read_urls_from_csv
        urls = read_urls_from_csv(str(csv_file))
        
        assert len(urls) == 2
        assert urls[0] == "https://maps.app.goo.gl/abc123"
        assert urls[1] == "https://maps.app.goo.gl/def456"
    
    def test_reads_urls_without_header(self, tmp_path):
        """Should read URLs from CSV without header (assumes first column)."""
        csv_content = "https://maps.app.goo.gl/abc123\nhttps://maps.app.goo.gl/def456"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import read_urls_from_csv
        urls = read_urls_from_csv(str(csv_file))
        
        assert len(urls) == 2
        assert urls[0] == "https://maps.app.goo.gl/abc123"
        assert urls[1] == "https://maps.app.goo.gl/def456"
    
    def test_ignores_empty_lines(self, tmp_path):
        """Should ignore empty lines in CSV."""
        csv_content = "url\nhttps://maps.app.goo.gl/abc123\n\nhttps://maps.app.goo.gl/def456\n"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import read_urls_from_csv
        urls = read_urls_from_csv(str(csv_file))
        
        assert len(urls) == 2
    
    def test_handles_csv_with_extra_columns(self, tmp_path):
        """Should handle CSV with extra columns."""
        csv_content = "name;url;note\nBusiness1;https://maps.app.goo.gl/abc123;test\nBusiness2;https://maps.app.goo.gl/def456;test2"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import read_urls_from_csv
        urls = read_urls_from_csv(str(csv_file))
        
        assert len(urls) == 2
        assert urls[0] == "https://maps.app.goo.gl/abc123"
        assert urls[1] == "https://maps.app.goo.gl/def456"
    
    def test_raises_error_for_missing_file(self):
        """Should raise FileNotFoundError for missing file."""
        from src.main import read_urls_from_csv
        
        with pytest.raises(FileNotFoundError):
            read_urls_from_csv("/nonexistent/path/urls.csv")
    
    def test_returns_empty_list_for_empty_file(self, tmp_path):
        """Should return empty list for empty CSV."""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        
        from src.main import read_urls_from_csv
        urls = read_urls_from_csv(str(csv_file))
        
        assert urls == []


class TestUpdateCsvWithReportId:
    """Tests for update_csv_with_report_id function."""
    
    def test_adds_report_id_column_and_value(self, tmp_path):
        """Should add report_id column and update the matching row."""
        csv_content = "url\nhttps://maps.app.goo.gl/abc123\nhttps://maps.app.goo.gl/def456"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import update_csv_with_report_id
        result = update_csv_with_report_id(
            str(csv_file), 
            "https://maps.app.goo.gl/abc123", 
            "9-1234567890"
        )
        
        assert result is True
        
        # Read back and verify
        updated_content = csv_file.read_text()
        assert "report_id" in updated_content
        assert "9-1234567890" in updated_content
    
    def test_updates_correct_row(self, tmp_path):
        """Should update only the row with matching URL."""
        csv_content = "url\nhttps://maps.app.goo.gl/abc123\nhttps://maps.app.goo.gl/def456"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import update_csv_with_report_id
        update_csv_with_report_id(
            str(csv_file), 
            "https://maps.app.goo.gl/def456", 
            "9-9999999999"
        )
        
        # Read back and verify structure
        import csv
        with open(csv_file, 'r') as f:
            reader = csv.reader(f, delimiter=';')
            rows = list(reader)
        
        # Header should have report_id
        assert "report_id" in rows[0]
        
        # First URL row should NOT have report_id
        assert rows[1][1] == "" if len(rows[1]) > 1 else True
        
        # Second URL row should have report_id
        assert "9-9999999999" in rows[2]
    
    def test_handles_csv_with_existing_report_id_column(self, tmp_path):
        """Should update existing report_id column."""
        csv_content = "url;report_id\nhttps://maps.app.goo.gl/abc123;\nhttps://maps.app.goo.gl/def456;"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import update_csv_with_report_id
        result = update_csv_with_report_id(
            str(csv_file), 
            "https://maps.app.goo.gl/abc123", 
            "9-1111111111"
        )
        
        assert result is True
        
        import csv
        with open(csv_file, 'r') as f:
            reader = csv.reader(f, delimiter=';')
            rows = list(reader)
        
        # Should have report_id value
        assert "9-1111111111" in rows[1]
    
    def test_returns_false_for_missing_file(self):
        """Should return False for missing file."""
        from src.main import update_csv_with_report_id
        result = update_csv_with_report_id(
            "/nonexistent/path/urls.csv",
            "https://maps.app.goo.gl/abc123",
            "9-1234567890"
        )
        
        assert result is False
    
    def test_returns_false_for_non_matching_url(self, tmp_path):
        """Should return False if URL not found in CSV."""
        csv_content = "url\nhttps://maps.app.goo.gl/abc123"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import update_csv_with_report_id
        result = update_csv_with_report_id(
            str(csv_file),
            "https://maps.app.goo.gl/xyz999",  # Not in CSV
            "9-1234567890"
        )
        
        assert result is False
    
    def test_writes_reviews_with_all_details(self, tmp_path):
        """Should write each review with all details: link, author, text, rating, status."""
        csv_content = "url;count\nhttps://maps.app.goo.gl/abc123;3"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import update_csv_with_report_id
        
        business = Business(
            name="Test Restaurant",
            maps_url="https://maps.app.goo.gl/abc123"
        )
        
        reviews = [
            Review(
                author_name="John Doe",
                rating=1,
                text="Terrible food!",
                review_url="https://maps.app.goo.gl/review1"
            ),
            Review(
                author_name="Jane Smith",
                rating=2,
                text="Bad service, won't come again",
                review_url="https://maps.app.goo.gl/review2"
            ),
            Review(
                author_name="Bob Wilson",
                rating=1,
                text="Worst experience ever",
                review_url="https://maps.app.goo.gl/review3"
            )
        ]
        
        result = update_csv_with_report_id(
            str(csv_file),
            "https://maps.app.goo.gl/abc123",
            "5-8818000039869",
            reviews=reviews,
            business=business
        )
        
        assert result is True
        
        import csv
        with open(csv_file, 'r') as f:
            reader = csv.reader(f, delimiter=';')
            rows = list(reader)
        
        # Header row should have all columns
        assert 'url' in rows[0]
        assert 'count' in rows[0]
        assert 'business_name' in rows[0]
        assert 'report_id' in rows[0]
        assert 'review_url' in rows[0]
        assert 'reviewer_name' in rows[0]
        assert 'review_text' in rows[0]
        assert 'rating' in rows[0]
        assert 'status' in rows[0]
        
        # First review row has url, count, business_name, report_id
        assert rows[1][0] == "https://maps.app.goo.gl/abc123"
        assert rows[1][1] == "3"
        assert rows[1][2] == "Test Restaurant"
        assert rows[1][3] == "5-8818000039869"
        assert rows[1][4] == "https://maps.app.goo.gl/review1"
        assert rows[1][5] == "John Doe"
        assert rows[1][6] == "Terrible food!"
        assert rows[1][7] == "1"
        assert rows[1][8] == "beklemede"
        
        # Subsequent rows have empty url/count/report_id but business_name is filled
        assert rows[2][0] == ""
        assert rows[2][1] == ""
        assert rows[2][2] == "Test Restaurant"
        assert rows[2][3] == ""
        assert rows[2][4] == "https://maps.app.goo.gl/review2"
        assert rows[2][5] == "Jane Smith"
        assert rows[2][6] == "Bad service, won't come again"
        assert rows[2][7] == "2"
        assert rows[2][8] == "beklemede"
        
        assert rows[3][4] == "https://maps.app.goo.gl/review3"
        assert rows[3][5] == "Bob Wilson"
        assert rows[3][8] == "beklemede"
    
    def test_handles_single_review_with_details(self, tmp_path):
        """Should handle single review with all details."""
        csv_content = "url;count\nhttps://maps.app.goo.gl/abc123;1"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import update_csv_with_report_id
        
        business = Business(name="Cafe Test")
        reviews = [
            Review(
                author_name="Test User",
                rating=1,
                text="Bad coffee",
                review_url="https://maps.app.goo.gl/review1"
            )
        ]
        
        result = update_csv_with_report_id(
            str(csv_file),
            "https://maps.app.goo.gl/abc123",
            "5-1234567890",
            reviews=reviews,
            business=business
        )
        
        assert result is True
        
        import csv
        with open(csv_file, 'r') as f:
            reader = csv.reader(f, delimiter=';')
            rows = list(reader)
        
        # Should have header + 1 data row
        assert len(rows) == 2
        assert rows[1][2] == "Cafe Test"  # business_name is now at index 2
        assert rows[1][5] == "Test User"
        assert rows[1][8] == "beklemede"
    
    def test_preserves_other_urls_in_csv(self, tmp_path):
        """Should preserve other URLs when adding reviews."""
        csv_content = "url;count\nhttps://maps.app.goo.gl/abc123;2\nhttps://maps.app.goo.gl/def456;3"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import update_csv_with_report_id
        
        business = Business(name="Restaurant A")
        reviews = [
            Review(author_name="User1", rating=1, text="Bad", review_url="https://maps.app.goo.gl/review1"),
            Review(author_name="User2", rating=2, text="Worse", review_url="https://maps.app.goo.gl/review2")
        ]
        
        result = update_csv_with_report_id(
            str(csv_file),
            "https://maps.app.goo.gl/abc123",
            "5-1111111111",
            reviews=reviews,
            business=business
        )
        
        assert result is True
        
        import csv
        with open(csv_file, 'r') as f:
            reader = csv.reader(f, delimiter=';')
            rows = list(reader)
        
        # Header + 2 rows for first URL + 1 row for second URL
        assert len(rows) == 4
        
        # First URL's rows
        assert rows[1][0] == "https://maps.app.goo.gl/abc123"
        assert rows[2][0] == ""  # Continuation row
        
        # Second URL should still be there
        assert rows[3][0] == "https://maps.app.goo.gl/def456"
        assert rows[3][1] == "3"  # count is at index 1
    
    def test_no_brackets_in_review_urls(self, tmp_path):
        """Should NOT add [] brackets to review URLs."""
        csv_content = "url;count\nhttps://maps.app.goo.gl/abc123;1"
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import update_csv_with_report_id
        
        business = Business(name="Test Place")
        reviews = [
            Review(author_name="User", rating=1, text="Bad", review_url="https://maps.app.goo.gl/review1")
        ]
        
        update_csv_with_report_id(
            str(csv_file),
            "https://maps.app.goo.gl/abc123",
            "5-123",
            reviews=reviews,
            business=business
        )
        
        content = csv_file.read_text()
        assert "[]" not in content
        assert "https://maps.app.goo.gl/review1" in content


class TestReadUrlsWithCountSkipsProcessedRows:
    """Tests that read_urls_with_count_from_csv skips processed rows in new format."""
    
    def test_skips_continuation_rows_with_empty_url(self, tmp_path):
        """Should skip rows that are continuation rows (empty URL with review)."""
        csv_content = """url;count;business_name;report_id;review_url;reviewer_name;review_text;rating;status
https://maps.app.goo.gl/abc123;3;Test Biz;5-8818000039869;https://maps.app.goo.gl/review1;John;Bad;1;beklemede
;;;;https://maps.app.goo.gl/review2;Jane;Worse;2;beklemede
;;;;https://maps.app.goo.gl/review3;Bob;Awful;1;beklemede
https://maps.app.goo.gl/def456;2;;;;;"""
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import read_urls_with_count_from_csv
        data = read_urls_with_count_from_csv(str(csv_file))
        
        # Should only return the second URL (first is processed)
        assert len(data) == 1
        assert data[0] == ("https://maps.app.goo.gl/def456", 2)
    
    def test_returns_all_unprocessed_urls(self, tmp_path):
        """Should return all URLs that don't have report_id."""
        csv_content = """url;count;business_name;report_id;review_url;reviewer_name;review_text;rating;status
https://maps.app.goo.gl/abc123;3;;;;;;
https://maps.app.goo.gl/def456;2;;;;;;"""
        csv_file = tmp_path / "urls.csv"
        csv_file.write_text(csv_content)
        
        from src.main import read_urls_with_count_from_csv
        data = read_urls_with_count_from_csv(str(csv_file))
        
        assert len(data) == 2
        assert data[0] == ("https://maps.app.goo.gl/abc123", 3)
        assert data[1] == ("https://maps.app.goo.gl/def456", 2)
