"""
RSS Feed Scraper - Aggregates scholarships from RSS feeds.

This is a low-risk approach that uses publicly available RSS feeds
from scholarship websites and news sources.
"""
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from bs4 import BeautifulSoup

from app.scraper.base import BaseScraper

# Known scholarship RSS feeds (add more as discovered)
DEFAULT_RSS_FEEDS = [
    # Example feeds - replace with actual feeds
    # "https://www.fastweb.com/rss/scholarships",
    # "https://www.scholarships.com/rss/latest",
]


class RssScraper(BaseScraper):
    """
    Scrapes scholarships from RSS feeds.

    RSS feeds are a legitimate and polite way to discover new scholarships
    as they are explicitly published for consumption.
    """

    def __init__(self, db, config: Dict[str, Any], job_id: Optional[int] = None):
        super().__init__(db, config, job_id)
        self.feeds = config.get('feeds', DEFAULT_RSS_FEEDS)

    @property
    def source_name(self) -> str:
        return "rss"

    @property
    def base_url(self) -> str:
        return "https://rss.feeds"  # Placeholder

    async def fetch_scholarship_urls(self) -> List[str]:
        """Fetch scholarship URLs from RSS feeds."""
        urls = []

        for feed_url in self.feeds:
            try:
                self.log_info(f"Fetching RSS feed: {feed_url}")
                content = await self.fetch_page(feed_url)
                if content:
                    feed_urls = self._parse_rss_feed(content)
                    urls.extend(feed_urls)
                    self.log_info(f"Found {len(feed_urls)} items in feed")
            except Exception as e:
                self.log_error(f"Failed to fetch feed {feed_url}: {e}")

        return list(set(urls))  # Deduplicate

    def _parse_rss_feed(self, content: str) -> List[str]:
        """Parse RSS/Atom feed and extract item URLs."""
        urls = []
        soup = BeautifulSoup(content, 'lxml-xml')

        # Try RSS format
        items = soup.find_all('item')
        for item in items:
            link = item.find('link')
            if link and link.string:
                urls.append(link.string.strip())

        # Try Atom format
        entries = soup.find_all('entry')
        for entry in entries:
            link = entry.find('link')
            if link:
                href = link.get('href')
                if href:
                    urls.append(href)

        return urls

    async def parse_scholarship_page(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """Parse scholarship page from RSS link."""
        soup = BeautifulSoup(html, 'html.parser')

        # Try to extract common scholarship fields
        data = {
            'source_url': url,
            'url': url,
        }

        # Try various common selectors for name
        name_selectors = [
            'h1',
            '.scholarship-name',
            '.title',
            '[itemprop="name"]',
            'title',
        ]
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                data['name'] = self.clean_text(element.get_text())
                break

        if not data.get('name'):
            self.log_warning(f"Could not extract name from {url}")
            return None

        # Try to extract description
        desc_selectors = [
            '.scholarship-description',
            '.description',
            '[itemprop="description"]',
            'article',
            '.content',
            'main',
        ]
        for selector in desc_selectors:
            element = soup.select_one(selector)
            if element:
                data['description'] = self.clean_text(element.get_text()[:2000])
                data['raw_text'] = element.get_text()
                break

        # Try to extract amount
        amount_patterns = [
            r'\$[\d,]+(?:\.\d{2})?',
            r'[\d,]+\s*dollars?',
        ]
        page_text = soup.get_text()
        for pattern in amount_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                data['award_amount'] = self.extract_amount(match.group())
                break

        # Try to extract deadline
        deadline_selectors = [
            '.deadline',
            '[itemprop="endDate"]',
            '.due-date',
        ]
        for selector in deadline_selectors:
            element = soup.select_one(selector)
            if element:
                data['deadline'] = self.parse_date(element.get_text())
                break

        # If no deadline found in selectors, try searching text
        if not data.get('deadline'):
            deadline_patterns = [
                r'deadline[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
                r'due[:\s]+([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
            ]
            for pattern in deadline_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    data['deadline'] = self.parse_date(match.group(1))
                    break

        # Try to extract provider
        provider_selectors = [
            '.provider',
            '.organization',
            '[itemprop="provider"]',
            '.sponsor',
        ]
        for selector in provider_selectors:
            element = soup.select_one(selector)
            if element:
                data['provider'] = self.clean_text(element.get_text())
                break

        return data

    async def check_robots_txt(self) -> bool:
        """RSS feeds are meant to be consumed, always return True."""
        return True
