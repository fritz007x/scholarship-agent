from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import datetime

from app.models.application import Application
from app.models.scholarship import Scholarship
from app.models.profile import UserProfile
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ChecklistItemUpdate
from app.services.checklist import ChecklistGenerator
from app.services.profile_mapper import ProfileMapper


class ApplicationService:
    def __init__(self, db: Session):
        self.db = db

    def get_application(self, application_id: int, user_id: int) -> Optional[Application]:
        return self.db.query(Application).filter(
            Application.id == application_id,
            Application.user_id == user_id
        ).first()

    def get_all_applications(self, user_id: int) -> List[Application]:
        return self.db.query(Application).filter(
            Application.user_id == user_id
        ).order_by(Application.deadline.asc()).all()

    def create_application(self, user_id: int, app_data: ApplicationCreate) -> Application:
        # Check if scholarship exists
        scholarship = self.db.query(Scholarship).filter(
            Scholarship.id == app_data.scholarship_id
        ).first()

        if not scholarship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Scholarship not found"
            )

        # Check if user already has an application for this scholarship
        existing = self.db.query(Application).filter(
            Application.user_id == user_id,
            Application.scholarship_id == app_data.scholarship_id
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application already exists for this scholarship"
            )

        # Generate checklist from scholarship requirements
        checklist = ChecklistGenerator.generate_checklist(scholarship)
        total, completed = ChecklistGenerator.calculate_progress(checklist)

        # Get user profile and generate pre-filled data
        profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()
        prefilled_data = ProfileMapper.generate_prefilled_data(profile)

        application = Application(
            user_id=user_id,
            scholarship_id=app_data.scholarship_id,
            deadline=scholarship.deadline,
            priority=app_data.priority or 3,
            notes=app_data.notes,
            checklist=checklist,
            checklist_total=total,
            checklist_completed=completed,
            prefilled_data=prefilled_data,
            status="saved"
        )

        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)
        return application

    def update_application(self, application_id: int, user_id: int, update_data: ApplicationUpdate) -> Application:
        application = self.get_application(application_id, user_id)

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(application, field, value)

        # If status changed to submitted, set submitted_at
        if update_data.status == "submitted" and not application.submitted_at:
            application.submitted_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(application)
        return application

    def update_checklist_item(
        self,
        application_id: int,
        user_id: int,
        item_id: str,
        update_data: ChecklistItemUpdate
    ) -> Application:
        application = self.get_application(application_id, user_id)

        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )

        checklist = application.checklist or []

        # Find and update the item
        item_found = False
        for item in checklist:
            if item["id"] == item_id:
                item["completed"] = update_data.completed
                if update_data.essay_id is not None:
                    item["essay_id"] = update_data.essay_id
                if update_data.document_id is not None:
                    item["document_id"] = update_data.document_id
                item_found = True
                break

        if not item_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Checklist item not found"
            )

        # Recalculate progress
        total, completed = ChecklistGenerator.calculate_progress(checklist)

        application.checklist = checklist
        application.checklist_total = total
        application.checklist_completed = completed

        # Auto-update status based on progress
        if completed == total and application.status == "saved":
            application.status = "in_progress"

        self.db.commit()
        self.db.refresh(application)
        return application

    def delete_application(self, application_id: int, user_id: int) -> bool:
        application = self.get_application(application_id, user_id)

        if not application:
            return False

        self.db.delete(application)
        self.db.commit()
        return True
