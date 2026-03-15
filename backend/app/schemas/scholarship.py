from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List, Dict, Any


class EssayRequirement(BaseModel):
    prompt: str
    word_count: Optional[int] = None


class EligibilityRequirements(BaseModel):
    gpa_minimum: Optional[float] = None
    grade_levels: Optional[List[str]] = None
    majors: Optional[List[str]] = None
    states: Optional[List[str]] = None
    citizenship: Optional[List[str]] = None
    demographics: Optional[Dict[str, Any]] = None


class ApplicationRequirements(BaseModel):
    essays: Optional[List[EssayRequirement]] = None
    documents: Optional[List[str]] = None
    other: Optional[List[str]] = None


class ScholarshipBase(BaseModel):
    name: str
    provider: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    award_amount: Optional[float] = None
    award_amount_min: Optional[float] = None
    award_amount_max: Optional[float] = None
    number_of_awards: Optional[int] = None
    is_renewable: Optional[bool] = False
    deadline: Optional[date] = None
    is_recurring: Optional[bool] = False
    eligibility: Optional[Dict[str, Any]] = None
    application_requirements: Optional[Dict[str, Any]] = None
    keywords: Optional[List[str]] = None
    categories: Optional[List[str]] = None


class ScholarshipCreate(ScholarshipBase):
    pass


class ScholarshipUpdate(BaseModel):
    name: Optional[str] = None
    provider: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    award_amount: Optional[float] = None
    award_amount_min: Optional[float] = None
    award_amount_max: Optional[float] = None
    number_of_awards: Optional[int] = None
    is_renewable: Optional[bool] = None
    deadline: Optional[date] = None
    is_recurring: Optional[bool] = None
    eligibility: Optional[Dict[str, Any]] = None
    application_requirements: Optional[Dict[str, Any]] = None
    keywords: Optional[List[str]] = None
    categories: Optional[List[str]] = None


class ScholarshipResponse(ScholarshipBase):
    id: int
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScholarshipList(BaseModel):
    scholarships: List[ScholarshipResponse]
    total: int
