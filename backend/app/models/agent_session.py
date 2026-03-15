from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AgentSession(Base):
    """Stores conversation state for the LLM agent."""
    __tablename__ = "agent_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True, nullable=False)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Conversation history - list of message objects
    # [{"role": "user"|"assistant"|"tool", "content": "...", "tool_calls": [...], "timestamp": "..."}]
    messages = Column(JSON, default=list)

    # Agent working context - tracks current state
    # {
    #   "current_scholarships": [id1, id2],  # IDs being discussed
    #   "user_intent": "find_scholarships",  # Current detected intent
    #   "active_filters": {"majors": ["CS"], "min_award": 1000},
    #   "workflow_state": "searching",  # Track multi-step workflows
    #   "last_tool_results": {}  # Cache of recent tool results
    # }
    context = Column(JSON, default=dict)

    # Usage tracking
    total_messages = Column(Integer, default=0)
    total_tool_calls = Column(Integer, default=0)
    total_tokens_used = Column(Integer, default=0)

    # Session state
    is_active = Column(Boolean, default=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="agent_sessions")
