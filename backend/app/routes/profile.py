from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
from app.services.profile import ProfileService
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile. Creates empty profile if none exists."""
    profile_service = ProfileService(db)
    return profile_service.get_or_create_profile(current_user.id)


@router.post("", response_model=ProfileResponse)
def create_profile(
    profile_data: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new profile for current user."""
    profile_service = ProfileService(db)
    return profile_service.create_profile(current_user.id, profile_data)


@router.put("", response_model=ProfileResponse)
def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile. Supports partial updates."""
    profile_service = ProfileService(db)
    return profile_service.update_profile(current_user.id, profile_data)
