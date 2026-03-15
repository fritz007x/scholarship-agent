from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Essay(Base):
    __tablename__ = "essays"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Content
    title = Column(String, nullable=False)
    content = Column(String)
    word_count = Column(Integer, default=0)
    original_prompt = Column(String)

    # Categorization
    prompt_category = Column(String)  # career_goals, overcoming_challenges, community_service, leadership, etc.
    tags = Column(JSON, default=list)  # ["personal", "academic", "STEM"]
    is_template = Column(Boolean, default=False)  # Master version vs adapted

    # Versioning
    parent_essay_id = Column(Integer, ForeignKey("essays.id"))

    # Usage tracking
    used_in_applications = Column(JSON, default=list)  # [application_id, ...]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="essays")
    parent_essay = relationship("Essay", remote_side=[id])
