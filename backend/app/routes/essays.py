from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.schemas.essay import EssayCreate, EssayUpdate, EssayResponse, EssayList
from app.services.essay import EssayService
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/essays", tags=["Essays"])


@router.get("", response_model=EssayList)
def list_essays(
    prompt_category: Optional[str] = Query(None, description="Filter by prompt category"),
    is_template: Optional[bool] = Query(None, description="Filter by template status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all essays for the current user with optional filters."""
    essay_service = EssayService(db)
    essays = essay_service.get_all_essays(
        current_user.id,
        prompt_category=prompt_category,
        is_template=is_template
    )
    return EssayList(essays=essays, total=len(essays))


@router.post("", response_model=EssayResponse, status_code=status.HTTP_201_CREATED)
def create_essay(
    essay_data: EssayCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new essay."""
    essay_service = EssayService(db)
    return essay_service.create_essay(current_user.id, essay_data)


@router.get("/{essay_id}", response_model=EssayResponse)
def get_essay(
    essay_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific essay."""
    essay_service = EssayService(db)
    essay = essay_service.get_essay(essay_id, current_user.id)

    if not essay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Essay not found"
        )

    return essay


@router.put("/{essay_id}", response_model=EssayResponse)
def update_essay(
    essay_id: int,
    update_data: EssayUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an essay."""
    essay_service = EssayService(db)
    return essay_service.update_essay(essay_id, current_user.id, update_data)


@router.delete("/{essay_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_essay(
    essay_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an essay."""
    essay_service = EssayService(db)
    if not essay_service.delete_essay(essay_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Essay not found"
        )
