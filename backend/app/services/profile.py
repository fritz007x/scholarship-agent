from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional

from app.models.profile import UserProfile
from app.models.user import User
from app.schemas.profile import ProfileCreate, ProfileUpdate


class ProfileService:
    def __init__(self, db: Session):
        self.db = db

    def get_profile(self, user_id: int) -> Optional[UserProfile]:
        return self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    def get_or_create_profile(self, user_id: int) -> UserProfile:
        profile = self.get_profile(user_id)
        if not profile:
            profile = UserProfile(user_id=user_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        return profile

    def create_profile(self, user_id: int, profile_data: ProfileCreate) -> UserProfile:
        existing = self.get_profile(user_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Profile already exists for this user"
            )

        profile_dict = profile_data.model_dump(exclude_unset=True)

        # Convert Pydantic models to dicts for JSON fields
        for field in ['extracurriculars', 'awards', 'volunteer_work', 'work_experience']:
            if field in profile_dict and profile_dict[field]:
                profile_dict[field] = [item.model_dump() if hasattr(item, 'model_dump') else item for item in profile_dict[field]]

        profile = UserProfile(user_id=user_id, **profile_dict)
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def update_profile(self, user_id: int, profile_data: ProfileUpdate) -> UserProfile:
        profile = self.get_or_create_profile(user_id)

        update_data = profile_data.model_dump(exclude_unset=True)

        # Convert Pydantic models to dicts for JSON fields
        for field in ['extracurriculars', 'awards', 'volunteer_work', 'work_experience']:
            if field in update_data and update_data[field]:
                update_data[field] = [item.model_dump() if hasattr(item, 'model_dump') else item for item in update_data[field]]

        for field, value in update_data.items():
            setattr(profile, field, value)

        self.db.commit()
        self.db.refresh(profile)
        return profile

    def delete_profile(self, user_id: int) -> bool:
        profile = self.get_profile(user_id)
        if not profile:
            return False
        self.db.delete(profile)
        self.db.commit()
        return True
