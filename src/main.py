"""Main entry point for ReportBot."""
import asyncio
import argparse
import csv
import os
import sys
from pathlib import Path

from src.maps_scraper import MapsScraper
from src.report_filler import ReportFiller
from src.review_finder import (
    find_lowest_rated_review,
    find_lowest_rated_reviews,
    filter_already_reported_reviews,
)
from src.models import Business, Review
from src.excel_handler import (
    read_excel_urls_with_count,
    update_excel_with_report,
    convert_csv_to_excel,
    get_reported_reviews_for_business,
)


def update_csv_with_report_id(
    csv_path: str, 
    url: str, 
    report_id: str, 
    reviews: list[Review] = None,
    business: Business = None
) -> bool:
    """Update the CSV file with the report ID and review details for a given URL.
    
    Updates the row with the matching URL, adding columns for business name,
    review details (url, author, text, rating), and status.
    Each review is written on a separate row, with url/business_name/count/report_id 
    only on the first row (grouped format).
    
    Args:
        csv_path: Path to the CSV file.
        url: The URL to find in the CSV.
        report_id: The report ID to save.
        reviews: List of Review objects that were reported.
        business: Business object for the place.
        
    Returns:
        True if update was successful, False otherwise.
    """
    if not os.path.exists(csv_path):
        return False
    
    try:
        # Read the CSV
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter=';')
            rows = list(reader)
        
        if not rows:
            return False
        
        # Check if first row is header
        first_line_lower = rows[0][0].lower() if rows[0] else ""
        has_header = 'url' in first_line_lower or any('url' in col.lower() for col in rows[0])
        
        # Define expected column structure in order
        EXPECTED_COLUMNS = ['url', 'count', 'business_name', 'report_id', 'review_url', 'reviewer_name', 'review_text', 'rating', 'status']
        
        if has_header:
            old_header = [col.lower().strip() for col in rows[0]]
            
            # Build new header with proper order
            new_header = EXPECTED_COLUMNS.copy()
            col_indices = {col: i for i, col in enumerate(new_header)}
            
            # Map old column indices to new ones
            old_to_new = {}
            for old_idx, old_col in enumerate(old_header):
                if old_col in col_indices:
                    old_to_new[old_idx] = col_indices[old_col]
            
            # Reconstruct all rows with new column structure
            new_rows = [new_header]
            for row_idx, row in enumerate(rows[1:], 1):
                new_row = [''] * len(EXPECTED_COLUMNS)
                for old_idx, val in enumerate(row):
                    if old_idx in old_to_new:
                        new_row[old_to_new[old_idx]] = val
                new_rows.append(new_row)
            rows = new_rows
        else:
            # No header - create one and restructure
            col_indices = {col: i for i, col in enumerate(EXPECTED_COLUMNS)}
            new_rows = [EXPECTED_COLUMNS]
            for row in rows:
                new_row = [''] * len(EXPECTED_COLUMNS)
                if row:
                    new_row[0] = row[0]  # URL in first column
                new_rows.append(new_row)
            rows = new_rows
        
        col_indices = {col: i for i, col in enumerate(EXPECTED_COLUMNS)}
        
        # Find and update the row with matching URL
        updated = False
        url_row_index = -1
        url_col_idx = col_indices['url']
        
        for i, row in enumerate(rows):
            if i == 0:
                continue  # Skip header
            
            if len(row) > url_col_idx and row[url_col_idx].strip() == url:
                url_row_index = i
                
                # Update row with report data
                row[col_indices['report_id']] = report_id
                
                # Add business name
                if business:
                    row[col_indices['business_name']] = business.name or ''
                
                # Add first review details to this row
                if reviews and len(reviews) > 0:
                    first_review = reviews[0]
                    row[col_indices['review_url']] = first_review.review_url or ''
                    row[col_indices['reviewer_name']] = first_review.author_name or ''
                    row[col_indices['review_text']] = first_review.text or ''
                    row[col_indices['rating']] = str(first_review.rating)
                    row[col_indices['status']] = 'beklemede'
                
                updated = True
                break
        
        if updated and reviews and len(reviews) > 1:
            # Insert additional rows for remaining reviews
            additional_rows = []
            
            for review in reviews[1:]:
                # Create a row with empty values except for review details
                new_row = [''] * len(EXPECTED_COLUMNS)
                new_row[col_indices['review_url']] = review.review_url or ''
                new_row[col_indices['reviewer_name']] = review.author_name or ''
                new_row[col_indices['review_text']] = review.text or ''
                new_row[col_indices['rating']] = str(review.rating)
                new_row[col_indices['status']] = 'beklemede'
                additional_rows.append(new_row)
            
            # Insert the additional rows right after the URL row
            for j, new_row in enumerate(additional_rows):
                rows.insert(url_row_index + 1 + j, new_row)
        
        if updated:
            # Write back to CSV
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerows(rows)
            print(f"✅ CSV güncellendi: {url[:50]}... -> {report_id}")
            if reviews:
                print(f"   Raporlanan yorumlar ({len(reviews)}) kaydedildi.")
            return True
        
        return False
        
    except Exception as e:
        print(f"⚠️ CSV güncellenirken hata: {e}")
        return False


def read_urls_with_count_from_csv(csv_path: str) -> list[tuple[str, int]]:
    """Read URLs and review counts from a CSV file.
    
    The CSV should have 'url' and optionally 'count' columns.
    If count is not provided, defaults to 1.
    Only returns rows where 'report_id' and 'reported_reviews' are empty.
    
    Args:
        csv_path: Path to the CSV file.
        
    Returns:
        List of (url, count) tuples.
        
    Raises:
        FileNotFoundError: If the CSV file doesn't exist.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    data = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if not content:
            return []
        
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Try to detect if first row is a header
        first_line = f.readline().strip()
        f.seek(0)
        
        # Check if 'url' is in the first line (header detection)
        first_line_lower = first_line.lower()
        has_header = 'url' in first_line_lower
        
        reader = csv.reader(f, delimiter=';')
        rows = list(reader)
        
        if not rows:
            return []
        
        # Find column indices
        url_col_index = 0
        count_col_index = -1
        report_id_col_index = -1
        reviews_col_index = -1
        
        if has_header:
            header = [col.lower().strip() for col in rows[0]]
            if 'url' in header:
                url_col_index = header.index('url')
            if 'count' in header:
                count_col_index = header.index('count')
            if 'report_id' in header:
                report_id_col_index = header.index('report_id')
            if 'reported_reviews' in header:
                reviews_col_index = header.index('reported_reviews')
            rows = rows[1:]  # Skip header
        
        for row in rows:
            if row and len(row) > url_col_index:
                url = row[url_col_index].strip()
                if not url:
                    continue

                # Check if already processed
                is_processed = False
                if report_id_col_index >= 0 and len(row) > report_id_col_index:
                    if row[report_id_col_index].strip():
                        is_processed = True
                
                if reviews_col_index >= 0 and len(row) > reviews_col_index:
                    if row[reviews_col_index].strip():
                        is_processed = True
                
                if is_processed:
                    continue

                # Get count, default to 1
                count = 1
                if count_col_index >= 0 and len(row) > count_col_index:
                    count_str = row[count_col_index].strip()
                    if count_str:
                        try:
                            count = int(count_str)
                        except ValueError:
                            count = 1
                data.append((url, count))
    
    return data


def read_urls_from_csv(csv_path: str) -> list[str]:
    """Read URLs from a CSV file.
    
    The CSV should have a 'url' column header. If no header is found,
    assumes the first column contains URLs.
    
    Args:
        csv_path: Path to the CSV file.
        
    Returns:
        List of URLs from the CSV file.
        
    Raises:
        FileNotFoundError: If the CSV file doesn't exist.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    urls = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
        if not content:
            return []
        
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Try to detect if first row is a header
        first_line = f.readline().strip()
        f.seek(0)
        
        # Check if 'url' is in the first line (header detection)
        first_line_lower = first_line.lower()
        has_header = 'url' in first_line_lower
        
        reader = csv.reader(f, delimiter=';')
        rows = list(reader)
        
        if not rows:
            return []
        
        # Find URL column index
        url_col_index = 0
        if has_header:
            header = [col.lower().strip() for col in rows[0]]
            if 'url' in header:
                url_col_index = header.index('url')
            rows = rows[1:]  # Skip header
        
        for row in rows:
            if row and len(row) > url_col_index:
                url = row[url_col_index].strip()
                if url:  # Ignore empty values
                    urls.append(url)
    
    return urls


async def run_bot(
    business_name: str = None,
    maps_url: str = None,
    report_reason: str = "Spam or fake content",
    additional_info: str = "",
    headless: bool = False,
    max_reviews: int = 50,
    google_email: str = None,
    google_password: str = None,
    country: str = "Türkiye",
    legal_name: str = "Doğukan Öztürk",
    review_count: int = 1,
    excel_path: str = None
) -> tuple[bool, str | None, list[Review], Business | None]:
    """
    Run the full automation flow.
    
    Args:
        business_name: Name of the business to search on Google Maps (optional if maps_url provided).
        maps_url: Direct Google Maps URL to navigate to (optional if business_name provided).
        report_reason: Reason for reporting the review.
        additional_info: Additional context for the report.
        headless: Whether to run browsers in headless mode.
        max_reviews: Maximum number of reviews to fetch.
        review_count: Number of lowest-rated reviews to report (default: 1).
        excel_path: Path to Excel file for checking previously reported reviews.
                   If provided, reviews that were already reported for the same
                   business (matched by first 25 chars of text) will be skipped.
        
    Returns:
        Tuple of (success, report_id, reviews_with_links, business). report_id is None if form was not submitted.
    """
    print(f"\n{'='*60}")
    print(f"ReportBot - Google Maps Review Reporter")
    print(f"{'='*60}\n")
    
    # Determine navigation method
    use_direct_url = maps_url is not None
    
    if use_direct_url:
        print(f"[1/5] Navigating directly to Maps URL: {maps_url}")
    else:
        if not business_name:
            print("❌ Either business_name or maps_url must be provided")
            return (False, None, [], None)
        print(f"[1/5] Searching for business: {business_name}")
    
    async with MapsScraper(headless=headless) as scraper:
        if use_direct_url:
            # Navigate directly to the Maps URL (dual-tab approach)
            business = await scraper.navigate_to_maps_url(maps_url)
        else:
            # Search for business by name
            business = await scraper.search_business(business_name)
        
        if not business:
            print(f"❌ Business not found")
            return (False, None, [], None)
        
        print(f"✓ Found business: {business.name}")
        if business.address:
            print(f"  Address: {business.address}")
        print(f"  URL: {business.maps_url}")
        
        # Step 2: Get reviews (WITHOUT share links - much faster!)
        print(f"\n[2/5] Fetching reviews (max {max_reviews})...")
        reviews = await scraper.get_reviews(
            business, 
            max_reviews=max_reviews, 
            get_share_links=False,
            from_direct_url=use_direct_url
        )
        
        if not reviews:
            print("❌ No reviews found for this business")
            return (False, None, [], business)
        
        print(f"✓ Found {len(reviews)} reviews")
        
        # Filter out previously reported reviews if excel_path is provided
        filtered_reviews = reviews
        if excel_path and business:
            print(f"\n  Checking for previously reported reviews for '{business.name}'...")
            reported_prefixes = get_reported_reviews_for_business(excel_path, business.name)
            
            if reported_prefixes:
                print(f"  Found {len(reported_prefixes)} previously reported review(s)")
                filtered_reviews = filter_already_reported_reviews(reviews, reported_prefixes)
                skipped_count = len(reviews) - len(filtered_reviews)
                print(f"  Skipping {skipped_count} already reported review(s)")
                print(f"  Remaining reviews to process: {len(filtered_reviews)}")
                
                if not filtered_reviews:
                    print("❌ All reviews have been previously reported for this business")
                    return (False, None, [], business)
            else:
                print(f"  No previously reported reviews found for this business")
        
        # Step 3: Find lowest rated reviews (multiple if review_count > 1)
        actual_count = min(review_count, len(filtered_reviews))
        print(f"\n[3/5] Finding {actual_count} lowest rated review(s)...")
        lowest_reviews = find_lowest_rated_reviews(filtered_reviews, count=actual_count)
        
        for i, rev in enumerate(lowest_reviews, 1):
            # Use filtered_reviews for finding index since that's what we're processing
            original_index = reviews.index(rev)  # Keep original index for scraper
            print(f"  [{i}] Index {original_index}: {rev.author_name} - {'⭐' * rev.rating} ({rev.rating}/5)")
            print(f"      {rev.text[:100]}{'...' if len(rev.text) > 100 else ''}")
        
        # Step 4: Get share links for all lowest rated reviews
        print(f"\n[4/5] Getting share links for {len(lowest_reviews)} review(s)...")
        reviews_with_links = []
        
        for i, rev in enumerate(lowest_reviews):
            original_index = reviews.index(rev)
            print(f"  Getting share link for review {i+1}/{len(lowest_reviews)} (index: {original_index})...")
            share_url = await scraper.get_share_link_for_review_at_index(original_index)
            
            # DEBUG: İlk yorumdan sonra pause - elementi incelemek için
            if i == 0:
                print("\n  🔍 DEBUG: İlk yorum share linki alındı. Sayfa duraklatıldı...")
                print("     Playwright Inspector'da elementi inceleyin.")
                print("     Devam etmek için Inspector'da 'Resume' tıklayın.\n")
                #await scraper._page.pause()
            
            # Update the review object with the share link
            updated_review = Review(
                author_name=rev.author_name,
                rating=rev.rating,
                text=rev.text,
                date=rev.date,
                review_url=share_url
            )
            reviews_with_links.append(updated_review)
            
            if share_url:
                print(f"    ✅ {share_url[:50]}...")
            else:
                print(f"    ⚠️ Share link alınamadı")
        
        # Detailed URL logging
        print("\n" + "="*60)
        print(f"📋 TOPLAM {len(reviews_with_links)} YORUM İÇİN URL'LER:")
        for i, rev in enumerate(reviews_with_links, 1):
            if rev.review_url and rev.review_url.startswith("https://maps.app.goo.gl/"):
                print(f"  [{i}] ✅ {rev.author_name}: {rev.review_url}")
            elif rev.review_url:
                print(f"  [{i}] ⚠️ {rev.author_name}: {rev.review_url} (kısa link değil)")
            else:
                print(f"  [{i}] ❌ {rev.author_name}: Share link BOŞ!")
        print("="*60 + "\n")
    
    # Step 5: Fill report form
    print(f"\n[5/5] Opening report form with {len(reviews_with_links)} review(s)...")
    
    report_id = None
    
    async with ReportFiller(
        headless=False,  # Never headless for CAPTCHA
        google_email=google_email,
        google_password=google_password,
        use_real_chrome=True  # Use real Chrome browser for reliable login
    ) as filler:
        success = await filler.fill_form(
            business=business,
            reviews=reviews_with_links,
            report_reason=report_reason,
            additional_info=additional_info,
            country=country,
            legal_name=legal_name
        )
        
        if success:
            print("\n" + "="*60)
            print("✓ Form filled successfully!")
            print("Please complete the CAPTCHA manually and submit.")
            print("="*60 + "\n")
            
            # Wait for user to complete CAPTCHA and get report ID
            report_id = await filler.wait_for_user(timeout_seconds=1800)
        else:
            print("❌ Failed to fill form")
            return (False, None, reviews_with_links, business)
    
    return (True, report_id, reviews_with_links, business)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ReportBot - Automatically report lowest-rated Google Maps reviews",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using business name (search):
  python -m src.main "Restaurant ABC Istanbul"
  python -m src.main "Coffee Shop XYZ" --reason "Harassment"
  
  # Using direct Maps URL (recommended):
  python -m src.main --url "https://maps.app.goo.gl/8hhn6aYo7Cy78HjK7"
  python -m src.main -u "https://maps.app.goo.gl/xxx" --max-reviews 100
  
  # Using CSV file with multiple URLs:
  python -m src.main --csv urls.csv
  python -m src.main --csv src/urls.csv --max-reviews 100
        """
    )
    
    parser.add_argument(
        "business",
        type=str,
        nargs="?",
        default=None,
        help="Name of the business to search on Google Maps (optional if --url is provided)"
    )
    
    parser.add_argument(
        "--url", "-u",
        type=str,
        default=None,
        help="Direct Google Maps URL to navigate to (e.g., https://maps.app.goo.gl/xxx)"
    )
    
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Path to CSV or Excel (.xlsx) file containing URLs (columns: 'url', 'count' for number of reviews to report)"
    )
    
    parser.add_argument(
        "--convert-to-excel",
        type=str,
        metavar="CSV_PATH",
        default=None,
        help="Convert a CSV file to formatted Excel (.xlsx) and exit"
    )
    
    parser.add_argument(
        "--reason", "-r",
        type=str,
        default="Spam or fake content",
        help="Reason for reporting (default: 'Spam or fake content')"
    )
    
    parser.add_argument(
        "--info", "-i",
        type=str,
        default="",
        help="Additional information for the report"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Maps scraper in headless mode (report form always visible for CAPTCHA)"
    )
    
    parser.add_argument(
        "--max-reviews", "-m",
        type=int,
        default=50,
        help="Maximum number of reviews to fetch (default: 50)"
    )
    
    parser.add_argument(
        "--email", "-e",
        type=str,
        default=None,
        help="Google account email (or set GOOGLE_EMAIL env var)"
    )
    
    parser.add_argument(
        "--password", "-p",
        type=str,
        default=None,
        help="Google account password (or set GOOGLE_PASSWORD env var)"
    )
    
    parser.add_argument(
        "--country", "-c",
        type=str,
        default="Türkiye",
        help="Country of residence for the report form (default: 'Türkiye')"
    )
    
    parser.add_argument(
        "--name", "-n",
        type=str,
        default="Doğukan Öztürk",
        help="Full legal name for the report form (default: 'Doğukan Öztürk')"
    )
    
    args = parser.parse_args()
    
    # Handle CSV to Excel conversion
    if args.convert_to_excel:
        try:
            excel_path = convert_csv_to_excel(args.convert_to_excel)
            print(f"\n✅ Dönüştürme tamamlandı!")
            print(f"   Excel dosyası: {excel_path}")
            print(f"\n💡 Artık bu Excel dosyasını kullanabilirsiniz:")
            print(f"   python -m src.main --csv {excel_path}")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Dönüştürme hatası: {e}")
            sys.exit(1)
    
    # Validate that either business name, URL, or CSV is provided
    if not args.business and not args.url and not args.csv:
        parser.error("Either a business name, --url, or --csv must be provided")
    
    # Collect URLs to process (with review counts)
    urls_to_process = []  # List of (url, count) tuples
    
    if args.csv:
        # Read URLs and counts from CSV or Excel file
        try:
            file_ext = Path(args.csv).suffix.lower()
            
            if file_ext == '.xlsx':
                # Read from Excel file
                urls_to_process = read_excel_urls_with_count(args.csv)
                file_type = "Excel"
            else:
                # Read from CSV file (legacy support)
                urls_to_process = read_urls_with_count_from_csv(args.csv)
                file_type = "CSV"
            
            if not urls_to_process:
                print(f"❌ No URLs found in {file_type} file: {args.csv}")
                sys.exit(1)
            total_reviews = sum(count for _, count in urls_to_process)
            print(f"📄 Loaded {len(urls_to_process)} URLs from {args.csv} ({file_type})")
            print(f"   Toplam raporlanacak yorum sayısı: {total_reviews}")
        except FileNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)
    elif args.url:
        urls_to_process = [(args.url, 1)]  # Default count of 1 for single URL
    
    try:
        if urls_to_process:
            # Process multiple URLs from CSV
            total = len(urls_to_process)
            successful = 0
            failed = 0
            results = []  # Store (url, count, report_id) tuples
            
            for i, (url, review_count) in enumerate(urls_to_process, 1):
                print(f"\n{'#'*60}")
                print(f"# Processing URL {i}/{total}")
                print(f"# {url}")
                print(f"# Review count: {review_count}")
                print(f"{'#'*60}")
                
                # Determine excel path for filtering previously reported reviews
                file_ext = Path(args.csv).suffix.lower()
                excel_path_for_filter = args.csv if file_ext == '.xlsx' else None
                
                success, report_id, reviews_with_links, business = asyncio.run(run_bot(
                    business_name=None,
                    maps_url=url,
                    report_reason=args.reason,
                    additional_info=args.info,
                    headless=args.headless,
                    max_reviews=args.max_reviews,
                    google_email=args.email,
                    google_password=args.password,
                    country=args.country,
                    legal_name=args.name,
                    review_count=review_count,
                    excel_path=excel_path_for_filter
                ))
                
                if success:
                    successful += 1
                    results.append((url, review_count, report_id))
                    
                    # Update file with report ID and review details if we have one
                    if report_id and args.csv:
                        file_ext = Path(args.csv).suffix.lower()
                        if file_ext == '.xlsx':
                            update_excel_with_report(args.csv, url, report_id, reviews=reviews_with_links, business=business)
                        else:
                            update_csv_with_report_id(args.csv, url, report_id, reviews=reviews_with_links, business=business)
                else:
                    failed += 1
                    results.append((url, review_count, None))
            
            # Summary
            print(f"\n{'='*60}")
            print(f"📊 SUMMARY")
            print(f"{'='*60}")
            print(f"  Total URLs: {total}")
            print(f"  ✅ Successful: {successful}")
            print(f"  ❌ Failed: {failed}")
            print(f"\n📋 Report IDs:")
            for url, review_count, report_id in results:
                status = f"✅ {report_id}" if report_id else "❌ N/A"
                print(f"  {url[:40]}... ({review_count} reviews) -> {status}")
            print(f"{'='*60}\n")
            
            sys.exit(0 if failed == 0 else 1)
        else:
            # Single business name search
            success, report_id, reviews_with_links, business = asyncio.run(run_bot(
                business_name=args.business,
                maps_url=args.url,
                report_reason=args.reason,
                additional_info=args.info,
                headless=args.headless,
                max_reviews=args.max_reviews,
                google_email=args.email,
                google_password=args.password,
                country=args.country,
                legal_name=args.name
            ))
            
            if report_id:
                print(f"\n✅ Raporlama Kimliği: {report_id}")
                if reviews_with_links:
                    review_urls = [r.review_url for r in reviews_with_links if r.review_url]
                    print(f"✅ Raporlanan Yorumlar: {', '.join(review_urls)}")
            
            sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
