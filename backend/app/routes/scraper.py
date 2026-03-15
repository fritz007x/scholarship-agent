"""
Scraper API Routes - Endpoints for managing scholarship scraping.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.models.scraping_job import ScrapingJob, ScrapingLog, ScraperConfig
from app.scraper.orchestrator import get_orchestrator

router = APIRouter(prefix="/scraper", tags=["Scraper"])


# Request/Response schemas

class StartJobRequest(BaseModel):
    source: str = Field(..., description="Scraper source (rss, edu, etc.)")
    mode: str = Field(default="incremental", pattern="^(full|incremental)$")


class JobResponse(BaseModel):
    id: int
    source: str
    mode: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    scholarships_found: int = 0
    scholarships_added: int = 0
    scholarships_updated: int = 0
    scholarships_skipped: int = 0
    errors_count: int = 0
    error_message: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    enabled: Optional[bool] = None
    rate_limit_delay: Optional[int] = Field(None, ge=1, le=60)
    jitter: Optional[int] = Field(None, ge=0, le=10)
    max_retries: Optional[int] = Field(None, ge=1, le=10)
    schedule_cron: Optional[str] = None
    base_url: Optional[str] = None


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin access."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for scraper operations"
        )
    return current_user


@router.get("/status")
def get_scraper_status(
    current_user: User = Depends(require_admin)
):
    """Get overall scraper status and statistics."""
    orchestrator = get_orchestrator()
    stats = orchestrator.get_statistics()

    return {
        "status": "operational",
        "available_sources": stats['available_sources'],
        "statistics": {
            "jobs_by_status": stats['jobs_by_status'],
            "total_scholarships_added": stats['total_scholarships_added'],
            "total_scholarships_updated": stats['total_scholarships_updated'],
            "total_errors": stats['total_errors'],
        }
    }


@router.post("/jobs")
async def start_scraping_job(
    request: StartJobRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Start a new scraping job.

    This endpoint starts the job asynchronously and returns immediately.
    Use GET /scraper/jobs/{job_id} to check status.
    """
    orchestrator = get_orchestrator()

    # Validate source
    if request.source not in orchestrator.get_available_sources():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown source: {request.source}. Available: {orchestrator.get_available_sources()}"
        )

    # Check for existing running job for this source
    existing = db.query(ScrapingJob).filter(
        ScrapingJob.source == request.source,
        ScrapingJob.status == 'running'
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A job for source '{request.source}' is already running (job_id: {existing.id})"
        )

    # Create job
    job = orchestrator.create_job(db, request.source, request.mode)

    # Start scraping in background
    background_tasks.add_task(
        orchestrator.run_scraper,
        request.source,
        request.mode,
        job.id
    )

    return {
        "message": "Scraping job started",
        "job_id": job.id,
        "source": request.source,
        "mode": request.mode,
        "status": "running"
    }


@router.get("/jobs")
def list_jobs(
    source: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(require_admin)
):
    """List scraping jobs with optional filters."""
    orchestrator = get_orchestrator()
    jobs = orchestrator.list_jobs(
        source=source,
        status=status_filter,
        limit=limit
    )

    return {
        "jobs": jobs,
        "total": len(jobs)
    }


@router.get("/jobs/{job_id}")
def get_job(
    job_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific job."""
    job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Get recent logs
    logs = db.query(ScrapingLog).filter(
        ScrapingLog.job_id == job_id
    ).order_by(ScrapingLog.created_at.desc()).limit(50).all()

    return {
        "job": {
            "id": job.id,
            "source": job.source,
            "mode": job.mode,
            "status": job.status,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "scholarships_found": job.scholarships_found,
            "scholarships_added": job.scholarships_added,
            "scholarships_updated": job.scholarships_updated,
            "scholarships_skipped": job.scholarships_skipped,
            "errors_count": job.errors_count,
            "error_message": job.error_message,
            "config_snapshot": job.config_snapshot,
        },
        "logs": [
            {
                "level": log.level,
                "message": log.message,
                "url": log.url,
                "timestamp": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    }


@router.delete("/jobs/{job_id}")
def cancel_job(
    job_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Cancel a running job."""
    job = db.query(ScrapingJob).filter(ScrapingJob.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if job.status != 'running':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not running (status: {job.status})"
        )

    orchestrator = get_orchestrator()
    success = orchestrator.cancel_job(job_id)

    if success:
        return {"message": "Job cancelled", "job_id": job_id}
    else:
        # Job might have completed between check and cancel
        return {"message": "Job may have already completed", "job_id": job_id}


@router.get("/logs")
def get_logs(
    job_id: Optional[int] = None,
    level: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get scraping logs with optional filters."""
    query = db.query(ScrapingLog)

    if job_id:
        query = query.filter(ScrapingLog.job_id == job_id)
    if level:
        query = query.filter(ScrapingLog.level == level.upper())

    logs = query.order_by(ScrapingLog.created_at.desc()).limit(limit).all()

    return {
        "logs": [
            {
                "id": log.id,
                "job_id": log.job_id,
                "level": log.level,
                "message": log.message,
                "url": log.url,
                "timestamp": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": len(logs)
    }


@router.get("/config")
def list_configs(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all scraper configurations."""
    configs = db.query(ScraperConfig).all()
    orchestrator = get_orchestrator()
    available_sources = orchestrator.get_available_sources()

    result = []
    for source in available_sources:
        config = next((c for c in configs if c.source == source), None)
        if config:
            result.append({
                "source": config.source,
                "enabled": config.enabled == 'true',
                "rate_limit_delay": config.rate_limit_delay,
                "jitter": config.jitter,
                "max_retries": config.max_retries,
                "schedule_cron": config.schedule_cron,
                "base_url": config.base_url,
                "last_successful_run": config.last_successful_run.isoformat() if config.last_successful_run else None,
                "consecutive_failures": config.consecutive_failures,
            })
        else:
            # Return defaults for sources without config
            result.append({
                "source": source,
                "enabled": True,
                "rate_limit_delay": 10,
                "jitter": 3,
                "max_retries": 3,
                "schedule_cron": None,
                "base_url": None,
                "last_successful_run": None,
                "consecutive_failures": 0,
            })

    return {"configs": result}


@router.get("/config/{source}")
def get_config(
    source: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get configuration for a specific source."""
    config = db.query(ScraperConfig).filter(
        ScraperConfig.source == source
    ).first()

    if config:
        return {
            "source": config.source,
            "enabled": config.enabled == 'true',
            "rate_limit_delay": config.rate_limit_delay,
            "jitter": config.jitter,
            "max_retries": config.max_retries,
            "schedule_cron": config.schedule_cron,
            "base_url": config.base_url,
            "last_successful_run": config.last_successful_run.isoformat() if config.last_successful_run else None,
            "consecutive_failures": config.consecutive_failures,
        }

    # Return defaults
    return {
        "source": source,
        "enabled": True,
        "rate_limit_delay": 10,
        "jitter": 3,
        "max_retries": 3,
        "schedule_cron": None,
        "base_url": None,
        "last_successful_run": None,
        "consecutive_failures": 0,
    }


@router.put("/config/{source}")
def update_config(
    source: str,
    request: ConfigUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update configuration for a scraper source."""
    config = db.query(ScraperConfig).filter(
        ScraperConfig.source == source
    ).first()

    if not config:
        # Create new config
        config = ScraperConfig(source=source)
        db.add(config)

    # Update fields
    if request.enabled is not None:
        config.enabled = 'true' if request.enabled else 'false'
    if request.rate_limit_delay is not None:
        config.rate_limit_delay = request.rate_limit_delay
    if request.jitter is not None:
        config.jitter = request.jitter
    if request.max_retries is not None:
        config.max_retries = request.max_retries
    if request.schedule_cron is not None:
        config.schedule_cron = request.schedule_cron
    if request.base_url is not None:
        config.base_url = request.base_url

    db.commit()

    return {
        "message": "Configuration updated",
        "source": source,
    }


@router.get("/sources")
def list_sources(
    current_user: User = Depends(require_admin)
):
    """List available scraper sources."""
    orchestrator = get_orchestrator()

    sources = []
    for source in orchestrator.get_available_sources():
        scraper_class = orchestrator.get_scraper_class(source)
        sources.append({
            "name": source,
            "description": scraper_class.__doc__.strip().split('\n')[0] if scraper_class.__doc__ else "No description",
        })

    return {"sources": sources}
