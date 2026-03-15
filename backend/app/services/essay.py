from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List, Optional

from app.models.essay import Essay
from app.schemas.essay import EssayCreate, EssayUpdate


class EssayService:
    def __init__(self, db: Session):
        self.db = db

    def get_essay(self, essay_id: int, user_id: int) -> Optional[Essay]:
        return self.db.query(Essay).filter(
            Essay.id == essay_id,
            Essay.user_id == user_id
        ).first()

    def get_all_essays(
        self,
        user_id: int,
        prompt_category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_template: Optional[bool] = None
    ) -> List[Essay]:
        query = self.db.query(Essay).filter(Essay.user_id == user_id)

        if prompt_category:
            query = query.filter(Essay.prompt_category == prompt_category)
        if is_template is not None:
            query = query.filter(Essay.is_template == is_template)
        # Note: Tag filtering would need JSON containment query specific to DB

        return query.order_by(Essay.updated_at.desc()).all()

    def create_essay(self, user_id: int, essay_data: EssayCreate) -> Essay:
        # Calculate word count
        content = essay_data.content or ""
        word_count = len(content.split()) if content else 0

        essay = Essay(
            user_id=user_id,
            title=essay_data.title,
            content=essay_data.content,
            word_count=word_count,
            original_prompt=essay_data.original_prompt,
            prompt_category=essay_data.prompt_category,
            tags=essay_data.tags or [],
            is_template=essay_data.is_template or False,
            parent_essay_id=essay_data.parent_essay_id,
            used_in_applications=[]
        )

        self.db.add(essay)
        self.db.commit()
        self.db.refresh(essay)
        return essay

    def update_essay(self, essay_id: int, user_id: int, update_data: EssayUpdate) -> Essay:
        essay = self.get_essay(essay_id, user_id)

        if not essay:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Essay not found"
            )

        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(essay, field, value)

        # Recalculate word count if content changed
        if "content" in update_dict:
            content = update_dict["content"] or ""
            essay.word_count = len(content.split()) if content else 0

        self.db.commit()
        self.db.refresh(essay)
        return essay

    def delete_essay(self, essay_id: int, user_id: int) -> bool:
        essay = self.get_essay(essay_id, user_id)

        if not essay:
            return False

        self.db.delete(essay)
        self.db.commit()
        return True

    def add_usage(self, essay_id: int, user_id: int, application_id: int) -> Essay:
        """Track that an essay was used in an application."""
        essay = self.get_essay(essay_id, user_id)

        if not essay:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Essay not found"
            )

        used_in = essay.used_in_applications or []
        if application_id not in used_in:
            used_in.append(application_id)
            essay.used_in_applications = used_in
            self.db.commit()
            self.db.refresh(essay)

        return essay
