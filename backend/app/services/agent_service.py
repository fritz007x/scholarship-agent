"""
Agent Service - Core orchestration for the ReAct agent loop.

Implements the Reasoning + Acting pattern:
1. Receive user message
2. Call LLM with tools available
3. If LLM wants to use a tool -> execute it, add result, loop back
4. If LLM gives final response -> return to user
"""
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.services.llm import get_llm_service
from app.services.agent_tools import AgentToolRegistry
from app.services.agent_memory import ConversationMemory
from app.models.agent_session import AgentSession
from app.schemas.agent import (
    ChatResponse, ToolCall, TOOL_DEFINITIONS,
    RecommendationItem, RecommendationsResponse
)
from app.utils.agent_prompts import AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Safety limits
MAX_REACT_ITERATIONS = 5  # Maximum tool calls per user message
MAX_TOKENS_PER_SESSION = 100000  # Token budget per session


class AgentServiceError(Exception):
    """Raised when agent encounters an error."""
    pass


class AgentService:
    """
    Main agent orchestration service.

    Handles the ReAct loop:
    - User sends message
    - Agent reasons about what to do
    - Agent may call tools
    - Agent provides response
    """

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.llm_service = get_llm_service()
        self.memory = ConversationMemory(db)
        self.tools = AgentToolRegistry(db, user_id)

    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Process a user message and return agent response.

        Args:
            message: User's message
            session_id: Optional session ID to continue conversation

        Returns:
            ChatResponse with agent's response and metadata
        """
        # Get or create session
        session = self.memory.get_or_create_session(session_id, self.user_id)

        # Check token budget
        if session.total_tokens_used > MAX_TOKENS_PER_SESSION:
            logger.warning(f"Session {session.session_id} exceeded token budget")
            return ChatResponse(
                session_id=session.session_id,
                message="This conversation has reached its limit. Please start a new conversation.",
                tool_calls=None,
                scholarships_mentioned=[],
                suggested_actions=["Start new conversation"]
            )

        # Add user message to history
        self.memory.add_user_message(session, message)

        # Run ReAct loop
        try:
            response_text, tool_calls_made = await self._react_loop(session)
        except Exception as e:
            logger.exception(f"ReAct loop failed: {e}")
            response_text = "I encountered an error processing your request. Please try again."
            tool_calls_made = []

        # Extract mentioned scholarships from context
        context = self.memory.get_context(session)
        scholarships_mentioned = context.current_scholarships

        # Generate suggested actions based on response
        suggested_actions = self._generate_suggested_actions(response_text, tool_calls_made)

        # Add assistant response to history
        self.memory.add_assistant_message(
            session,
            response_text,
            [{"id": tc.id, "name": tc.name, "parameters": tc.parameters}
             for tc in tool_calls_made] if tool_calls_made else None
        )

        return ChatResponse(
            session_id=session.session_id,
            message=response_text,
            tool_calls=tool_calls_made if tool_calls_made else None,
            scholarships_mentioned=scholarships_mentioned,
            suggested_actions=suggested_actions
        )

    async def _react_loop(self, session: AgentSession) -> tuple[str, List[ToolCall]]:
        """
        Execute the ReAct reasoning loop.

        Returns:
            Tuple of (final_response_text, list_of_tool_calls_made)
        """
        all_tool_calls = []
        iteration = 0

        while iteration < MAX_REACT_ITERATIONS:
            iteration += 1
            logger.info(f"ReAct iteration {iteration} for session {session.session_id}")

            # Format messages for LLM
            messages = self._format_messages_for_gemini(session)

            # Call LLM with tools
            try:
                llm_response = await self.llm_service.chat_with_tools(
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    system_prompt=AGENT_SYSTEM_PROMPT
                )
                # Track token usage
                tokens_used = llm_response.get("tokens_used", 0)
                if tokens_used > 0:
                    self.memory.update_token_usage(session, tokens_used)
            except Exception as e:
                logger.exception(f"LLM call failed: {e}")
                return "I'm having trouble connecting to my language model. Please try again.", all_tool_calls

            # Check if LLM wants to call tools
            if llm_response.get("tool_calls"):
                tool_calls = llm_response["tool_calls"]
                logger.info(f"LLM wants to call {len(tool_calls)} tool(s)")

                for tc in tool_calls:
                    tool_call = ToolCall(
                        id=tc["id"],
                        name=tc["name"],
                        parameters=tc.get("parameters", {})
                    )
                    all_tool_calls.append(tool_call)

                    # Execute the tool
                    result = await self.tools.execute_tool(
                        tool_call.name,
                        tool_call.parameters
                    )

                    # Track scholarship IDs mentioned in results
                    self._track_scholarships_from_result(session, result)

                    # Add tool result to memory
                    self.memory.add_tool_result(
                        session,
                        tool_call.id,
                        tool_call.name,
                        result
                    )

                # Continue loop to let LLM process tool results
                continue

            # LLM gave a final response
            response_text = llm_response.get("text", "")
            if response_text:
                return response_text, all_tool_calls

            # Edge case: no text and no tool calls
            return "I'm not sure how to help with that. Could you rephrase your question?", all_tool_calls

        # Max iterations reached
        logger.warning(f"Max iterations ({MAX_REACT_ITERATIONS}) reached for session {session.session_id}")
        return "I've done extensive research but need to provide you with what I've found so far. " + \
               (llm_response.get("text", "Please let me know if you need more specific information.")), all_tool_calls

    def _format_messages_for_gemini(self, session: AgentSession) -> List[Dict[str, Any]]:
        """Format conversation history for Gemini API."""
        formatted = []
        messages = self.memory.get_context_window(session)

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")

            if role == "user":
                formatted.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == "assistant":
                parts = []
                if content:
                    parts.append({"text": content})
                if not parts:
                    parts.append({"text": "I'll help you with that."})
                formatted.append({
                    "role": "model",
                    "parts": parts
                })
            elif role == "tool":
                # Include tool results as user messages with clear formatting
                tool_name = msg.get("tool_name", "unknown")
                result = msg.get("result", {})
                formatted.append({
                    "role": "user",
                    "parts": [{"text": f"[Tool Result: {tool_name}]\n{self._format_tool_result(result)}"}]
                })

        return formatted

    def _format_tool_result(self, result: Dict[str, Any]) -> str:
        """Format tool result for inclusion in conversation."""
        if not result.get("success"):
            return f"Error: {result.get('error', 'Unknown error')}"

        data = result.get("data", {})

        # Format based on common result patterns
        if "scholarships" in data:
            scholarships = data["scholarships"]
            if not scholarships:
                return "No scholarships found matching the criteria."
            lines = [f"Found {len(scholarships)} scholarship(s):"]
            for s in scholarships[:5]:  # Limit to 5 for context
                lines.append(f"- {s.get('name')} (ID: {s.get('id')}): {s.get('award_amount', 'Varies')}, Deadline: {s.get('deadline', 'N/A')}")
            if len(scholarships) > 5:
                lines.append(f"  ... and {len(scholarships) - 5} more")
            return "\n".join(lines)

        if "applications" in data:
            apps = data["applications"]
            if not apps:
                return "No applications found."
            lines = [f"Found {len(apps)} application(s):"]
            for a in apps[:5]:
                lines.append(f"- {a.get('scholarship_name')} (Status: {a.get('status')}, Progress: {a.get('progress')})")
            return "\n".join(lines)

        if "recommendations" in data:
            recs = data["recommendations"]
            if not recs:
                return "No recommendations available. Complete your profile for better results."
            lines = ["Top recommendations:"]
            for r in recs:
                lines.append(f"- {r.get('name')} (Match: {r.get('match_score')}%): {r.get('reason')}")
            return "\n".join(lines)

        if "match_score" in data:
            return f"Match Score: {data.get('match_score')}%\n" \
                   f"Summary: {data.get('summary')}\n" \
                   f"Strengths: {', '.join(data.get('strengths', []))}\n" \
                   f"Considerations: {', '.join(data.get('considerations', []))}"

        # Default: return JSON-like summary
        import json
        return json.dumps(data, indent=2, default=str)[:1500]  # Limit length

    def _track_scholarships_from_result(self, session: AgentSession, result: Dict[str, Any]) -> None:
        """Extract and track scholarship IDs from tool results."""
        if not result.get("success"):
            return

        data = result.get("data", {})
        scholarship_ids = []

        # Check various result patterns
        if "scholarships" in data:
            scholarship_ids.extend(s.get("id") for s in data["scholarships"] if s.get("id"))
        if "scholarship_id" in data:
            scholarship_ids.append(data["scholarship_id"])
        if "recommendations" in data:
            scholarship_ids.extend(r.get("scholarship_id") for r in data["recommendations"] if r.get("scholarship_id"))

        if scholarship_ids:
            self.memory.track_mentioned_scholarships(session, scholarship_ids)

    def _generate_suggested_actions(
        self,
        response_text: str,
        tool_calls: List[ToolCall]
    ) -> List[str]:
        """Generate suggested follow-up actions based on conversation."""
        suggestions = []

        # Based on tools used
        tool_names = [tc.name for tc in tool_calls]

        if "search_scholarships" in tool_names:
            suggestions.append("Get match analysis for a scholarship")
            suggestions.append("Start an application")

        if "evaluate_scholarship_match" in tool_names:
            suggestions.append("View application requirements")
            suggestions.append("Find similar scholarships")

        if "get_user_applications" in tool_names:
            suggestions.append("Check missing requirements")
            suggestions.append("Find essay matches")

        if "get_recommendations" in tool_names:
            suggestions.append("Get details on a recommended scholarship")

        # Default suggestions
        if not suggestions:
            suggestions = [
                "Search for scholarships",
                "Get personalized recommendations",
                "Check my applications"
            ]

        return suggestions[:3]  # Limit to 3 suggestions

    async def get_recommendations(
        self,
        limit: int = 5,
        exclude_applied: bool = True
    ) -> RecommendationsResponse:
        """Get direct recommendations without chat."""
        result = await self.tools.execute_tool(
            "get_recommendations",
            {"limit": limit, "exclude_applied": exclude_applied}
        )

        if not result.get("success"):
            return RecommendationsResponse(
                recommendations=[],
                profile_completeness=0,
                missing_profile_fields=["Unable to load recommendations"]
            )

        data = result["data"]
        recommendations = [
            RecommendationItem(
                scholarship_id=r["scholarship_id"],
                scholarship_name=r["name"],
                match_score=r["match_score"],
                award_amount=float(r["award_amount"].replace("$", "").replace(",", "")) if r.get("award_amount") and r["award_amount"] != "Varies" else None,
                deadline=r.get("deadline"),
                reason=r["reason"]
            )
            for r in data.get("recommendations", [])
        ]

        return RecommendationsResponse(
            recommendations=recommendations,
            profile_completeness=data.get("profile_completeness", 0),
            missing_profile_fields=[]
        )

    def get_session_history(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session details and history."""
        session = self.memory.get_session(session_id, self.user_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "last_activity": session.last_activity.isoformat() if session.last_activity else None,
            "total_messages": session.total_messages,
            "total_tool_calls": session.total_tool_calls,
            "messages": session.messages or [],
            "context": session.context or {}
        }

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List user's agent sessions."""
        sessions = self.memory.get_user_sessions(self.user_id, limit=limit)
        return [
            {
                "session_id": s.session_id,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "last_activity": s.last_activity.isoformat() if s.last_activity else None,
                "total_messages": s.total_messages,
                "is_active": s.is_active
            }
            for s in sessions
        ]

    def archive_session(self, session_id: str) -> bool:
        """Archive a session."""
        session = self.memory.get_session(session_id, self.user_id)
        if not session:
            return False
        self.memory.archive_session(session)
        return True
