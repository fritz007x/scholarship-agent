"""
Scraper Orchestrator - Coordinates and schedules scraping jobs.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Type
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.scraping_job import ScrapingJob, ScraperConfig
from app.scraper.base import BaseScraper, ScraperError
from app.scraper.scrapers.rss_scraper import RssScraper
from app.scraper.scrapers.edu_scraper import EduScholarshipScraper

logger = logging.getLogger(__name__)

# Registry of available scrapers
SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    'rss': RssScraper,
    'edu': EduScholarshipScraper,
    # Add more scrapers here as they're implemented
}


class ScraperOrchestrator:
    """
    Orchestrates scraping jobs across multiple sources.

    Responsibilities:
    - Create and track scraping jobs
    - Load scraper configurations
    - Execute scrapers with proper error handling
    - Update job status and statistics
    """

    def __init__(self, db: Session = None):
        """Initialize orchestrator with optional database session."""
        self._db = db
        self._running_jobs: Dict[int, asyncio.Task] = {}

    def _get_db(self) -> Session:
        """Get database session."""
        if self._db:
            return self._db
        return SessionLocal()

    def _close_db(self, db: Session):
        """Close database session if we created it."""
        if db != self._db:
            db.close()

    def get_scraper_class(self, source: str) -> Optional[Type[BaseScraper]]:
        """Get scraper class by source name."""
        return SCRAPER_REGISTRY.get(source)

    def get_available_sources(self) -> list:
        """Get list of available scraper sources."""
        return list(SCRAPER_REGISTRY.keys())

    def get_scraper_config(self, db: Session, source: str) -> Dict[str, Any]:
        """Get configuration for a scraper source."""
        config = db.query(ScraperConfig).filter(
            ScraperConfig.source == source
        ).first()

        if config:
            return {
                'rate_limit_delay': config.rate_limit_delay,
                'jitter': config.jitter,
                'max_retries': config.max_retries,
                'base_url': config.base_url,
                **(config.extra_data or {}),
            }

        # Default config
        return {
            'rate_limit_delay': 10,
            'jitter': 3,
            'max_retries': 3,
        }

    def create_job(
        self,
        db: Session,
        source: str,
        mode: str = 'incremental'
    ) -> ScrapingJob:
        """Create a new scraping job."""
        config = self.get_scraper_config(db, source)

        job = ScrapingJob(
            source=source,
            mode=mode,
            status='pending',
            config_snapshot=config,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(f"Created scraping job {job.id} for source '{source}'")
        return job

    def update_job_status(
        self,
        db: Session,
        job_id: int,
        status: str,
        stats: Dict[str, int] = None,
        error: str = None
    ):
        """Update job status and statistics."""
        job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
        if not job:
            return

        job.status = status

        if status == 'running':
            job.started_at = datetime.utcnow()
        elif status in ('completed', 'failed', 'cancelled'):
            job.completed_at = datetime.utcnow()

        if stats:
            job.scholarships_found = stats.get('found', 0)
            job.scholarships_added = stats.get('added', 0)
            job.scholarships_updated = stats.get('updated', 0)
            job.scholarships_skipped = stats.get('skipped', 0)
            job.errors_count = stats.get('errors', 0)

        if error:
            job.error_message = error

        db.commit()

    async def run_scraper(
        self,
        source: str,
        mode: str = 'incremental',
        job_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run a scraper for the specified source.

        Args:
            source: Source name (e.g., 'rss', 'edu')
            mode: 'full' or 'incremental'
            job_id: Optional existing job ID

        Returns:
            Result dictionary with job_id and statistics
        """
        db = self._get_db()

        try:
            # Get scraper class
            scraper_class = self.get_scraper_class(source)
            if not scraper_class:
                raise ValueError(f"Unknown scraper source: {source}")

            # Create or get job
            if job_id:
                job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
                if not job:
                    raise ValueError(f"Job {job_id} not found")
            else:
                job = self.create_job(db, source, mode)

            # Check if already running
            if job.status == 'running':
                return {
                    'job_id': job.id,
                    'status': 'already_running',
                    'message': 'Job is already running'
                }

            # Update status to running
            self.update_job_status(db, job.id, 'running')

            # Get config and create scraper
            config = self.get_scraper_config(db, source)
            scraper = scraper_class(db, config, job.id)

            # Run scraper
            logger.info(f"Starting scraper job {job.id} for source '{source}'")
            stats = await scraper.scrape_all()

            # Update job with results
            self.update_job_status(db, job.id, 'completed', stats)

            # Update source config with last successful run
            self._update_source_last_run(db, source)

            return {
                'job_id': job.id,
                'status': 'completed',
                'statistics': stats,
            }

        except ScraperError as e:
            logger.error(f"Scraper error: {e}")
            if job_id:
                self.update_job_status(db, job_id, 'failed', error=str(e))
            return {
                'job_id': job_id,
                'status': 'failed',
                'error': str(e),
            }

        except Exception as e:
            logger.exception(f"Unexpected error in scraper: {e}")
            if job_id:
                self.update_job_status(db, job_id, 'failed', error=str(e))
            return {
                'job_id': job_id,
                'status': 'failed',
                'error': str(e),
            }

        finally:
            self._close_db(db)

    def _update_source_last_run(self, db: Session, source: str):
        """Update last successful run time for a source."""
        config = db.query(ScraperConfig).filter(
            ScraperConfig.source == source
        ).first()

        if config:
            config.last_successful_run = datetime.utcnow()
            config.consecutive_failures = 0
            db.commit()

    async def run_scraper_async(
        self,
        source: str,
        mode: str = 'incremental'
    ) -> int:
        """
        Start a scraper job asynchronously.

        Returns:
            Job ID
        """
        db = self._get_db()
        try:
            job = self.create_job(db, source, mode)
            job_id = job.id
        finally:
            self._close_db(db)

        # Create async task
        task = asyncio.create_task(self.run_scraper(source, mode, job_id))
        self._running_jobs[job_id] = task

        return job_id

    def cancel_job(self, job_id: int) -> bool:
        """Cancel a running job."""
        if job_id in self._running_jobs:
            task = self._running_jobs[job_id]
            task.cancel()
            del self._running_jobs[job_id]

            db = self._get_db()
            try:
                self.update_job_status(db, job_id, 'cancelled')
            finally:
                self._close_db(db)

            return True
        return False

    def get_job_status(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get status of a job."""
        db = self._get_db()
        try:
            job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()
            if not job:
                return None

            return {
                'id': job.id,
                'source': job.source,
                'mode': job.mode,
                'status': job.status,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                'scholarships_found': job.scholarships_found,
                'scholarships_added': job.scholarships_added,
                'scholarships_updated': job.scholarships_updated,
                'scholarships_skipped': job.scholarships_skipped,
                'errors_count': job.errors_count,
                'error_message': job.error_message,
            }
        finally:
            self._close_db(db)

    def list_jobs(
        self,
        source: str = None,
        status: str = None,
        limit: int = 20
    ) -> list:
        """List scraping jobs with optional filters."""
        db = self._get_db()
        try:
            query = db.query(ScrapingJob)

            if source:
                query = query.filter(ScrapingJob.source == source)
            if status:
                query = query.filter(ScrapingJob.status == status)

            jobs = query.order_by(ScrapingJob.created_at.desc()).limit(limit).all()

            return [
                {
                    'id': job.id,
                    'source': job.source,
                    'status': job.status,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'scholarships_added': job.scholarships_added,
                    'errors_count': job.errors_count,
                }
                for job in jobs
            ]
        finally:
            self._close_db(db)

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall scraping statistics."""
        db = self._get_db()
        try:
            from sqlalchemy import func

            # Count jobs by status
            status_counts = db.query(
                ScrapingJob.status,
                func.count(ScrapingJob.id)
            ).group_by(ScrapingJob.status).all()

            # Total scholarships added
            totals = db.query(
                func.sum(ScrapingJob.scholarships_added),
                func.sum(ScrapingJob.scholarships_updated),
                func.sum(ScrapingJob.errors_count),
            ).filter(ScrapingJob.status == 'completed').first()

            return {
                'jobs_by_status': dict(status_counts),
                'total_scholarships_added': totals[0] or 0,
                'total_scholarships_updated': totals[1] or 0,
                'total_errors': totals[2] or 0,
                'available_sources': self.get_available_sources(),
            }
        finally:
            self._close_db(db)


# Global orchestrator instance
_orchestrator: Optional[ScraperOrchestrator] = None


def get_orchestrator() -> ScraperOrchestrator:
    """Get singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ScraperOrchestrator()
    return _orchestrator
