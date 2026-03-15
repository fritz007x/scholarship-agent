"""
Agent API Routes - Endpoints for the scholarship agent.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.auth import get_current_user
from app.services.agent_service import AgentService
from app.services.llm import get_llm_service
from app.models.user import User
from app.schemas.agent import (
    ChatRequest, ChatResponse,
    SessionResponse, SessionListResponse,
    RecommendationsResponse
)

router = APIRouter(prefix="/agent", tags=["Agent"])


# Rate limiting tracking (simple in-memory, use Redis for production)
_rate_limits = {}
_last_cleanup = 0
_CLEANUP_INTERVAL = 300  # Clean up every 5 minutes
_MAX_RATE_LIMIT_ENTRIES = 10000  # Maximum entries before forced cleanup


def check_rate_limit(user_id: int, max_requests: int = 10, window_seconds: int = 60) -> bool:
    """Simple rate limiting check with memory leak prevention."""
    import time
    global _last_cleanup
    current_time = time.time()
    key = f"agent_{user_id}"

    # Periodic cleanup of stale entries to prevent memory leak
    if current_time - _last_cleanup > _CLEANUP_INTERVAL or len(_rate_limits) > _MAX_RATE_LIMIT_ENTRIES:
        _cleanup_stale_entries(current_time, window_seconds)
        _last_cleanup = current_time

    if key not in _rate_limits:
        _rate_limits[key] = []

    # Remove old entries for this user
    _rate_limits[key] = [t for t in _rate_limits[key] if current_time - t < window_seconds]

    if len(_rate_limits[key]) >= max_requests:
        return False

    _rate_limits[key].append(current_time)
    return True


def _cleanup_stale_entries(current_time: float, window_seconds: int = 60) -> None:
    """Remove stale rate limit entries to prevent memory leak."""
    stale_keys = []
    for key, timestamps in _rate_limits.items():
        # Filter out old timestamps
        valid_timestamps = [t for t in timestamps if current_time - t < window_seconds]
        if not valid_timestamps:
            stale_keys.append(key)
        else:
            _rate_limits[key] = valid_timestamps

    # Remove keys with no valid timestamps
    for key in stale_keys:
        del _rate_limits[key]


@router.get("/status")
def agent_status():
    """Check if the agent service is available."""
    llm = get_llm_service()
    return {
        "available": llm.is_available(),
        "message": "Agent service is ready" if llm.is_available() else "LLM not configured (GOOGLE_API_KEY required)",
        "features": {
            "chat": llm.is_available(),
            "recommendations": True,  # Works with basic matching even without LLM
            "tools": [
                "search_scholarships",
                "get_scholarship_details",
                "evaluate_scholarship_match",
                "get_user_profile",
                "get_user_applications",
                "get_user_essays",
                "get_user_documents",
                "create_application",
                "get_application_checklist",
                "check_missing_requirements",
                "suggest_essay_matches",
                "get_recommendations"
            ]
        }
    }


@router.post("/chat", response_model=ChatResponse)
async def agent_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with the scholarship agent.

    Send a message and receive an intelligent response. The agent can:
    - Search for scholarships based on your criteria
    - Evaluate how well you match specific scholarships
    - Help you manage applications
    - Provide personalized recommendations

    Optionally pass a session_id to continue a previous conversation.
    """
    # Check LLM availability
    llm = get_llm_service()
    if not llm.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent service requires LLM configuration. Set GOOGLE_API_KEY in environment."
        )

    # Rate limiting
    if not check_rate_limit(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait a moment before trying again."
        )

    # Create agent service and process message
    agent = AgentService(db, current_user.id)

    try:
        response = await agent.chat(
            message=request.message,
            session_id=request.session_id
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent error: {str(e)}"
        )


@router.get("/sessions", response_model=SessionListResponse)
def list_sessions(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's agent conversation sessions."""
    agent = AgentService(db, current_user.id)
    sessions = agent.list_sessions(limit=limit)

    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=i,
                session_id=s["session_id"],
                is_active=s["is_active"],
                total_messages=s["total_messages"],
                total_tool_calls=0,  # Not tracked in list view
                last_activity=s["last_activity"],
                created_at=s["created_at"],
                context={}
            )
            for i, s in enumerate(sessions)
        ],
        total=len(sessions)
    )


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific session including message history."""
    agent = AgentService(db, current_user.id)
    session = agent.get_session_history(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return session


@router.delete("/sessions/{session_id}")
def archive_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Archive (close) a conversation session."""
    agent = AgentService(db, current_user.id)
    success = agent.archive_session(session_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    return {"success": True, "message": "Session archived"}


@router.get("/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    limit: int = 5,
    exclude_applied: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized scholarship recommendations.

    This endpoint provides quick recommendations without starting a conversation.
    For more interactive assistance, use the /agent/chat endpoint.
    """
    agent = AgentService(db, current_user.id)

    try:
        recommendations = await agent.get_recommendations(
            limit=limit,
            exclude_applied=exclude_applied
        )
        return recommendations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}"
        )


# Quick action endpoints for common tasks

class QuickSearchRequest(BaseModel):
    keywords: Optional[List[str]] = None
    min_award: Optional[float] = None
    max_award: Optional[float] = None
    limit: int = Field(default=10, le=50)


@router.post("/quick/search")
async def quick_search(
    request: QuickSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick scholarship search without full conversation.

    For simple searches, this is faster than using chat.
    """
    from app.services.agent_tools import AgentToolRegistry

    tools = AgentToolRegistry(db, current_user.id)
    result = await tools.execute_tool(
        "search_scholarships",
        {
            "keywords": request.keywords,
            "min_award": request.min_award,
            "max_award": request.max_award,
            "limit": request.limit
        }
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Search failed")
        )

    return result["data"]


@router.get("/quick/match/{scholarship_id}")
async def quick_match(
    scholarship_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick match evaluation for a specific scholarship.

    Returns match score and explanation without full conversation.
    """
    from app.services.agent_tools import AgentToolRegistry

    tools = AgentToolRegistry(db, current_user.id)
    result = await tools.execute_tool(
        "evaluate_scholarship_match",
        {"scholarship_id": scholarship_id}
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Match evaluation failed")
        )

    return result["data"]


@router.get("/quick/checklist/{application_id}")
async def quick_checklist(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quick checklist view for an application.

    Returns checklist status and missing items.
    """
    from app.services.agent_tools import AgentToolRegistry

    tools = AgentToolRegistry(db, current_user.id)

    # Get checklist
    checklist_result = await tools.execute_tool(
        "get_application_checklist",
        {"application_id": application_id}
    )

    if not checklist_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=checklist_result.get("error", "Failed to get checklist")
        )

    # Get missing requirements
    missing_result = await tools.execute_tool(
        "check_missing_requirements",
        {"application_id": application_id}
    )

    return {
        "checklist": checklist_result["data"],
        "missing": missing_result.get("data", {}) if missing_result.get("success") else {}
    }
