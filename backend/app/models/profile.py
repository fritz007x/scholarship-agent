from sqlalchemy import Column, Integer, String, Date, Float, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Personal Information
    first_name = Column(String)
    middle_name = Column(String)
    last_name = Column(String)
    date_of_birth = Column(Date)
    phone = Column(String)
    street_address = Column(String)
    city = Column(String)
    state = Column(String)
    zip_code = Column(String)
    country = Column(String)

    # Academic Information
    current_school = Column(String)
    graduation_year = Column(Integer)
    gpa = Column(Float)
    gpa_scale = Column(Float, default=4.0)
    class_rank = Column(Integer)
    class_size = Column(Integer)
    test_scores = Column(JSON, default=dict)  # {"SAT": 1500, "ACT": 34, etc.}
    intended_major = Column(String)
    intended_minor = Column(String)
    career_interests = Column(JSON, default=list)  # ["Engineering", "Medicine"]

    # Activities & Achievements (JSON arrays)
    extracurriculars = Column(JSON, default=list)  # [{"name": "", "role": "", "years": 0, "hours_per_week": 0}]
    awards = Column(JSON, default=list)  # [{"name": "", "year": 0, "level": ""}]
    volunteer_work = Column(JSON, default=list)  # [{"name": "", "role": "", "hours": 0, "description": ""}]
    work_experience = Column(JSON, default=list)  # [{"employer": "", "title": "", "start": "", "end": "", "description": ""}]

    # Financial Information (optional)
    estimated_efc = Column(Integer)  # Expected Family Contribution
    household_income_range = Column(String)

    # Demographics (optional)
    gender = Column(String)
    ethnicity = Column(JSON, default=list)  # ["Hispanic", "Asian"]
    citizenship_status = Column(String)
    first_generation = Column(Boolean)
    exclude_demographics_from_matching = Column(Boolean, default=False)

    # Essay Topics for matching
    essay_topics = Column(JSON, default=list)  # ["leadership", "community service", "overcoming adversity"]

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="profile")
