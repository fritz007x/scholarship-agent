from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List, Dict, Any


class ChecklistItem(BaseModel):
    id: str
    type: str  # essay, document, form, recommendation, other
    description: str
    completed: bool = False
    essay_id: Optional[int] = None
    document_id: Optional[int] = None


class ApplicationBase(BaseModel):
    scholarship_id: int
    priority: Optional[int] = 3
    notes: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[int] = None
    notes: Optional[str] = None


class ChecklistItemUpdate(BaseModel):
    completed: bool
    essay_id: Optional[int] = None
    document_id: Optional[int] = None


class ApplicationResponse(BaseModel):
    id: int
    user_id: int
    scholarship_id: int
    status: str
    deadline: Optional[date] = None
    priority: int
    notes: Optional[str] = None
    checklist: List[ChecklistItem]
    checklist_total: int
    checklist_completed: int
    prefilled_data: Dict[str, Any]
    submitted_essay_ids: List[int]
    submitted_document_ids: List[int]
    submitted_at: Optional[datetime] = None
    award_amount_received: Optional[float] = None
    result_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApplicationWithScholarship(ApplicationResponse):
    scholarship_name: str
    scholarship_provider: Optional[str] = None
    scholarship_award_amount: Optional[float] = None


class ApplicationList(BaseModel):
    applications: List[ApplicationWithScholarship]
    total: int
