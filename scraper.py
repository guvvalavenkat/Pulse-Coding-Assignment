#!/usr/bin/env python3
"""
Pulse Coding Assignment - SaaS Product Review Scraper

This script scrapes product reviews from G2, Capterra, and TrustRadius
based on company name and date range filters.
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class ScrapingError(Exception):
    """Custom exception for scraping errors"""
    pass


def validate_dates(start_date: str, end_date: str) -> tuple:
    """
    Validate and parse date strings.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Tuple of (start_date_obj, end_date_obj)
    
    Raises:
        ValueError: If dates are invalid or start_date > end_date
    """
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD format. Error: {e}")
    
    if start > end:
        raise ValueError("start_date must be less than or equal to end_date")
    
    return start, end


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse various date formats commonly found in review sites.
    
    Args:
        date_str: Date string in various formats
    
    Returns:
        datetime object or None if parsing fails
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    date_str = date_str.strip()
    
    # Common date formats used by review platforms
    date_formats = [
        '%Y-%m-%d',
        '%Y-%m-%d %H:%M:%S',
        '%B %d, %Y',
        '%b %d, %Y',
        '%B %d, %Y %I:%M %p',
        '%b %d, %Y %I:%M %p',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%d-%m-%Y',
        '%m-%d-%Y',
        '%d %B %Y',
        '%d %b %Y',
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, AttributeError):
            continue
    
    # Try ISO format variants
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        pass
    
    # For relative dates like "2 months ago", we skip them as they're not accurate
    # In production, you might want to convert these using dateutil.relativedelta
    logger.warning(f"Could not parse date: {date_str}")
    return None


class BaseScraper:
    """Base class for review scrapers"""
    
    BASE_URL = ""
    
    def __init__(self, company_name: str, start_date: datetime, end_date: datetime):
        self.company_name = company_name
        self.start_date = start_date
        self.end_date = end_date
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def search_company(self) -> Optional[str]:
        """Search for company - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement search_company")
    
    def scrape_reviews(self) -> List[Dict]:
        """Scrape reviews - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement scrape_reviews")
    
    def _parse_review(self, element) -> Optional[Dict]:
        """Parse review element - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _parse_review")


class G2Scraper(BaseScraper):
    """Scraper for G2 reviews"""
    
    BASE_URL = "https://www.g2.com"
    
    def search_company(self) -> Optional[str]:
        """
        Search for the company on G2 and return the product URL.
        
        Returns:
            Product URL or None if not found
        """
        search_url = f"{self.BASE_URL}/search?query={quote_plus(self.company_name)}"
        
        try:
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for product links in search results
            # G2 typically has links like /products/[product-name]
            product_links = soup.find_all('a', href=re.compile(r'/products/[^/]+'))
            
            if product_links:
                # Take the first matching product
                product_path = product_links[0].get('href')
                return urljoin(self.BASE_URL, product_path)
            
            logger.error(f"Company '{self.company_name}' not found on G2")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error searching for company on G2: {e}")
            return None
    
    def scrape_reviews(self) -> List[Dict]:
        """
        Scrape all reviews for the company within the date range.
        
        Returns:
            List of review dictionaries
        """
        reviews = []
        product_url = self.search_company()
        
        if not product_url:
            raise ScrapingError(f"Could not find company '{self.company_name}' on G2")
        
        # Navigate to reviews page
        reviews_url = urljoin(product_url, 'reviews')
        page = 1
        
        while True:
            try:
                # G2 uses pagination with page parameter
                paginated_url = f"{reviews_url}?page={page}"
                logger.info(f"Scraping G2 page {page}...")
                
                response = self.session.get(paginated_url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find review elements - this selector may need adjustment based on actual G2 structure
                review_elements = soup.find_all('div', class_=re.compile(r'review|Review'))
                
                if not review_elements:
                    logger.info(f"No more reviews found on page {page}")
                    break
                
                page_reviews = []
                for element in review_elements:
                    review = self._parse_review(element)
                    if review:
                        review_date = review.get('review_date')
                        if review_date:
                            review_dt = parse_date(review_date)
                            if review_dt:
                                # If review is before start_date, stop scraping
                                if review_dt < self.start_date:
                                    logger.info(f"Reached reviews before start_date, stopping pagination")
                                    return reviews
                                
                                # Only include reviews within date range
                                if self.start_date <= review_dt <= self.end_date:
                                    page_reviews.append(review)
                
                if not page_reviews:
                    logger.info(f"No reviews in date range on page {page}, stopping")
                    break
                
                reviews.extend(page_reviews)
                page += 1
                
            except requests.RequestException as e:
                logger.error(f"Error scraping G2 page {page}: {e}")
                break
        
        return reviews
    
    def _parse_review(self, element) -> Optional[Dict]:
        """
        Parse a single review element.
        
        Args:
            element: BeautifulSoup element containing review data
        
        Returns:
            Review dictionary or None
        """
        try:
            review = {
                'source': 'G2',
                'title': '',
                'description': '',
                'review_date': '',
                'reviewer_name': '',
                'rating': ''
            }
            
            # Extract title
            title_elem = element.find(['h3', 'h4', 'div'], class_=re.compile(r'title|heading', re.I))
            if title_elem:
                review['title'] = title_elem.get_text(strip=True)
            
            # Extract description
            desc_elem = element.find('div', class_=re.compile(r'description|text|content|body', re.I))
            if desc_elem:
                review['description'] = desc_elem.get_text(strip=True)
            
            # Extract date
            date_elem = element.find(['time', 'span', 'div'], class_=re.compile(r'date|time', re.I))
            if date_elem:
                review['review_date'] = date_elem.get_text(strip=True)
                # Check datetime attribute
                if date_elem.get('datetime'):
                    review['review_date'] = date_elem.get('datetime')
            
            # Extract reviewer name
            reviewer_elem = element.find(['span', 'div', 'a'], class_=re.compile(r'author|reviewer|name', re.I))
            if reviewer_elem:
                review['reviewer_name'] = reviewer_elem.get_text(strip=True)
            
            # Extract rating
            rating_elem = element.find(['span', 'div'], class_=re.compile(r'rating|star', re.I))
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                # Extract numeric rating
                rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                if rating_match:
                    review['rating'] = rating_match.group(1)
            
            # Only return review if it has at least title or description
            if review['title'] or review['description']:
                return review
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing review element: {e}")
            return None


class CapterraScraper(BaseScraper):
    """Scraper for Capterra reviews"""
    
    BASE_URL = "https://www.capterra.com"
    
    def search_company(self) -> Optional[str]:
        """
        Search for the company on Capterra and return the product URL.
        
        Returns:
            Product URL or None if not found
        """
        search_url = f"{self.BASE_URL}/search?utf8=✓&query={quote_plus(self.company_name)}"
        
        try:
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for product links in search results
            product_links = soup.find_all('a', href=re.compile(r'/reviews/[^/]+'))
            
            if product_links:
                product_path = product_links[0].get('href')
                return urljoin(self.BASE_URL, product_path)
            
            logger.error(f"Company '{self.company_name}' not found on Capterra")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error searching for company on Capterra: {e}")
            return None
    
    def scrape_reviews(self) -> List[Dict]:
        """
        Scrape all reviews for the company within the date range.
        
        Returns:
            List of review dictionaries
        """
        reviews = []
        product_url = self.search_company()
        
        if not product_url:
            raise ScrapingError(f"Could not find company '{self.company_name}' on Capterra")
        
        # Navigate to reviews section
        reviews_url = urljoin(product_url, '#reviews')
        page = 1
        
        while True:
            try:
                # Capterra uses pagination
                paginated_url = f"{product_url}?page={page}#reviews"
                logger.info(f"Scraping Capterra page {page}...")
                
                response = self.session.get(paginated_url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find review elements
                review_elements = soup.find_all('div', class_=re.compile(r'review|comment', re.I))
                
                if not review_elements:
                    logger.info(f"No more reviews found on page {page}")
                    break
                
                page_reviews = []
                for element in review_elements:
                    review = self._parse_review(element)
                    if review:
                        review_date = review.get('review_date')
                        if review_date:
                            review_dt = parse_date(review_date)
                            if review_dt:
                                if review_dt < self.start_date:
                                    logger.info(f"Reached reviews before start_date, stopping pagination")
                                    return reviews
                                
                                if self.start_date <= review_dt <= self.end_date:
                                    page_reviews.append(review)
                
                if not page_reviews:
                    logger.info(f"No reviews in date range on page {page}, stopping")
                    break
                
                reviews.extend(page_reviews)
                page += 1
                
            except requests.RequestException as e:
                logger.error(f"Error scraping Capterra page {page}: {e}")
                break
        
        return reviews
    
    def _parse_review(self, element) -> Optional[Dict]:
        """
        Parse a single review element.
        
        Args:
            element: BeautifulSoup element containing review data
        
        Returns:
            Review dictionary or None
        """
        try:
            review = {
                'source': 'Capterra',
                'title': '',
                'description': '',
                'review_date': '',
                'reviewer_name': '',
                'rating': ''
            }
            
            # Extract title
            title_elem = element.find(['h3', 'h4', 'div'], class_=re.compile(r'title|heading', re.I))
            if title_elem:
                review['title'] = title_elem.get_text(strip=True)
            
            # Extract description
            desc_elem = element.find('div', class_=re.compile(r'description|text|content|body|review-text', re.I))
            if desc_elem:
                review['description'] = desc_elem.get_text(strip=True)
            
            # Extract date
            date_elem = element.find(['time', 'span', 'div'], class_=re.compile(r'date|time', re.I))
            if date_elem:
                review['review_date'] = date_elem.get_text(strip=True)
                if date_elem.get('datetime'):
                    review['review_date'] = date_elem.get('datetime')
            
            # Extract reviewer name
            reviewer_elem = element.find(['span', 'div', 'a'], class_=re.compile(r'author|reviewer|name|user', re.I))
            if reviewer_elem:
                review['reviewer_name'] = reviewer_elem.get_text(strip=True)
            
            # Extract rating
            rating_elem = element.find(['span', 'div'], class_=re.compile(r'rating|star', re.I))
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                if rating_match:
                    review['rating'] = rating_match.group(1)
            
            if review['title'] or review['description']:
                return review
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing review element: {e}")
            return None


class TrustRadiusScraper(BaseScraper):
    """Scraper for TrustRadius reviews (Bonus source)"""
    
    BASE_URL = "https://www.trustradius.com"
    
    def search_company(self) -> Optional[str]:
        """
        Search for the company on TrustRadius and return the product URL.
        
        Returns:
            Product URL or None if not found
        """
        search_url = f"{self.BASE_URL}/search?q={quote_plus(self.company_name)}"
        
        try:
            response = self.session.get(search_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for product links
            product_links = soup.find_all('a', href=re.compile(r'/products/[^/]+'))
            
            if product_links:
                product_path = product_links[0].get('href')
                return urljoin(self.BASE_URL, product_path)
            
            logger.error(f"Company '{self.company_name}' not found on TrustRadius")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Error searching for company on TrustRadius: {e}")
            return None
    
    def scrape_reviews(self) -> List[Dict]:
        """
        Scrape all reviews for the company within the date range.
        
        Returns:
            List of review dictionaries
        """
        reviews = []
        product_url = self.search_company()
        
        if not product_url:
            raise ScrapingError(f"Could not find company '{self.company_name}' on TrustRadius")
        
        # Navigate to reviews page
        reviews_url = urljoin(product_url, 'reviews')
        page = 1
        
        while True:
            try:
                paginated_url = f"{reviews_url}?page={page}"
                logger.info(f"Scraping TrustRadius page {page}...")
                
                response = self.session.get(paginated_url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find review elements
                review_elements = soup.find_all('div', class_=re.compile(r'review|Review', re.I))
                
                if not review_elements:
                    logger.info(f"No more reviews found on page {page}")
                    break
                
                page_reviews = []
                for element in review_elements:
                    review = self._parse_review(element)
                    if review:
                        review_date = review.get('review_date')
                        if review_date:
                            review_dt = parse_date(review_date)
                            if review_dt:
                                if review_dt < self.start_date:
                                    logger.info(f"Reached reviews before start_date, stopping pagination")
                                    return reviews
                                
                                if self.start_date <= review_dt <= self.end_date:
                                    page_reviews.append(review)
                
                if not page_reviews:
                    logger.info(f"No reviews in date range on page {page}, stopping")
                    break
                
                reviews.extend(page_reviews)
                page += 1
                
            except requests.RequestException as e:
                logger.error(f"Error scraping TrustRadius page {page}: {e}")
                break
        
        return reviews
    
    def _parse_review(self, element) -> Optional[Dict]:
        """
        Parse a single review element.
        
        Args:
            element: BeautifulSoup element containing review data
        
        Returns:
            Review dictionary or None
        """
        try:
            review = {
                'source': 'TrustRadius',
                'title': '',
                'description': '',
                'review_date': '',
                'reviewer_name': '',
                'rating': ''
            }
            
            # Extract title
            title_elem = element.find(['h3', 'h4', 'div'], class_=re.compile(r'title|heading', re.I))
            if title_elem:
                review['title'] = title_elem.get_text(strip=True)
            
            # Extract description
            desc_elem = element.find('div', class_=re.compile(r'description|text|content|body', re.I))
            if desc_elem:
                review['description'] = desc_elem.get_text(strip=True)
            
            # Extract date
            date_elem = element.find(['time', 'span', 'div'], class_=re.compile(r'date|time', re.I))
            if date_elem:
                review['review_date'] = date_elem.get_text(strip=True)
                if date_elem.get('datetime'):
                    review['review_date'] = date_elem.get('datetime')
            
            # Extract reviewer name
            reviewer_elem = element.find(['span', 'div', 'a'], class_=re.compile(r'author|reviewer|name', re.I))
            if reviewer_elem:
                review['reviewer_name'] = reviewer_elem.get_text(strip=True)
            
            # Extract rating
            rating_elem = element.find(['span', 'div'], class_=re.compile(r'rating|star', re.I))
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r'(\d+(?:\.\d+)?)', rating_text)
                if rating_match:
                    review['rating'] = rating_match.group(1)
            
            if review['title'] or review['description']:
                return review
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing review element: {e}")
            return None


def get_scraper(source: str, company_name: str, start_date: datetime, end_date: datetime):
    """
    Factory function to get the appropriate scraper instance.
    
    Args:
        source: Source name ('G2', 'Capterra', or 'TrustRadius')
        company_name: Company name to search for
        start_date: Start date for filtering
        end_date: End date for filtering
    
    Returns:
        Scraper instance
    
    Raises:
        ValueError: If source is not supported
    """
    source = source.lower()
    
    if source == 'g2':
        return G2Scraper(company_name, start_date, end_date)
    elif source == 'capterra':
        return CapterraScraper(company_name, start_date, end_date)
    elif source == 'trustradius':
        return TrustRadiusScraper(company_name, start_date, end_date)
    else:
        raise ValueError(f"Unsupported source: {source}. Supported sources: G2, Capterra, TrustRadius")


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Scrape SaaS product reviews from G2, Capterra, or TrustRadius',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scraper.py --company "Salesforce" --start-date 2023-01-01 --end-date 2023-12-31 --source G2
  python scraper.py --company "HubSpot" --start-date 2023-06-01 --end-date 2023-06-30 --source Capterra
        """
    )
    
    parser.add_argument(
        '--company',
        dest='company_name',
        required=True,
        help='Company name to search for'
    )
    
    parser.add_argument(
        '--start-date',
        dest='start_date',
        required=True,
        help='Start date in YYYY-MM-DD format'
    )
    
    parser.add_argument(
        '--end-date',
        dest='end_date',
        required=True,
        help='End date in YYYY-MM-DD format'
    )
    
    parser.add_argument(
        '--source',
        required=True,
        choices=['G2', 'Capterra', 'TrustRadius'],
        help='Review source platform'
    )
    
    parser.add_argument(
        '--output',
        default='reviews.json',
        help='Output JSON file path (default: reviews.json)'
    )
    
    args = parser.parse_args()
    
    try:
        # Validate dates
        logger.info("Validating input parameters...")
        start_date, end_date = validate_dates(args.start_date, args.end_date)
        
        logger.info(f"Scraping reviews for '{args.company_name}' from {args.source}")
        logger.info(f"Date range: {args.start_date} to {args.end_date}")
        
        # Get scraper instance
        scraper = get_scraper(args.source, args.company_name, start_date, end_date)
        
        # Scrape reviews
        reviews = scraper.scrape_reviews()
        
        if not reviews:
            logger.warning(f"No reviews found for '{args.company_name}' in the specified date range")
            reviews = []
        
        # Save to JSON file
        output_data = {
            'company_name': args.company_name,
            'source': args.source,
            'start_date': args.start_date,
            'end_date': args.end_date,
            'total_reviews': len(reviews),
            'reviews': reviews
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Successfully saved {len(reviews)} reviews to {args.output}")
        
        return 0
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return 1
    except ScrapingError as e:
        logger.error(f"Scraping error: {e}")
        return 1
    except requests.RequestException as e:
        logger.error(f"Network error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

