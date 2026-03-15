import json
import logging
import google.generativeai as genai
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ParsedScholarship(BaseModel):
    """Structured scholarship data extracted by LLM."""
    gpa_minimum: Optional[float] = None
    grade_levels: Optional[list[str]] = None  # ["high_school_senior", "college_freshman", etc.]
    majors: Optional[list[str]] = None
    states: Optional[list[str]] = None  # US state codes
    citizenship_required: Optional[str] = None  # "us_citizen", "permanent_resident", etc.
    gender: Optional[str] = None
    ethnicity: Optional[list[str]] = None
    first_generation: Optional[bool] = None
    financial_need: Optional[bool] = None
    essay_required: Optional[bool] = None
    essay_prompts: Optional[list[dict]] = None  # [{"prompt": "...", "word_count": 500}]
    documents_required: Optional[list[str]] = None  # ["transcript", "recommendation_letter"]
    keywords: Optional[list[str]] = None  # For matching


class MatchExplanation(BaseModel):
    """Explanation of why a scholarship matches a user."""
    match_score: int  # 0-100
    summary: str  # 1-2 sentence summary
    strengths: list[str]  # Why user is a good fit
    considerations: list[str]  # Potential concerns or things to highlight
    tips: list[str]  # Application tips


class LLMService:
    def __init__(self):
        self.enabled = bool(settings.google_api_key)
        if self.enabled:
            genai.configure(api_key=settings.google_api_key)
            self.model = genai.GenerativeModel(settings.gemini_model)

    def is_available(self) -> bool:
        return self.enabled

    async def parse_scholarship(self, raw_text: str, name: str = "") -> ParsedScholarship:
        """Parse unstructured scholarship description into structured eligibility data."""
        if not self.enabled:
            raise RuntimeError("LLM service not configured. Set GOOGLE_API_KEY in environment.")

        prompt = f"""Analyze this scholarship description and extract structured eligibility requirements.
Return ONLY valid JSON matching this schema (use null for unknown fields):

{{
    "gpa_minimum": <number or null>,
    "grade_levels": <list of strings like "high_school_senior", "college_freshman", "college_sophomore", "college_junior", "college_senior", "graduate" or null>,
    "majors": <list of major/field names or null>,
    "states": <list of US state codes like "CA", "NY" or null if national>,
    "citizenship_required": <"us_citizen", "permanent_resident", "daca", "international", "any" or null>,
    "gender": <"male", "female", "any" or null>,
    "ethnicity": <list of ethnicities if restricted, or null>,
    "first_generation": <true if requires first-gen student, false if excludes, null if not mentioned>,
    "financial_need": <true if need-based, null otherwise>,
    "essay_required": <true/false>,
    "essay_prompts": <list of {{"prompt": "...", "word_count": number}} or null>,
    "documents_required": <list like ["transcript", "recommendation_letter", "resume", "financial_document"] or null>,
    "keywords": <list of 5-10 keywords for matching: field, interests, activities, etc.>
}}

Scholarship Name: {name}

Scholarship Description:
{raw_text}

JSON Output:"""

        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text)
            return ParsedScholarship(**data)
        except Exception as e:
            logger.exception(f"Error parsing scholarship: {e}")
            # Return empty parsed result on error
            return ParsedScholarship(keywords=[])

    async def generate_match_explanation(
        self,
        scholarship_name: str,
        scholarship_description: str,
        scholarship_requirements: dict,
        user_profile: dict
    ) -> MatchExplanation:
        """Generate explanation of why a scholarship matches a user's profile."""
        if not self.enabled:
            raise RuntimeError("LLM service not configured. Set GOOGLE_API_KEY in environment.")

        prompt = f"""Analyze how well this student matches this scholarship and provide guidance.

SCHOLARSHIP:
Name: {scholarship_name}
Description: {scholarship_description}
Requirements: {json.dumps(scholarship_requirements, indent=2)}

STUDENT PROFILE:
{json.dumps(user_profile, indent=2)}

Return ONLY valid JSON matching this schema:
{{
    "match_score": <0-100 score based on how well student meets requirements>,
    "summary": "<1-2 sentence summary of match quality>",
    "strengths": ["<strength 1>", "<strength 2>", ...],
    "considerations": ["<consideration 1>", ...],
    "tips": ["<application tip 1>", "<application tip 2>", ...]
}}

Consider:
- Hard requirements (GPA, grade level, citizenship) - if not met, score should be low
- Soft preferences (major, interests, activities) - boost score if aligned
- Financial need alignment if applicable
- Essay/application requirements vs student's experience

JSON Output:"""

        try:
            response = await self.model.generate_content_async(prompt)
            text = response.text.strip()

            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            data = json.loads(text)
            return MatchExplanation(**data)
        except Exception as e:
            logger.exception(f"Error generating match explanation: {e}")
            # Return default explanation on error
            return MatchExplanation(
                match_score=50,
                summary="Unable to generate detailed analysis. Please review requirements manually.",
                strengths=[],
                considerations=["Review scholarship requirements carefully"],
                tips=["Ensure you meet all eligibility criteria before applying"]
            )

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: str = ""
    ) -> Dict[str, Any]:
        """
        Chat with the model using function calling.

        Args:
            messages: Conversation history in Gemini format
            tools: List of tool definitions
            system_prompt: System instructions for the model

        Returns:
            Dict with 'text' (response text) and 'tool_calls' (list of function calls)
        """
        if not self.enabled:
            raise RuntimeError("LLM service not configured. Set GOOGLE_API_KEY in environment.")

        try:
            # Convert tool definitions to Gemini function declarations
            function_declarations = []
            for tool in tools:
                func_decl = {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                }
                function_declarations.append(func_decl)

            # Create model with tools
            model_with_tools = genai.GenerativeModel(
                model_name=settings.gemini_model,
                tools=[{"function_declarations": function_declarations}],
                system_instruction=system_prompt if system_prompt else None
            )

            # Start chat
            chat = model_with_tools.start_chat(history=messages[:-1] if len(messages) > 1 else [])

            # Send the last message
            last_message = messages[-1] if messages else {"parts": [{"text": "Hello"}]}
            response = await chat.send_message_async(last_message.get("parts", [{"text": ""}]))

            # Parse response
            result = {
                "text": "",
                "tool_calls": [],
                "finish_reason": "stop",
                "tokens_used": 0
            }

            # Extract token usage if available
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                result["tokens_used"] = getattr(usage, 'total_token_count', 0) or (
                    getattr(usage, 'prompt_token_count', 0) +
                    getattr(usage, 'candidates_token_count', 0)
                )

            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if hasattr(part, 'text') and part.text:
                        result["text"] += part.text
                    elif hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        # Convert function call args to dict
                        args = {}
                        if fc.args:
                            for key, value in fc.args.items():
                                args[key] = value

                        result["tool_calls"].append({
                            "id": f"call_{fc.name}_{len(result['tool_calls'])}",
                            "name": fc.name,
                            "parameters": args
                        })
                        result["finish_reason"] = "tool_calls"

            logger.info(f"LLM response: text={len(result['text'])} chars, tool_calls={len(result['tool_calls'])}, tokens={result['tokens_used']}")
            return result

        except Exception as e:
            logger.exception(f"Error in chat_with_tools: {e}")
            raise

    async def simple_chat(self, message: str, system_prompt: str = "") -> str:
        """Simple chat without tools - for basic queries."""
        if not self.enabled:
            raise RuntimeError("LLM service not configured. Set GOOGLE_API_KEY in environment.")

        try:
            model = genai.GenerativeModel(
                model_name=settings.gemini_model,
                system_instruction=system_prompt if system_prompt else None
            )
            response = await model.generate_content_async(message)
            return response.text
        except Exception as e:
            logger.exception(f"Error in simple_chat: {e}")
            raise


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
