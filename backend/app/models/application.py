from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    scholarship_id = Column(Integer, ForeignKey("scholarships.id"), nullable=False, index=True)

    # Status tracking
    status = Column(String, default="saved")  # saved, in_progress, submitted, awarded, rejected, withdrawn
    deadline = Column(Date)  # Cached from scholarship
    priority = Column(Integer, default=3)  # 1-5 for sorting
    notes = Column(String)

    # Checklist System (JSON)
    checklist = Column(JSON, default=list)
    # [
    #   {
    #     "id": "uuid",
    #     "type": "essay",  # essay, document, form, recommendation, other
    #     "description": "500-word essay on leadership",
    #     "completed": false,
    #     "essay_id": null,
    #     "document_id": null
    #   }
    # ]

    # Progress tracking
    checklist_total = Column(Integer, default=0)
    checklist_completed = Column(Integer, default=0)

    # Pre-filled Data (JSON) - generated from profile when application created
    prefilled_data = Column(JSON, default=dict)
    # {
    #   "full_name": "John Doe",
    #   "email": "john@example.com",
    #   "address": "123 Main St, City, State 12345",
    #   "gpa": "3.8/4.0",
    #   "test_scores": "SAT: 1500, ACT: 34",
    #   "activities_summary": "...",
    #   ...
    # }

    # Submitted Materials
    submitted_essay_ids = Column(JSON, default=list)
    submitted_document_ids = Column(JSON, default=list)
    submitted_at = Column(DateTime(timezone=True))
    award_amount_received = Column(Float)
    result_notes = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="applications")
    scholarship = relationship("Scholarship", back_populates="applications")
