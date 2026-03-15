from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    SYSTEM = "system"


class ToolCall(BaseModel):
    """Represents a tool call made by the agent."""
    id: str
    name: str
    parameters: Dict[str, Any]


class ToolResult(BaseModel):
    """Result from executing a tool."""
    tool_call_id: str
    name: str
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class Message(BaseModel):
    """A single message in the conversation."""
    role: MessageRole
    content: str
    tool_calls: Optional[List[ToolCall]] = None
    tool_results: Optional[List[ToolResult]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentContext(BaseModel):
    """Working context for the agent."""
    current_scholarships: List[int] = []
    user_intent: Optional[str] = None
    active_filters: Dict[str, Any] = {}
    workflow_state: Optional[str] = None
    last_tool_results: Dict[str, Any] = {}


# Request/Response schemas

class ChatRequest(BaseModel):
    """Request to chat with the agent."""
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None  # If None, creates new session


class ChatResponse(BaseModel):
    """Response from the agent."""
    session_id: str
    message: str
    tool_calls: Optional[List[ToolCall]] = None
    scholarships_mentioned: List[int] = []  # IDs of scholarships referenced
    suggested_actions: List[str] = []  # Quick actions user can take


class SessionResponse(BaseModel):
    """Response with session details."""
    id: int
    session_id: str
    is_active: bool
    total_messages: int
    total_tool_calls: int
    last_activity: datetime
    created_at: datetime
    context: AgentContext

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """List of user's sessions."""
    sessions: List[SessionResponse]
    total: int


class RecommendationItem(BaseModel):
    """A scholarship recommendation from the agent."""
    scholarship_id: int
    scholarship_name: str
    match_score: int
    award_amount: Optional[float] = None
    deadline: Optional[str] = None
    reason: str  # Why this is recommended


class RecommendationsResponse(BaseModel):
    """Agent's scholarship recommendations."""
    recommendations: List[RecommendationItem]
    profile_completeness: int  # 0-100
    missing_profile_fields: List[str] = []


# Tool parameter schemas

class SearchScholarshipsParams(BaseModel):
    """Parameters for search_scholarships tool."""
    min_award: Optional[float] = None
    max_award: Optional[float] = None
    deadline_before: Optional[str] = None  # ISO date
    deadline_after: Optional[str] = None  # ISO date
    majors: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    limit: int = Field(default=10, le=50)
    sort_by: str = Field(default="deadline", pattern="^(deadline|award_amount|match_score)$")


class EvaluateMatchParams(BaseModel):
    """Parameters for evaluate_scholarship_match tool."""
    scholarship_id: int


class GetApplicationChecklistParams(BaseModel):
    """Parameters for get_application_checklist tool."""
    application_id: int


class CreateApplicationParams(BaseModel):
    """Parameters for create_application tool."""
    scholarship_id: int
    priority: int = Field(default=3, ge=1, le=5)
    notes: Optional[str] = None


class SuggestEssayMatchesParams(BaseModel):
    """Parameters for suggest_essay_matches tool."""
    scholarship_id: int


# Tool definitions for Gemini function calling

TOOL_DEFINITIONS = [
    {
        "name": "search_scholarships",
        "description": "Search and filter scholarships based on criteria. Returns matching scholarships with eligibility info. Use this when the user wants to find scholarships.",
        "parameters": {
            "type": "object",
            "properties": {
                "min_award": {
                    "type": "number",
                    "description": "Minimum award amount in dollars"
                },
                "max_award": {
                    "type": "number",
                    "description": "Maximum award amount in dollars"
                },
                "deadline_before": {
                    "type": "string",
                    "description": "Only show scholarships with deadline before this date (ISO format: YYYY-MM-DD)"
                },
                "deadline_after": {
                    "type": "string",
                    "description": "Only show scholarships with deadline after this date (ISO format: YYYY-MM-DD)"
                },
                "majors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by intended major/field of study"
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to search in scholarship name and description"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (default 10, max 50)"
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["deadline", "award_amount", "match_score"],
                    "description": "How to sort results"
                }
            }
        }
    },
    {
        "name": "get_scholarship_details",
        "description": "Get full details of a specific scholarship by ID. Use when user asks about a specific scholarship.",
        "parameters": {
            "type": "object",
            "properties": {
                "scholarship_id": {
                    "type": "integer",
                    "description": "The scholarship ID to get details for"
                }
            },
            "required": ["scholarship_id"]
        }
    },
    {
        "name": "evaluate_scholarship_match",
        "description": "Evaluate how well a scholarship matches the user's profile. Returns match score and detailed explanation. Use when user wants to know if they're a good fit.",
        "parameters": {
            "type": "object",
            "properties": {
                "scholarship_id": {
                    "type": "integer",
                    "description": "The scholarship ID to evaluate match for"
                }
            },
            "required": ["scholarship_id"]
        }
    },
    {
        "name": "get_user_profile",
        "description": "Retrieve the user's academic profile, achievements, and preferences. Use to understand what scholarships might fit.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_user_applications",
        "description": "Get list of user's scholarship applications with their status. Use when user asks about their applications.",
        "parameters": {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string",
                    "enum": ["saved", "in_progress", "submitted", "accepted", "rejected"],
                    "description": "Filter by application status (optional)"
                }
            }
        }
    },
    {
        "name": "get_user_essays",
        "description": "Retrieve user's existing essays, optionally filtered by category or tags. Use when helping with essay matching.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by essay category"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by tags"
                }
            }
        }
    },
    {
        "name": "get_user_documents",
        "description": "Retrieve user's uploaded documents. Use when checking what documents the user has available.",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_type": {
                    "type": "string",
                    "description": "Filter by document type (transcript, recommendation, resume, etc.)"
                }
            }
        }
    },
    {
        "name": "create_application",
        "description": "Create a new scholarship application for the user. Use when user wants to start applying to a scholarship.",
        "parameters": {
            "type": "object",
            "properties": {
                "scholarship_id": {
                    "type": "integer",
                    "description": "The scholarship ID to apply for"
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority level 1-5 (1=highest)"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes about this application"
                }
            },
            "required": ["scholarship_id"]
        }
    },
    {
        "name": "get_application_checklist",
        "description": "Get detailed checklist for a scholarship application showing required items and completion status.",
        "parameters": {
            "type": "object",
            "properties": {
                "application_id": {
                    "type": "integer",
                    "description": "The application ID to get checklist for"
                }
            },
            "required": ["application_id"]
        }
    },
    {
        "name": "check_missing_requirements",
        "description": "Identify missing documents and essays needed for an application. Use to help user understand what they still need.",
        "parameters": {
            "type": "object",
            "properties": {
                "application_id": {
                    "type": "integer",
                    "description": "The application ID to check"
                }
            },
            "required": ["application_id"]
        }
    },
    {
        "name": "suggest_essay_matches",
        "description": "Find existing user essays that could be adapted for a scholarship's essay prompts.",
        "parameters": {
            "type": "object",
            "properties": {
                "scholarship_id": {
                    "type": "integer",
                    "description": "The scholarship ID to match essays for"
                }
            },
            "required": ["scholarship_id"]
        }
    },
    {
        "name": "get_recommendations",
        "description": "Get personalized scholarship recommendations based on user profile. Use when user wants suggestions.",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recommendations (default 5)"
                },
                "exclude_applied": {
                    "type": "boolean",
                    "description": "Exclude scholarships user already applied to (default true)"
                }
            }
        }
    }
]
