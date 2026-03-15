from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.services.auth import get_current_user
from app.services.llm import get_llm_service, ParsedScholarship, MatchExplanation
from app.services.profile_mapper import ProfileMapper
from app.models.user import User
from app.models.scholarship import Scholarship

router = APIRouter(prefix="/llm", tags=["LLM"])


class ParseScholarshipRequest(BaseModel):
    raw_text: str
    name: Optional[str] = ""


class ParseScholarshipResponse(BaseModel):
    success: bool
    parsed: Optional[ParsedScholarship] = None
    error: Optional[str] = None


class MatchExplanationResponse(BaseModel):
    success: bool
    explanation: Optional[MatchExplanation] = None
    error: Optional[str] = None


@router.get("/status")
def llm_status():
    """Check if LLM service is available."""
    llm = get_llm_service()
    return {
        "available": llm.is_available(),
        "message": "LLM service is ready" if llm.is_available() else "GOOGLE_API_KEY not configured"
    }


@router.post("/parse-scholarship", response_model=ParseScholarshipResponse)
async def parse_scholarship(
    request: ParseScholarshipRequest,
    current_user: User = Depends(get_current_user)
):
    """Parse unstructured scholarship text into structured eligibility data."""
    llm = get_llm_service()

    if not llm.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service not configured. Set GOOGLE_API_KEY in environment."
        )

    try:
        parsed = await llm.parse_scholarship(request.raw_text, request.name)
        return ParseScholarshipResponse(success=True, parsed=parsed)
    except Exception as e:
        return ParseScholarshipResponse(success=False, error=str(e))


@router.get("/match-explanation/{scholarship_id}", response_model=MatchExplanationResponse)
async def get_match_explanation(
    scholarship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate explanation of why a scholarship matches the current user's profile."""
    llm = get_llm_service()

    if not llm.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service not configured. Set GOOGLE_API_KEY in environment."
        )

    # Get scholarship
    scholarship = db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()
    if not scholarship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scholarship not found"
        )

    # Get user profile
    profile_mapper = ProfileMapper(db)
    user_profile = profile_mapper.get_profile_for_matching(current_user.id)

    if not user_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete your profile first"
        )

    try:
        explanation = await llm.generate_match_explanation(
            scholarship_name=scholarship.name,
            scholarship_description=scholarship.description or "",
            scholarship_requirements=scholarship.eligibility or {},
            user_profile=user_profile
        )
        return MatchExplanationResponse(success=True, explanation=explanation)
    except Exception as e:
        return MatchExplanationResponse(success=False, error=str(e))


@router.post("/parse-and-save/{scholarship_id}")
async def parse_and_save_scholarship(
    scholarship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Parse a scholarship's raw_text and update its eligibility/requirements fields."""
    llm = get_llm_service()

    if not llm.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service not configured"
        )

    # Check admin (only admins can modify scholarships)
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    scholarship = db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()
    if not scholarship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scholarship not found"
        )

    if not scholarship.raw_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scholarship has no raw_text to parse"
        )

    try:
        parsed = await llm.parse_scholarship(scholarship.raw_text, scholarship.name)

        # Update scholarship with parsed data
        scholarship.eligibility = {
            "gpa_minimum": parsed.gpa_minimum,
            "grade_levels": parsed.grade_levels,
            "majors": parsed.majors,
            "states": parsed.states,
            "citizenship_required": parsed.citizenship_required,
            "gender": parsed.gender,
            "ethnicity": parsed.ethnicity,
            "first_generation": parsed.first_generation,
            "financial_need": parsed.financial_need,
        }

        scholarship.application_requirements = {
            "essay_required": parsed.essay_required,
            "essay_prompts": parsed.essay_prompts,
            "documents_required": parsed.documents_required,
        }

        scholarship.keywords = parsed.keywords
        scholarship.categories = parsed.majors[:3] if parsed.majors else []

        db.commit()

        return {
            "success": True,
            "message": "Scholarship updated with parsed data",
            "parsed": parsed.model_dump()
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
