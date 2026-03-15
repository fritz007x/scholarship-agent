"""
Rate Limiter - Implements polite crawling with per-domain throttling.
"""
import asyncio
import time
import random
import logging
from collections import defaultdict
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter with per-domain tracking.

    Implements polite crawling behavior with:
    - Configurable delays between requests
    - Random jitter to appear more human-like
    - Per-domain tracking to respect different site limits
    - Exponential backoff on errors
    """

    def __init__(
        self,
        delay: float = 10.0,
        jitter: float = 3.0,
        max_backoff: float = 300.0
    ):
        """
        Initialize rate limiter.

        Args:
            delay: Base delay between requests in seconds
            jitter: Maximum random jitter to add to delay
            max_backoff: Maximum backoff delay for errors
        """
        self.delay = delay
        self.jitter = jitter
        self.max_backoff = max_backoff
        self.last_request: dict[str, float] = defaultdict(float)
        self.backoff_multiplier: dict[str, float] = defaultdict(lambda: 1.0)
        self._lock = asyncio.Lock()

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url or url == 'default':
            return 'default'
        try:
            parsed = urlparse(url)
            return parsed.netloc or 'default'
        except Exception:
            return 'default'

    async def wait(self, url: str = 'default') -> None:
        """
        Wait before making next request to a domain.

        Args:
            url: URL being requested (used to extract domain)
        """
        domain = self._get_domain(url)

        async with self._lock:
            now = time.time()
            elapsed = now - self.last_request[domain]

            # Calculate delay with backoff and jitter
            base_delay = self.delay * self.backoff_multiplier[domain]
            total_delay = base_delay + random.uniform(0, self.jitter)

            if elapsed < total_delay:
                wait_time = total_delay - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s for {domain}")
                await asyncio.sleep(wait_time)

            self.last_request[domain] = time.time()

    def record_success(self, url: str = 'default') -> None:
        """Record successful request, reset backoff."""
        domain = self._get_domain(url)
        self.backoff_multiplier[domain] = 1.0

    def record_failure(self, url: str = 'default') -> None:
        """Record failed request, increase backoff."""
        domain = self._get_domain(url)
        current = self.backoff_multiplier[domain]
        # Exponential backoff with cap
        self.backoff_multiplier[domain] = min(current * 2.0, self.max_backoff / self.delay)
        logger.warning(f"Backoff increased for {domain}: {self.backoff_multiplier[domain]:.1f}x")

    def get_wait_time(self, url: str = 'default') -> float:
        """Get estimated wait time for next request."""
        domain = self._get_domain(url)
        elapsed = time.time() - self.last_request[domain]
        base_delay = self.delay * self.backoff_multiplier[domain]
        remaining = max(0, base_delay - elapsed)
        return remaining


class CircuitBreaker:
    """
    Circuit breaker pattern for handling persistent failures.

    After a threshold of consecutive failures, the circuit opens
    and subsequent requests are rejected until a timeout expires.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 300.0
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures: dict[str, int] = defaultdict(int)
        self.last_failure_time: dict[str, float] = defaultdict(float)
        self.state: dict[str, str] = defaultdict(lambda: 'closed')  # closed, open, half-open

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if not url or url == 'default':
            return 'default'
        try:
            parsed = urlparse(url)
            return parsed.netloc or 'default'
        except Exception:
            return 'default'

    def can_proceed(self, url: str = 'default') -> bool:
        """Check if request can proceed."""
        domain = self._get_domain(url)
        state = self.state[domain]

        if state == 'closed':
            return True

        if state == 'open':
            # Check if recovery timeout has passed
            elapsed = time.time() - self.last_failure_time[domain]
            if elapsed >= self.recovery_timeout:
                self.state[domain] = 'half-open'
                logger.info(f"Circuit half-open for {domain}")
                return True
            return False

        # half-open: allow one request
        return True

    def record_success(self, url: str = 'default') -> None:
        """Record successful request."""
        domain = self._get_domain(url)
        self.failures[domain] = 0
        if self.state[domain] == 'half-open':
            self.state[domain] = 'closed'
            logger.info(f"Circuit closed for {domain}")

    def record_failure(self, url: str = 'default') -> None:
        """Record failed request."""
        domain = self._get_domain(url)
        self.failures[domain] += 1
        self.last_failure_time[domain] = time.time()

        if self.state[domain] == 'half-open':
            # Failed during recovery test
            self.state[domain] = 'open'
            logger.warning(f"Circuit re-opened for {domain}")
        elif self.failures[domain] >= self.failure_threshold:
            self.state[domain] = 'open'
            logger.warning(f"Circuit opened for {domain} after {self.failures[domain]} failures")

    def get_status(self, url: str = 'default') -> dict:
        """Get circuit breaker status for domain."""
        domain = self._get_domain(url)
        return {
            'domain': domain,
            'state': self.state[domain],
            'failures': self.failures[domain],
            'last_failure': self.last_failure_time[domain]
        }
