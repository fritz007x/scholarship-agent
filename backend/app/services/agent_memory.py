"""
Agent Memory Management - Handles conversation history and context.
"""
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.agent_session import AgentSession
from app.schemas.agent import Message, MessageRole, ToolCall, ToolResult, AgentContext

logger = logging.getLogger(__name__)

# Maximum messages to keep in context window
MAX_CONTEXT_MESSAGES = 20


class ConversationMemory:
    """Manages conversation history and agent context."""

    def __init__(self, db: Session):
        self.db = db

    def create_session(self, user_id: int) -> AgentSession:
        """Create a new agent session."""
        session = AgentSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            messages=[],
            context={},
            total_messages=0,
            total_tool_calls=0,
            total_tokens_used=0,
            is_active=True
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        logger.info(f"Created new session {session.session_id} for user {user_id}")
        return session

    def get_session(self, session_id: str, user_id: int) -> Optional[AgentSession]:
        """Get an existing session by ID."""
        return self.db.query(AgentSession).filter(
            AgentSession.session_id == session_id,
            AgentSession.user_id == user_id,
            AgentSession.is_active == True
        ).first()

    def get_or_create_session(self, session_id: Optional[str], user_id: int) -> AgentSession:
        """Get existing session or create a new one."""
        if session_id:
            session = self.get_session(session_id, user_id)
            if session:
                return session
            logger.warning(f"Session {session_id} not found, creating new session")

        return self.create_session(user_id)

    def add_user_message(self, session: AgentSession, content: str) -> None:
        """Add a user message to the session with row-level locking."""
        # Lock the row to prevent race conditions
        locked_session = self.db.query(AgentSession).filter(
            AgentSession.id == session.id
        ).with_for_update().first()

        if not locked_session:
            return

        messages = list(locked_session.messages or [])
        messages.append({
            "role": MessageRole.USER.value,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        locked_session.messages = messages
        locked_session.total_messages = len(messages)
        self.db.commit()
        # Refresh the original session object
        self.db.refresh(session)

    def add_assistant_message(
        self,
        session: AgentSession,
        content: str,
        tool_calls: Optional[List[Dict]] = None
    ) -> None:
        """Add an assistant message to the session with row-level locking."""
        # Lock the row to prevent race conditions
        locked_session = self.db.query(AgentSession).filter(
            AgentSession.id == session.id
        ).with_for_update().first()

        if not locked_session:
            return

        messages = list(locked_session.messages or [])
        message = {
            "role": MessageRole.ASSISTANT.value,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        if tool_calls:
            message["tool_calls"] = tool_calls
            locked_session.total_tool_calls += len(tool_calls)

        messages.append(message)
        locked_session.messages = messages
        locked_session.total_messages = len(messages)
        self.db.commit()
        # Refresh the original session object
        self.db.refresh(session)

    def add_tool_result(
        self,
        session: AgentSession,
        tool_call_id: str,
        tool_name: str,
        result: Dict[str, Any]
    ) -> None:
        """Add a tool execution result to the session with row-level locking."""
        # Lock the row to prevent race conditions
        locked_session = self.db.query(AgentSession).filter(
            AgentSession.id == session.id
        ).with_for_update().first()

        if not locked_session:
            return

        messages = list(locked_session.messages or [])
        messages.append({
            "role": MessageRole.TOOL.value,
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "content": str(result),
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        })
        locked_session.messages = messages
        self.db.commit()
        # Refresh the original session object
        self.db.refresh(session)

    def get_context_window(
        self,
        session: AgentSession,
        max_messages: int = MAX_CONTEXT_MESSAGES
    ) -> List[Dict[str, Any]]:
        """Get recent messages for LLM context."""
        messages = session.messages or []

        # Take the most recent messages
        if len(messages) > max_messages:
            # Always keep the first message for context
            return [messages[0]] + messages[-(max_messages - 1):]

        return messages

    def update_context(
        self,
        session: AgentSession,
        updates: Dict[str, Any]
    ) -> None:
        """Update the agent's working context."""
        context = session.context or {}
        context.update(updates)
        session.context = context
        self.db.commit()

    def get_context(self, session: AgentSession) -> AgentContext:
        """Get the current agent context."""
        ctx = session.context or {}
        return AgentContext(
            current_scholarships=ctx.get("current_scholarships", []),
            user_intent=ctx.get("user_intent"),
            active_filters=ctx.get("active_filters", {}),
            workflow_state=ctx.get("workflow_state"),
            last_tool_results=ctx.get("last_tool_results", {})
        )

    def track_mentioned_scholarships(
        self,
        session: AgentSession,
        scholarship_ids: List[int]
    ) -> None:
        """Track scholarship IDs mentioned in conversation."""
        context = session.context or {}
        current = set(context.get("current_scholarships", []))
        current.update(scholarship_ids)
        # Keep only the 10 most recent
        context["current_scholarships"] = list(current)[-10:]
        session.context = context
        self.db.commit()

    def set_user_intent(self, session: AgentSession, intent: str) -> None:
        """Set the detected user intent."""
        self.update_context(session, {"user_intent": intent})

    def archive_session(self, session: AgentSession) -> None:
        """Archive a session (mark as inactive)."""
        session.is_active = False
        self.db.commit()
        logger.info(f"Archived session {session.session_id}")

    def get_user_sessions(
        self,
        user_id: int,
        include_archived: bool = False,
        limit: int = 10
    ) -> List[AgentSession]:
        """Get user's agent sessions."""
        query = self.db.query(AgentSession).filter(AgentSession.user_id == user_id)

        if not include_archived:
            query = query.filter(AgentSession.is_active == True)

        return query.order_by(AgentSession.last_activity.desc()).limit(limit).all()

    def update_token_usage(self, session: AgentSession, tokens: int) -> None:
        """Update the token usage counter."""
        session.total_tokens_used += tokens
        self.db.commit()

    def format_messages_for_llm(
        self,
        session: AgentSession,
        system_prompt: str
    ) -> List[Dict[str, Any]]:
        """Format conversation history for the LLM API."""
        formatted = []

        # Add system message
        formatted.append({
            "role": "user",
            "parts": [{"text": f"[SYSTEM]\n{system_prompt}"}]
        })
        formatted.append({
            "role": "model",
            "parts": [{"text": "I understand. I'm ready to help with scholarship search and applications."}]
        })

        # Add conversation history
        messages = self.get_context_window(session)

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == MessageRole.USER.value:
                formatted.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == MessageRole.ASSISTANT.value:
                parts = [{"text": content}] if content else []
                # Tool calls are handled separately by Gemini
                formatted.append({
                    "role": "model",
                    "parts": parts if parts else [{"text": "I'll help you with that."}]
                })
            elif role == MessageRole.TOOL.value:
                # Tool results are passed back as function responses
                tool_name = msg.get("tool_name", "unknown")
                result = msg.get("result", {})
                formatted.append({
                    "role": "user",
                    "parts": [{"text": f"[Tool Result - {tool_name}]\n{result}"}]
                })

        return formatted
