from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class EssayBase(BaseModel):
    title: str
    content: Optional[str] = None
    original_prompt: Optional[str] = None
    prompt_category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_template: Optional[bool] = False


class EssayCreate(EssayBase):
    parent_essay_id: Optional[int] = None


class EssayUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    original_prompt: Optional[str] = None
    prompt_category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_template: Optional[bool] = None


class EssayResponse(EssayBase):
    id: int
    user_id: int
    word_count: int
    parent_essay_id: Optional[int] = None
    used_in_applications: List[int]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EssayList(BaseModel):
    essays: List[EssayResponse]
    total: int
