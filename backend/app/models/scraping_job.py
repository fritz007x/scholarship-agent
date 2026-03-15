from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class ScrapingJob(Base):
    """Tracks scraping job execution and results."""
    __tablename__ = "scraping_jobs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False, index=True)  # 'scholarships_com', 'bold_org', 'rss', etc.
    mode = Column(String, default='incremental')  # 'full', 'incremental'
    status = Column(String, nullable=False, default='pending')  # pending, running, completed, failed, cancelled

    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Statistics
    scholarships_found = Column(Integer, default=0)
    scholarships_added = Column(Integer, default=0)
    scholarships_updated = Column(Integer, default=0)
    scholarships_skipped = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)

    # Error tracking
    error_message = Column(Text)

    # Metadata
    config_snapshot = Column(JSON, default=dict)  # Config at time of run
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    logs = relationship("ScrapingLog", back_populates="job", cascade="all, delete-orphan")


class ScrapingLog(Base):
    """Detailed logs for scraping operations."""
    __tablename__ = "scraping_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("scraping_jobs.id"), nullable=False, index=True)
    level = Column(String, nullable=False)  # INFO, WARNING, ERROR
    message = Column(Text, nullable=False)
    url = Column(String)
    extra_data = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    job = relationship("ScrapingJob", back_populates="logs")


class ScraperConfig(Base):
    """Configuration for each scraper source."""
    __tablename__ = "scraper_configs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, unique=True, nullable=False, index=True)
    enabled = Column(String, default='true')  # Use string for SQLite compatibility

    # Rate limiting
    rate_limit_delay = Column(Integer, default=10)  # seconds between requests
    jitter = Column(Integer, default=3)  # random delay variance
    max_retries = Column(Integer, default=3)

    # Scheduling (cron expression)
    schedule_cron = Column(String)  # e.g., "0 2 * * 0" for Sunday 2 AM

    # Status tracking
    last_successful_run = Column(DateTime(timezone=True))
    consecutive_failures = Column(Integer, default=0)

    # Source-specific config
    base_url = Column(String)
    extra_data = Column("metadata", JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
