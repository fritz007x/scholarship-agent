"""
.edu Scholarship Scraper - Scrapes scholarship pages from universities.

This scraper targets university financial aid and scholarship pages
which are typically publicly accessible and contain valuable scholarship info.
"""
import re
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from app.scraper.base import BaseScraper

# Sample university scholarship pages (would be expanded in production)
DEFAULT_EDU_SOURCES = [
    {
        "name": "MIT Scholarships",
        "base_url": "https://sfs.mit.edu",
        "listing_url": "https://sfs.mit.edu/undergraduate-students/types-of-aid/scholarships/",
    },
    # Add more university sources here
]


class EduScholarshipScraper(BaseScraper):
    """
    Scrapes scholarships from .edu university websites.

    Universities publish scholarship information publicly as part
    of their financial aid resources. This scraper extracts that information.
    """

    def __init__(self, db, config: Dict[str, Any], job_id: Optional[int] = None):
        super().__init__(db, config, job_id)
        self.sources = config.get('edu_sources', DEFAULT_EDU_SOURCES)
        self._current_source = None

    @property
    def source_name(self) -> str:
        return "edu"

    @property
    def base_url(self) -> str:
        if self._current_source:
            return self._current_source.get('base_url', '')
        return "https://edu.sites"

    async def fetch_scholarship_urls(self) -> List[str]:
        """Fetch scholarship URLs from .edu sites."""
        all_urls = []

        for source in self.sources:
            self._current_source = source
            self.log_info(f"Scraping {source.get('name')}")

            try:
                listing_url = source.get('listing_url')
                if not listing_url:
                    continue

                # Check robots.txt for this domain
                if not await self.check_robots_txt():
                    self.log_warning(f"Skipping {source.get('name')} - blocked by robots.txt")
                    continue

                html = await self.fetch_page(listing_url)
                if not html:
                    continue

                urls = self._extract_scholarship_links(html, listing_url, source)
                all_urls.extend(urls)
                self.log_info(f"Found {len(urls)} scholarship links from {source.get('name')}")

            except Exception as e:
                self.log_error(f"Error scraping {source.get('name')}: {e}")

        return all_urls

    def _extract_scholarship_links(
        self,
        html: str,
        base_url: str,
        source: Dict
    ) -> List[str]:
        """Extract scholarship links from a listing page."""
        soup = BeautifulSoup(html, 'html.parser')
        urls = []

        # Common link patterns for scholarship pages
        link_patterns = source.get('link_patterns', [
            r'scholarship',
            r'award',
            r'grant',
            r'fellowship',
        ])

        # Get all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()
            href_lower = href.lower()

            # Check if link looks like a scholarship
            is_scholarship = any(
                pattern in href_lower or pattern in text
                for pattern in link_patterns
            )

            if is_scholarship:
                # Make absolute URL
                absolute_url = urljoin(base_url, href)

                # Only include same domain or .edu links
                parsed = urlparse(absolute_url)
                if parsed.netloc.endswith('.edu'):
                    urls.append(absolute_url)

        return list(set(urls))

    async def parse_scholarship_page(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse a scholarship page from an .edu site."""
        soup = BeautifulSoup(html, 'html.parser')

        # Remove script and style elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()

        data = {
            'source_url': url,
            'url': url,
        }

        # Extract page title as scholarship name
        title = soup.find('h1')
        if not title:
            title = soup.find('title')
        if title:
            data['name'] = self.clean_text(title.get_text())

        if not data.get('name'):
            return None

        # Get the source institution as provider
        parsed_url = urlparse(url)
        domain_parts = parsed_url.netloc.split('.')
        if len(domain_parts) >= 2:
            # Get university name from domain (e.g., 'mit' from 'sfs.mit.edu')
            data['provider'] = domain_parts[-2].upper() if domain_parts[-2] != 'www' else domain_parts[-3].upper()

        # Extract main content
        content_selectors = [
            'main',
            'article',
            '.content',
            '#content',
            '.main-content',
            '.scholarship-details',
        ]

        content_element = None
        for selector in content_selectors:
            content_element = soup.select_one(selector)
            if content_element:
                break

        if not content_element:
            content_element = soup.body

        if content_element:
            text = content_element.get_text(separator='\n')
            data['raw_text'] = text
            data['description'] = self.clean_text(text[:2000])

            # Extract amount
            amount_match = re.search(r'\$[\d,]+(?:\.\d{2})?', text)
            if amount_match:
                data['award_amount'] = self.extract_amount(amount_match.group())

            # Extract deadline
            deadline_patterns = [
                r'deadline[:\s]*([A-Za-z]+\s+\d{1,2},?\s*\d{4})',
                r'due\s+(?:date)?[:\s]*([A-Za-z]+\s+\d{1,2},?\s*\d{4})',
                r'applications?\s+due[:\s]*([A-Za-z]+\s+\d{1,2},?\s*\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
            ]
            for pattern in deadline_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    data['deadline'] = self.parse_date(match.group(1))
                    if data['deadline']:
                        break

            # Extract eligibility hints
            eligibility = {}

            # GPA requirement
            gpa_match = re.search(r'(?:minimum\s+)?GPA[:\s]+(\d+\.\d+)', text, re.IGNORECASE)
            if gpa_match:
                try:
                    eligibility['gpa_minimum'] = float(gpa_match.group(1))
                except ValueError:
                    pass

            # Major/field requirement
            major_patterns = [
                r'(?:major|majoring)\s+in\s+([^,.]+)',
                r'(?:field|study)\s+(?:of\s+)?([^,.]+)',
            ]
            for pattern in major_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    eligibility['majors'] = [match.group(1).strip()]
                    break

            # Citizenship requirement
            if 'u.s. citizen' in text.lower() or 'us citizen' in text.lower():
                eligibility['citizenship_required'] = 'us_citizen'
            elif 'permanent resident' in text.lower():
                eligibility['citizenship_required'] = 'permanent_resident'

            if eligibility:
                data['eligibility'] = eligibility

            # Extract keywords from content
            keywords = self._extract_keywords(text)
            if keywords:
                data['keywords'] = keywords

        return data

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from scholarship text."""
        # Common scholarship-related keywords to look for
        keyword_patterns = [
            'stem', 'engineering', 'science', 'technology', 'math',
            'business', 'arts', 'humanities', 'nursing', 'medicine',
            'law', 'education', 'leadership', 'community service',
            'first-generation', 'minority', 'women', 'undergraduate',
            'graduate', 'research', 'international', 'merit',
            'need-based', 'athletic', 'music', 'art',
        ]

        text_lower = text.lower()
        found_keywords = []

        for keyword in keyword_patterns:
            if keyword in text_lower:
                found_keywords.append(keyword)

        return found_keywords[:10]  # Limit to 10 keywords
