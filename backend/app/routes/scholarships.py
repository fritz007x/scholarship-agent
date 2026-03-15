from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models.scholarship import Scholarship
from app.schemas.scholarship import ScholarshipResponse, ScholarshipList, ScholarshipCreate
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/scholarships", tags=["Scholarships"])


@router.get("", response_model=ScholarshipList)
def list_scholarships(
    search: Optional[str] = Query(None, description="Search in name and description"),
    category: Optional[str] = Query(None, description="Filter by category"),
    min_amount: Optional[float] = Query(None, description="Minimum award amount"),
    max_amount: Optional[float] = Query(None, description="Maximum award amount"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List and search scholarships. Does not require authentication."""
    query = db.query(Scholarship)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Scholarship.name.ilike(search_term)) |
            (Scholarship.description.ilike(search_term)) |
            (Scholarship.provider.ilike(search_term))
        )

    if min_amount is not None:
        query = query.filter(
            (Scholarship.award_amount >= min_amount) |
            (Scholarship.award_amount_max >= min_amount)
        )

    if max_amount is not None:
        query = query.filter(
            (Scholarship.award_amount <= max_amount) |
            (Scholarship.award_amount_min <= max_amount)
        )

    # Note: Category filtering would need JSON containment query

    total = query.count()
    scholarships = query.order_by(Scholarship.deadline.asc()).offset(offset).limit(limit).all()

    return ScholarshipList(scholarships=scholarships, total=total)


@router.get("/{scholarship_id}", response_model=ScholarshipResponse)
def get_scholarship(
    scholarship_id: int,
    db: Session = Depends(get_db)
):
    """Get scholarship details. Does not require authentication."""
    scholarship = db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()

    if not scholarship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scholarship not found"
        )

    return scholarship


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that ensures the current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


@router.post("", response_model=ScholarshipResponse, status_code=status.HTTP_201_CREATED)
def create_scholarship(
    scholarship_data: ScholarshipCreate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new scholarship. Requires admin authentication."""
    scholarship = Scholarship(**scholarship_data.model_dump())
    db.add(scholarship)
    db.commit()
    db.refresh(scholarship)
    return scholarship
