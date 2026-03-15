from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List, Dict, Any


class ExtracurricularItem(BaseModel):
    name: str
    role: Optional[str] = None
    years: Optional[int] = None
    hours_per_week: Optional[float] = None


class AwardItem(BaseModel):
    name: str
    year: Optional[int] = None
    level: Optional[str] = None  # school, regional, state, national, international


class VolunteerItem(BaseModel):
    name: str
    role: Optional[str] = None
    hours: Optional[int] = None
    description: Optional[str] = None


class WorkExperienceItem(BaseModel):
    employer: str
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


class ProfileBase(BaseModel):
    # Personal Information
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    phone: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

    # Academic Information
    current_school: Optional[str] = None
    graduation_year: Optional[int] = None
    gpa: Optional[float] = None
    gpa_scale: Optional[float] = 4.0
    class_rank: Optional[int] = None
    class_size: Optional[int] = None
    test_scores: Optional[Dict[str, Any]] = None
    intended_major: Optional[str] = None
    intended_minor: Optional[str] = None
    career_interests: Optional[List[str]] = None

    # Activities & Achievements
    extracurriculars: Optional[List[ExtracurricularItem]] = None
    awards: Optional[List[AwardItem]] = None
    volunteer_work: Optional[List[VolunteerItem]] = None
    work_experience: Optional[List[WorkExperienceItem]] = None

    # Financial Information
    estimated_efc: Optional[int] = None
    household_income_range: Optional[str] = None

    # Demographics
    gender: Optional[str] = None
    ethnicity: Optional[List[str]] = None
    citizenship_status: Optional[str] = None
    first_generation: Optional[bool] = None
    exclude_demographics_from_matching: Optional[bool] = False

    # Essay Topics
    essay_topics: Optional[List[str]] = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
