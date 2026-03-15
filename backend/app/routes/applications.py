from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.application import (
    ApplicationCreate, ApplicationUpdate, ApplicationResponse,
    ApplicationWithScholarship, ApplicationList, ChecklistItemUpdate
)
from app.services.application import ApplicationService
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get("", response_model=ApplicationList)
def list_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all applications for the current user."""
    app_service = ApplicationService(db)
    applications = app_service.get_all_applications(current_user.id)

    result = []
    for app in applications:
        app_dict = {
            "id": app.id,
            "user_id": app.user_id,
            "scholarship_id": app.scholarship_id,
            "status": app.status,
            "deadline": app.deadline,
            "priority": app.priority,
            "notes": app.notes,
            "checklist": app.checklist or [],
            "checklist_total": app.checklist_total,
            "checklist_completed": app.checklist_completed,
            "prefilled_data": app.prefilled_data or {},
            "submitted_essay_ids": app.submitted_essay_ids or [],
            "submitted_document_ids": app.submitted_document_ids or [],
            "submitted_at": app.submitted_at,
            "award_amount_received": app.award_amount_received,
            "result_notes": app.result_notes,
            "created_at": app.created_at,
            "updated_at": app.updated_at,
            "scholarship_name": app.scholarship.name if app.scholarship else "Unknown",
            "scholarship_provider": app.scholarship.provider if app.scholarship else None,
            "scholarship_award_amount": app.scholarship.award_amount if app.scholarship else None
        }
        result.append(ApplicationWithScholarship(**app_dict))

    return ApplicationList(applications=result, total=len(result))


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    app_data: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new application for a scholarship."""
    app_service = ApplicationService(db)
    return app_service.create_application(current_user.id, app_data)


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific application."""
    app_service = ApplicationService(db)
    application = app_service.get_application(application_id, current_user.id)

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    return application


@router.put("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: int,
    update_data: ApplicationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an application."""
    app_service = ApplicationService(db)
    return app_service.update_application(application_id, current_user.id, update_data)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an application."""
    app_service = ApplicationService(db)
    if not app_service.delete_application(application_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )


@router.put("/{application_id}/checklist/{item_id}", response_model=ApplicationResponse)
def update_checklist_item(
    application_id: int,
    item_id: str,
    update_data: ChecklistItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a checklist item as complete/incomplete and optionally attach a resource."""
    app_service = ApplicationService(db)
    return app_service.update_checklist_item(
        application_id, current_user.id, item_id, update_data
    )
