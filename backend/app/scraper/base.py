"""
Base Scraper - Abstract base class for all scholarship scrapers.
"""
import asyncio
import hashlib
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, urljoin

import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models.scholarship import Scholarship
from app.models.scraping_job import ScrapingJob, ScrapingLog
from app.scraper.rate_limiter import RateLimiter, CircuitBreaker
from app.services.llm import get_llm_service

logger = logging.getLogger(__name__)

# Common User-Agent strings (rotate to avoid detection)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class ScraperError(Exception):
    """Base exception for scraper errors."""
    pass


class RobotsTxtViolation(ScraperError):
    """Raised when robots.txt disallows scraping."""
    pass


class BaseScraper(ABC):
    """
    Abstract base class for scholarship scrapers.

    Provides common functionality for:
    - HTTP requests with rate limiting
    - robots.txt compliance
    - HTML parsing
    - Deduplication
    - Database operations
    - Logging
    """

    def __init__(
        self,
        db: Session,
        config: Dict[str, Any],
        job_id: Optional[int] = None
    ):
        """
        Initialize scraper.

        Args:
            db: SQLAlchemy database session
            config: Scraper configuration dict
            job_id: Optional job ID for logging
        """
        self.db = db
        self.config = config
        self.job_id = job_id

        # Rate limiting
        self.rate_limiter = RateLimiter(
            delay=config.get('rate_limit_delay', 10),
            jitter=config.get('jitter', 3)
        )
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=config.get('circuit_breaker_threshold', 5),
            recovery_timeout=config.get('circuit_breaker_timeout', 300)
        )

        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None
        self._user_agent_index = 0

        # LLM service for parsing
        self.llm_service = get_llm_service()

        # Robots.txt cache
        self._robots_cache: Dict[str, Dict] = {}

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Unique identifier for this scraper source."""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Base URL for the scholarship source."""
        pass

    @abstractmethod
    async def fetch_scholarship_urls(self) -> List[str]:
        """
        Fetch list of scholarship page URLs to scrape.

        Returns:
            List of URLs to individual scholarship pages
        """
        pass

    @abstractmethod
    async def parse_scholarship_page(self, html: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single scholarship page and extract data.

        Args:
            html: Raw HTML content
            url: URL of the page

        Returns:
            Dictionary with scholarship data, or None if parsing failed
        """
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        await self._create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._close_session()

    async def _create_session(self):
        """Create aiohttp session."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def _close_session(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with rotating User-Agent."""
        self._user_agent_index = (self._user_agent_index + 1) % len(USER_AGENTS)
        return {
            "User-Agent": USER_AGENTS[self._user_agent_index],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    async def check_robots_txt(self) -> bool:
        """
        Check if scraping is allowed by robots.txt.

        Returns:
            True if scraping is allowed, False otherwise
        """
        domain = urlparse(self.base_url).netloc
        if domain in self._robots_cache:
            return self._robots_cache[domain].get('allowed', False)

        robots_url = urljoin(self.base_url, '/robots.txt')
        try:
            async with self.session.get(robots_url, headers=self._get_headers()) as response:
                if response.status == 200:
                    text = await response.text()
                    allowed = self._parse_robots_txt(text)
                    self._robots_cache[domain] = {'allowed': allowed, 'content': text}
                    return allowed
                else:
                    # No robots.txt = allowed
                    self._robots_cache[domain] = {'allowed': True}
                    return True
        except Exception as e:
            logger.warning(f"Failed to fetch robots.txt for {domain}: {e}")
            # Be conservative - assume allowed but log warning
            self._robots_cache[domain] = {'allowed': True}
            return True

    def _parse_robots_txt(self, content: str) -> bool:
        """
        Parse robots.txt and check if scraping is allowed.

        This is a simplified parser - for production, use robotexclusionrulesparser.
        """
        lines = content.lower().split('\n')
        user_agent_applies = False
        disallow_all = False

        for line in lines:
            line = line.strip()
            if line.startswith('user-agent:'):
                agent = line.split(':', 1)[1].strip()
                user_agent_applies = agent == '*' or 'bot' in agent

            if user_agent_applies:
                if line.startswith('disallow:'):
                    path = line.split(':', 1)[1].strip()
                    if path == '/' or path == '/*':
                        disallow_all = True

                if line.startswith('crawl-delay:'):
                    try:
                        delay = float(line.split(':', 1)[1].strip())
                        # Respect crawl-delay
                        self.rate_limiter.delay = max(self.rate_limiter.delay, delay)
                    except ValueError:
                        pass

        return not disallow_all

    async def fetch_page(self, url: str, retries: int = 3) -> Optional[str]:
        """
        Fetch a page with rate limiting and retries.

        Args:
            url: URL to fetch
            retries: Number of retry attempts

        Returns:
            HTML content or None if failed
        """
        if not self.circuit_breaker.can_proceed(url):
            self.log_warning(f"Circuit breaker open for {url}")
            return None

        for attempt in range(retries):
            try:
                await self.rate_limiter.wait(url)

                async with self.session.get(url, headers=self._get_headers()) as response:
                    if response.status == 200:
                        html = await response.text()
                        self.rate_limiter.record_success(url)
                        self.circuit_breaker.record_success(url)
                        return html

                    elif response.status == 429:
                        # Rate limited - back off
                        self.rate_limiter.record_failure(url)
                        retry_after = int(response.headers.get('Retry-After', 60))
                        self.log_warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)

                    elif response.status in (403, 404):
                        # Don't retry these
                        self.log_warning(f"HTTP {response.status} for {url}")
                        return None

                    else:
                        self.log_warning(f"HTTP {response.status} for {url}")
                        self.rate_limiter.record_failure(url)

            except asyncio.TimeoutError:
                self.log_warning(f"Timeout fetching {url} (attempt {attempt + 1})")
                self.rate_limiter.record_failure(url)

            except Exception as e:
                self.log_error(f"Error fetching {url}: {e}")
                self.rate_limiter.record_failure(url)

            # Exponential backoff between retries
            if attempt < retries - 1:
                await asyncio.sleep(5 * (2 ** attempt))

        self.circuit_breaker.record_failure(url)
        return None

    def generate_hash(self, data: Dict[str, Any]) -> str:
        """Generate a hash for deduplication."""
        # Use key fields that identify a unique scholarship
        key_fields = [
            str(data.get('name', '')).lower().strip(),
            str(data.get('provider', '')).lower().strip(),
            str(data.get('deadline', '')),
            str(data.get('award_amount', '')),
        ]
        content = '|'.join(key_fields)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def find_existing_scholarship(self, source_url: str, scrape_hash: str) -> Optional[Scholarship]:
        """Find existing scholarship by URL or hash."""
        # First try exact URL match
        if source_url:
            existing = self.db.query(Scholarship).filter(
                Scholarship.source_url == source_url
            ).first()
            if existing:
                return existing

        # Then try hash match
        if scrape_hash:
            existing = self.db.query(Scholarship).filter(
                Scholarship.scrape_hash == scrape_hash
            ).first()
            if existing:
                return existing

        return None

    async def save_scholarship(self, data: Dict[str, Any]) -> str:
        """
        Save or update a scholarship in the database.

        Args:
            data: Scholarship data dictionary

        Returns:
            'added', 'updated', or 'skipped'
        """
        source_url = data.get('source_url')
        scrape_hash = self.generate_hash(data)

        existing = self.find_existing_scholarship(source_url, scrape_hash)

        if existing:
            # Check if data has changed
            if existing.scrape_hash == scrape_hash:
                # No changes, just update last_scraped_at
                existing.last_scraped_at = datetime.utcnow()
                self.db.commit()
                return 'skipped'

            # Update existing scholarship
            existing.name = data.get('name', existing.name)
            existing.provider = data.get('provider', existing.provider)
            existing.description = data.get('description', existing.description)
            existing.url = data.get('url', existing.url)
            existing.award_amount = data.get('award_amount')
            existing.award_amount_min = data.get('award_amount_min')
            existing.award_amount_max = data.get('award_amount_max')
            existing.deadline = data.get('deadline')
            existing.eligibility = data.get('eligibility', existing.eligibility)
            existing.application_requirements = data.get('application_requirements', existing.application_requirements)
            existing.keywords = data.get('keywords', existing.keywords)
            existing.raw_text = data.get('raw_text')
            existing.scrape_hash = scrape_hash
            existing.last_scraped_at = datetime.utcnow()
            existing.verification_status = 'unverified'
            self.db.commit()
            return 'updated'

        # Create new scholarship
        scholarship = Scholarship(
            name=data.get('name'),
            provider=data.get('provider'),
            description=data.get('description'),
            url=data.get('url'),
            award_amount=data.get('award_amount'),
            award_amount_min=data.get('award_amount_min'),
            award_amount_max=data.get('award_amount_max'),
            deadline=data.get('deadline'),
            eligibility=data.get('eligibility', {}),
            application_requirements=data.get('application_requirements', {}),
            keywords=data.get('keywords', []),
            source=self.source_name,
            source_url=source_url,
            raw_text=data.get('raw_text'),
            scrape_hash=scrape_hash,
            last_scraped_at=datetime.utcnow(),
            verification_status='unverified',
        )
        self.db.add(scholarship)
        self.db.commit()
        return 'added'

    async def parse_with_llm(self, raw_text: str, name: str = "") -> Dict[str, Any]:
        """
        Use LLM to parse unstructured scholarship text.

        Args:
            raw_text: Raw scholarship description text
            name: Optional scholarship name

        Returns:
            Parsed scholarship data dictionary
        """
        if not self.llm_service.is_available():
            return {}

        try:
            parsed = await self.llm_service.parse_scholarship(raw_text, name)
            return {
                'eligibility': {
                    'gpa_minimum': parsed.gpa_minimum,
                    'grade_levels': parsed.grade_levels,
                    'majors': parsed.majors,
                    'states': parsed.states,
                    'citizenship_required': parsed.citizenship_required,
                    'gender': parsed.gender,
                    'ethnicity': parsed.ethnicity,
                    'first_generation': parsed.first_generation,
                    'financial_need': parsed.financial_need,
                },
                'application_requirements': {
                    'essay_required': parsed.essay_required,
                    'essays': parsed.essay_prompts,
                    'documents': parsed.documents_required,
                },
                'keywords': parsed.keywords or [],
            }
        except Exception as e:
            logger.error(f"LLM parsing failed: {e}")
            return {}

    async def scrape_all(self) -> Dict[str, int]:
        """
        Main scraping workflow.

        Returns:
            Statistics dictionary with counts
        """
        stats = {
            'found': 0,
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
        }

        try:
            await self._create_session()

            # Check robots.txt
            if not await self.check_robots_txt():
                raise RobotsTxtViolation(f"robots.txt disallows scraping {self.source_name}")

            self.log_info(f"Starting scrape for {self.source_name}")

            # Fetch scholarship URLs
            urls = await self.fetch_scholarship_urls()
            stats['found'] = len(urls)
            self.log_info(f"Found {len(urls)} scholarship URLs")

            # Process each URL
            for i, url in enumerate(urls):
                try:
                    self.log_info(f"Processing {i + 1}/{len(urls)}: {url}")

                    html = await self.fetch_page(url)
                    if not html:
                        stats['errors'] += 1
                        continue

                    data = await self.parse_scholarship_page(html, url)
                    if not data:
                        stats['errors'] += 1
                        continue

                    # Add source URL
                    data['source_url'] = url

                    # Use LLM to enhance parsing if raw_text available
                    if data.get('raw_text') and not data.get('eligibility'):
                        llm_data = await self.parse_with_llm(
                            data['raw_text'],
                            data.get('name', '')
                        )
                        data.update(llm_data)

                    result = await self.save_scholarship(data)
                    stats[result] += 1

                except Exception as e:
                    stats['errors'] += 1
                    self.log_error(f"Error processing {url}: {e}")

        except RobotsTxtViolation as e:
            self.log_error(str(e))
            raise

        except Exception as e:
            self.log_error(f"Scraping failed: {e}")
            raise

        finally:
            await self._close_session()

        self.log_info(f"Scrape completed: {stats}")
        return stats

    # Logging helpers
    def log_info(self, message: str, url: str = None):
        """Log info message."""
        logger.info(f"[{self.source_name}] {message}")
        if self.job_id:
            self._save_log('INFO', message, url)

    def log_warning(self, message: str, url: str = None):
        """Log warning message."""
        logger.warning(f"[{self.source_name}] {message}")
        if self.job_id:
            self._save_log('WARNING', message, url)

    def log_error(self, message: str, url: str = None):
        """Log error message."""
        logger.error(f"[{self.source_name}] {message}")
        if self.job_id:
            self._save_log('ERROR', message, url)

    def _save_log(self, level: str, message: str, url: str = None):
        """Save log to database."""
        try:
            log = ScrapingLog(
                job_id=self.job_id,
                level=level,
                message=message,
                url=url,
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to save log: {e}")

    @staticmethod
    def clean_text(text: Optional[str]) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def extract_amount(text: str) -> Optional[float]:
        """Extract dollar amount from text."""
        if not text:
            return None
        # Match patterns like $1,000 or $1000 or 1,000
        match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', text.replace(',', ''))
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                pass
        return None

    @staticmethod
    def parse_date(text: str) -> Optional[datetime]:
        """Parse date from various formats."""
        if not text:
            return None

        import re
        from datetime import datetime

        # Common date patterns
        patterns = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # MM/DD/YYYY
            r'(\d{4})-(\d{2})-(\d{2})',  # YYYY-MM-DD
            r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',  # Month DD, YYYY
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        if groups[0].isalpha():
                            # Month name format
                            return datetime.strptime(
                                f"{groups[0]} {groups[1]} {groups[2]}",
                                "%B %d %Y"
                            ).date()
                        elif len(groups[0]) == 4:
                            # YYYY-MM-DD
                            return datetime.strptime(
                                f"{groups[0]}-{groups[1]}-{groups[2]}",
                                "%Y-%m-%d"
                            ).date()
                        else:
                            # MM/DD/YYYY
                            return datetime.strptime(
                                f"{groups[0]}/{groups[1]}/{groups[2]}",
                                "%m/%d/%Y"
                            ).date()
                except ValueError:
                    continue

        return None
