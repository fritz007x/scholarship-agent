"""
Agent Tool Registry - Implements all tools the LLM agent can use.

Each tool wraps existing database operations and services,
providing structured access for the agent.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models import Scholarship, Application, Essay, Document, UserProfile
from app.services.profile_mapper import ProfileMapper
from app.services.llm import get_llm_service
from app.services.checklist import ChecklistGenerator
from app.schemas.agent import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)


class ToolExecutionError(Exception):
    """Raised when a tool fails to execute."""
    pass


class AgentToolRegistry:
    """Registry and executor for agent tools."""

    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.llm_service = get_llm_service()

    @staticmethod
    def get_tool_definitions() -> List[Dict]:
        """Return Gemini-compatible function definitions."""
        return TOOL_DEFINITIONS

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return results."""
        logger.info(f"Executing tool: {tool_name} with params: {parameters}")

        tool_method = getattr(self, f"_tool_{tool_name}", None)
        if not tool_method:
            logger.error(f"Unknown tool: {tool_name}")
            return {"success": False, "error": f"Unknown tool: {tool_name}"}

        try:
            result = await tool_method(**parameters)
            return {"success": True, "data": result}
        except ToolExecutionError as e:
            logger.warning(f"Tool {tool_name} execution error: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.exception(f"Tool {tool_name} failed unexpectedly")
            return {"success": False, "error": f"Tool execution failed: {str(e)}"}

    # ===================
    # Search & Discovery
    # ===================

    async def _tool_search_scholarships(
        self,
        min_award: Optional[float] = None,
        max_award: Optional[float] = None,
        deadline_before: Optional[str] = None,
        deadline_after: Optional[str] = None,
        majors: Optional[List[str]] = None,
        keywords: Optional[List[str]] = None,
        limit: int = 10,
        sort_by: str = "deadline"
    ) -> Dict[str, Any]:
        """Search and filter scholarships."""
        query = self.db.query(Scholarship)

        # Award amount filters
        if min_award is not None:
            query = query.filter(
                or_(
                    Scholarship.award_amount >= min_award,
                    Scholarship.award_amount_max >= min_award
                )
            )
        if max_award is not None:
            query = query.filter(
                or_(
                    Scholarship.award_amount <= max_award,
                    Scholarship.award_amount_min <= max_award,
                    Scholarship.award_amount.is_(None)
                )
            )

        # Deadline filters
        if deadline_before:
            try:
                before_date = datetime.fromisoformat(deadline_before).date()
                query = query.filter(Scholarship.deadline <= before_date)
            except ValueError:
                pass

        if deadline_after:
            try:
                after_date = datetime.fromisoformat(deadline_after).date()
                query = query.filter(Scholarship.deadline >= after_date)
            except ValueError:
                pass

        # Filter by active deadlines (not passed)
        today = date.today()
        query = query.filter(
            or_(Scholarship.deadline.is_(None), Scholarship.deadline >= today)
        )

        # Keyword search in name, description, and keywords JSON
        if keywords:
            keyword_conditions = []
            for kw in keywords:
                # Escape SQL LIKE wildcards to prevent injection
                escaped_kw = kw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                keyword_conditions.append(Scholarship.name.ilike(f"%{escaped_kw}%", escape="\\"))
                keyword_conditions.append(Scholarship.description.ilike(f"%{escaped_kw}%", escape="\\"))
            query = query.filter(or_(*keyword_conditions))

        # Sorting
        if sort_by == "deadline":
            query = query.order_by(Scholarship.deadline.asc().nullslast())
        elif sort_by == "award_amount":
            query = query.order_by(Scholarship.award_amount.desc().nullslast())

        # Limit results
        limit = min(limit, 50)
        scholarships = query.limit(limit).all()

        # Format results
        results = []
        for s in scholarships:
            amount = s.award_amount
            if not amount and s.award_amount_min and s.award_amount_max:
                amount = f"${s.award_amount_min:,.0f} - ${s.award_amount_max:,.0f}"
            elif amount:
                amount = f"${amount:,.0f}"
            else:
                amount = "Varies"

            results.append({
                "id": s.id,
                "name": s.name,
                "provider": s.provider,
                "award_amount": amount,
                "deadline": s.deadline.isoformat() if s.deadline else None,
                "description": (s.description[:200] + "...") if s.description and len(s.description) > 200 else s.description,
                "renewable": s.is_renewable,
                "keywords": s.keywords or []
            })

        return {
            "scholarships": results,
            "count": len(results),
            "filters_applied": {
                "min_award": min_award,
                "max_award": max_award,
                "keywords": keywords,
                "deadline_range": f"{deadline_after or 'any'} to {deadline_before or 'any'}"
            }
        }

    async def _tool_get_scholarship_details(self, scholarship_id: int) -> Dict[str, Any]:
        """Get full details of a specific scholarship."""
        scholarship = self.db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()

        if not scholarship:
            raise ToolExecutionError(f"Scholarship {scholarship_id} not found")

        # Check if user has already applied
        existing_app = self.db.query(Application).filter(
            Application.user_id == self.user_id,
            Application.scholarship_id == scholarship_id
        ).first()

        amount = scholarship.award_amount
        if not amount and scholarship.award_amount_min and scholarship.award_amount_max:
            amount = f"${scholarship.award_amount_min:,.0f} - ${scholarship.award_amount_max:,.0f}"
        elif amount:
            amount = f"${amount:,.0f}"
        else:
            amount = "Varies"

        return {
            "id": scholarship.id,
            "name": scholarship.name,
            "provider": scholarship.provider,
            "description": scholarship.description,
            "url": scholarship.url,
            "award_amount": amount,
            "num_awards": scholarship.number_of_awards,
            "renewable": scholarship.is_renewable,
            "deadline": scholarship.deadline.isoformat() if scholarship.deadline else None,
            "eligibility": scholarship.eligibility or {},
            "requirements": scholarship.application_requirements or {},
            "keywords": scholarship.keywords or [],
            "categories": scholarship.categories or [],
            "user_has_applied": existing_app is not None,
            "user_application_id": existing_app.id if existing_app else None,
            "user_application_status": existing_app.status if existing_app else None
        }

    async def _tool_evaluate_scholarship_match(self, scholarship_id: int) -> Dict[str, Any]:
        """Evaluate how well a scholarship matches the user's profile."""
        scholarship = self.db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()
        if not scholarship:
            raise ToolExecutionError(f"Scholarship {scholarship_id} not found")

        # Get user profile
        profile_mapper = ProfileMapper(self.db)
        profile_data = profile_mapper.get_profile_for_matching(self.user_id)

        if not profile_data:
            profile_data = {}

        # Use LLM to generate match explanation
        if not self.llm_service.is_available() or not profile_data:
            # Fallback: basic rule-based matching
            return self._basic_match_evaluation(scholarship, profile_data)

        explanation = await self.llm_service.generate_match_explanation(
            scholarship_name=scholarship.name,
            scholarship_description=scholarship.description or "",
            scholarship_requirements=scholarship.eligibility or {},
            user_profile=profile_data
        )

        return {
            "scholarship_id": scholarship_id,
            "scholarship_name": scholarship.name,
            "match_score": explanation.match_score,
            "summary": explanation.summary,
            "strengths": explanation.strengths,
            "considerations": explanation.considerations,
            "tips": explanation.tips
        }

    def _basic_match_evaluation(self, scholarship: Scholarship, profile: Dict) -> Dict[str, Any]:
        """Fallback matching when LLM is unavailable."""
        score = 70  # Base score
        strengths = []
        considerations = []

        eligibility = scholarship.eligibility or {}

        # GPA check
        if eligibility.get("gpa_minimum") and profile.get("gpa"):
            if profile["gpa"] >= eligibility["gpa_minimum"]:
                score += 10
                strengths.append(f"Your GPA ({profile['gpa']}) meets the minimum requirement ({eligibility['gpa_minimum']})")
            else:
                score -= 20
                considerations.append(f"Your GPA ({profile['gpa']}) is below the minimum ({eligibility['gpa_minimum']})")

        # Major check
        if eligibility.get("majors") and profile.get("intended_major"):
            if any(m.lower() in profile["intended_major"].lower() for m in eligibility["majors"]):
                score += 10
                strengths.append("Your intended major aligns with scholarship requirements")

        # State check
        if eligibility.get("states") and profile.get("state"):
            if profile["state"] in eligibility["states"]:
                score += 5
                strengths.append("You're in an eligible state")
            else:
                score -= 15
                considerations.append(f"This scholarship may be limited to specific states")

        score = max(0, min(100, score))

        return {
            "scholarship_id": scholarship.id,
            "scholarship_name": scholarship.name,
            "match_score": score,
            "summary": "Basic eligibility check completed (AI analysis unavailable)",
            "strengths": strengths,
            "considerations": considerations,
            "tips": ["Review full eligibility requirements carefully"]
        }

    # ===================
    # Profile & User Data
    # ===================

    async def _tool_get_user_profile(self) -> Dict[str, Any]:
        """Retrieve user's profile data."""
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == self.user_id).first()

        if not profile:
            return {
                "profile_exists": False,
                "message": "Profile not created yet. You can still search for scholarships, but completing your profile will improve match accuracy."
            }

        # Calculate completeness
        fields = [
            profile.first_name, profile.last_name, profile.current_school,
            profile.graduation_year, profile.gpa, profile.intended_major
        ]
        filled = sum(1 for f in fields if f)
        completeness = int((filled / len(fields)) * 100)

        return {
            "profile_exists": True,
            "completeness": completeness,
            "name": f"{profile.first_name or ''} {profile.last_name or ''}".strip(),
            "school": profile.current_school,
            "graduation_year": profile.graduation_year,
            "gpa": profile.gpa,
            "gpa_scale": profile.gpa_scale,
            "intended_major": profile.intended_major,
            "intended_minor": profile.intended_minor,
            "state": profile.state,
            "citizenship_status": profile.citizenship_status,
            "first_generation": profile.first_generation,
            "extracurriculars_count": len(profile.extracurriculars or []),
            "awards_count": len(profile.awards or []),
            "volunteer_hours": sum(v.get("hours", 0) for v in (profile.volunteer_work or [])),
            "has_financial_info": profile.estimated_efc is not None or profile.household_income_range is not None
        }

    async def _tool_get_user_applications(
        self,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get user's scholarship applications."""
        query = self.db.query(Application).filter(Application.user_id == self.user_id)

        if status_filter:
            query = query.filter(Application.status == status_filter)

        applications = query.order_by(Application.deadline.asc().nullslast()).all()

        results = []
        for app in applications:
            scholarship = self.db.query(Scholarship).filter(Scholarship.id == app.scholarship_id).first()
            results.append({
                "id": app.id,
                "scholarship_id": app.scholarship_id,
                "scholarship_name": scholarship.name if scholarship else "Unknown",
                "status": app.status,
                "deadline": app.deadline.isoformat() if app.deadline else None,
                "priority": app.priority,
                "progress": f"{app.checklist_completed}/{app.checklist_total}" if app.checklist_total > 0 else "N/A",
                "progress_percent": int((app.checklist_completed / app.checklist_total) * 100) if app.checklist_total > 0 else 0
            })

        # Group by status
        by_status = {}
        for app in results:
            status = app["status"]
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(app)

        return {
            "applications": results,
            "total": len(results),
            "by_status": by_status,
            "upcoming_deadlines": [a for a in results if a["deadline"] and a["status"] in ["saved", "in_progress"]][:5]
        }

    async def _tool_get_user_essays(
        self,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Retrieve user's essays."""
        query = self.db.query(Essay).filter(Essay.user_id == self.user_id)

        if category:
            query = query.filter(Essay.prompt_category == category)

        essays = query.order_by(Essay.updated_at.desc()).all()

        # Filter by tags if provided (JSON contains)
        if tags:
            essays = [e for e in essays if e.tags and any(t in e.tags for t in tags)]

        results = []
        for essay in essays:
            results.append({
                "id": essay.id,
                "title": essay.title,
                "word_count": essay.word_count,
                "category": essay.prompt_category,
                "tags": essay.tags or [],
                "is_template": essay.is_template,
                "used_count": len(essay.used_in_applications or []),
                "preview": (essay.content[:150] + "...") if essay.content and len(essay.content) > 150 else essay.content
            })

        # Group by category
        by_category = {}
        for essay in results:
            cat = essay["category"] or "uncategorized"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(essay)

        return {
            "essays": results,
            "total": len(results),
            "by_category": by_category
        }

    async def _tool_get_user_documents(
        self,
        doc_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Retrieve user's documents."""
        query = self.db.query(Document).filter(Document.user_id == self.user_id)

        if doc_type:
            query = query.filter(Document.document_type == doc_type)

        documents = query.order_by(Document.created_at.desc()).all()

        results = []
        for doc in documents:
            results.append({
                "id": doc.id,
                "title": doc.title or doc.original_filename,
                "type": doc.document_type,
                "filename": doc.original_filename,
                "uploaded": doc.created_at.isoformat() if doc.created_at else None,
                "used_count": len(doc.used_in_applications or [])
            })

        # Group by type
        by_type = {}
        for doc in results:
            dtype = doc["type"] or "other"
            if dtype not in by_type:
                by_type[dtype] = []
            by_type[dtype].append(doc)

        return {
            "documents": results,
            "total": len(results),
            "by_type": by_type
        }

    # ===================
    # Application Management
    # ===================

    async def _tool_create_application(
        self,
        scholarship_id: int,
        priority: int = 3,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new scholarship application."""
        # Check if scholarship exists
        scholarship = self.db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()
        if not scholarship:
            raise ToolExecutionError(f"Scholarship {scholarship_id} not found")

        # Check for existing application
        existing = self.db.query(Application).filter(
            Application.user_id == self.user_id,
            Application.scholarship_id == scholarship_id
        ).first()

        if existing:
            return {
                "created": False,
                "message": "You already have an application for this scholarship",
                "application_id": existing.id,
                "status": existing.status
            }

        # Generate checklist
        checklist_gen = ChecklistGenerator()
        checklist = checklist_gen.generate_checklist(scholarship)

        # Get pre-filled data from profile
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == self.user_id).first()
        prefilled = ProfileMapper.generate_prefilled_data(profile) if profile else {}

        # Create application
        application = Application(
            user_id=self.user_id,
            scholarship_id=scholarship_id,
            status="saved",
            deadline=scholarship.deadline,
            priority=priority,
            notes=notes,
            checklist=checklist,
            checklist_total=len(checklist),
            checklist_completed=0,
            prefilled_data=prefilled
        )

        self.db.add(application)
        self.db.commit()
        self.db.refresh(application)

        return {
            "created": True,
            "application_id": application.id,
            "scholarship_name": scholarship.name,
            "deadline": scholarship.deadline.isoformat() if scholarship.deadline else None,
            "checklist_items": len(checklist),
            "message": f"Application created for {scholarship.name}"
        }

    async def _tool_get_application_checklist(self, application_id: int) -> Dict[str, Any]:
        """Get detailed checklist for an application."""
        application = self.db.query(Application).filter(
            Application.id == application_id,
            Application.user_id == self.user_id
        ).first()

        if not application:
            raise ToolExecutionError(f"Application {application_id} not found")

        scholarship = self.db.query(Scholarship).filter(Scholarship.id == application.scholarship_id).first()

        checklist = application.checklist or []

        # Group by type
        by_type = {}
        for item in checklist:
            item_type = item.get("type", "other")
            if item_type not in by_type:
                by_type[item_type] = []
            by_type[item_type].append(item)

        completed = [item for item in checklist if item.get("completed")]
        pending = [item for item in checklist if not item.get("completed")]

        return {
            "application_id": application_id,
            "scholarship_name": scholarship.name if scholarship else "Unknown",
            "status": application.status,
            "deadline": application.deadline.isoformat() if application.deadline else None,
            "checklist": checklist,
            "by_type": by_type,
            "completed_count": len(completed),
            "pending_count": len(pending),
            "progress_percent": int((len(completed) / len(checklist)) * 100) if checklist else 0,
            "completed_items": [c["description"] for c in completed],
            "pending_items": [p["description"] for p in pending]
        }

    async def _tool_check_missing_requirements(self, application_id: int) -> Dict[str, Any]:
        """Identify missing documents and essays for an application."""
        application = self.db.query(Application).filter(
            Application.id == application_id,
            Application.user_id == self.user_id
        ).first()

        if not application:
            raise ToolExecutionError(f"Application {application_id} not found")

        scholarship = self.db.query(Scholarship).filter(Scholarship.id == application.scholarship_id).first()
        checklist = application.checklist or []

        # Get user's available resources
        user_essays = self.db.query(Essay).filter(Essay.user_id == self.user_id).all()
        user_docs = self.db.query(Document).filter(Document.user_id == self.user_id).all()

        missing_essays = []
        missing_documents = []
        missing_other = []

        for item in checklist:
            if item.get("completed"):
                continue

            item_type = item.get("type", "other")
            desc = item.get("description", "")

            if item_type == "essay":
                missing_essays.append({
                    "id": item.get("id"),
                    "description": desc,
                    "can_reuse": len(user_essays) > 0
                })
            elif item_type == "document":
                # Check if user has this type of document
                doc_types = ["transcript", "recommendation", "resume", "financial"]
                has_match = any(d.document_type and any(t in d.document_type.lower() for t in doc_types if t in desc.lower()) for d in user_docs)
                missing_documents.append({
                    "id": item.get("id"),
                    "description": desc,
                    "may_have_document": has_match
                })
            else:
                missing_other.append({
                    "id": item.get("id"),
                    "description": desc
                })

        return {
            "application_id": application_id,
            "scholarship_name": scholarship.name if scholarship else "Unknown",
            "deadline": application.deadline.isoformat() if application.deadline else None,
            "missing_essays": missing_essays,
            "missing_documents": missing_documents,
            "missing_other": missing_other,
            "total_missing": len(missing_essays) + len(missing_documents) + len(missing_other),
            "user_essay_count": len(user_essays),
            "user_document_count": len(user_docs)
        }

    async def _tool_suggest_essay_matches(self, scholarship_id: int) -> Dict[str, Any]:
        """Find existing essays that could be adapted for a scholarship."""
        scholarship = self.db.query(Scholarship).filter(Scholarship.id == scholarship_id).first()
        if not scholarship:
            raise ToolExecutionError(f"Scholarship {scholarship_id} not found")

        requirements = scholarship.application_requirements or {}
        essay_prompts = requirements.get("essays", [])

        user_essays = self.db.query(Essay).filter(Essay.user_id == self.user_id).all()

        suggestions = []
        for i, prompt in enumerate(essay_prompts):
            prompt_text = prompt.get("prompt", "") if isinstance(prompt, dict) else str(prompt)
            word_count = prompt.get("word_count", 500) if isinstance(prompt, dict) else 500

            matches = []
            for essay in user_essays:
                # Simple keyword matching (LLM would be better)
                score = 0
                if essay.prompt_category:
                    # Check category relevance
                    if any(kw in prompt_text.lower() for kw in [essay.prompt_category.lower()]):
                        score += 30

                # Check tag overlap
                if essay.tags:
                    for tag in essay.tags:
                        if tag.lower() in prompt_text.lower():
                            score += 10

                # Word count compatibility
                if essay.word_count:
                    diff = abs(essay.word_count - word_count)
                    if diff < 100:
                        score += 20
                    elif diff < 200:
                        score += 10

                if score > 0:
                    matches.append({
                        "essay_id": essay.id,
                        "essay_title": essay.title,
                        "word_count": essay.word_count,
                        "category": essay.prompt_category,
                        "match_score": min(score, 100),
                        "needs_adaptation": essay.word_count != word_count if essay.word_count else True
                    })

            matches.sort(key=lambda x: x["match_score"], reverse=True)

            suggestions.append({
                "prompt": prompt_text[:200] + "..." if len(prompt_text) > 200 else prompt_text,
                "required_word_count": word_count,
                "matching_essays": matches[:3],
                "has_matches": len(matches) > 0
            })

        return {
            "scholarship_id": scholarship_id,
            "scholarship_name": scholarship.name,
            "essay_requirements": len(essay_prompts),
            "suggestions": suggestions,
            "user_essay_count": len(user_essays)
        }

    # ===================
    # Recommendations
    # ===================

    async def _tool_get_recommendations(
        self,
        limit: int = 5,
        exclude_applied: bool = True
    ) -> Dict[str, Any]:
        """Get personalized scholarship recommendations."""
        # Get user profile
        profile_mapper = ProfileMapper(self.db)
        profile_data = profile_mapper.get_profile_for_matching(self.user_id)

        # Get scholarships to evaluate
        query = self.db.query(Scholarship)

        # Exclude already applied
        if exclude_applied:
            applied_ids = [a.scholarship_id for a in
                          self.db.query(Application.scholarship_id).filter(Application.user_id == self.user_id).all()]
            if applied_ids:
                query = query.filter(~Scholarship.id.in_(applied_ids))

        # Only active scholarships
        today = date.today()
        query = query.filter(
            or_(Scholarship.deadline.is_(None), Scholarship.deadline >= today)
        )

        scholarships = query.limit(20).all()  # Get more than limit for scoring

        # Score each scholarship (use empty dict if no profile)
        profile_for_scoring = profile_data or {}

        scored = []
        for s in scholarships:
            score = self._calculate_basic_match_score(s, profile_for_scoring)
            scored.append((s, score))

        # Sort by score and take top N
        scored.sort(key=lambda x: x[1], reverse=True)
        top_scholarships = scored[:limit]

        recommendations = []
        for scholarship, score in top_scholarships:
            amount = scholarship.award_amount
            if not amount and scholarship.award_amount_min:
                amount = scholarship.award_amount_min

            recommendations.append({
                "scholarship_id": scholarship.id,
                "name": scholarship.name,
                "provider": scholarship.provider,
                "match_score": score,
                "award_amount": f"${amount:,.0f}" if amount else "Varies",
                "deadline": scholarship.deadline.isoformat() if scholarship.deadline else None,
                "reason": self._get_match_reason(scholarship, profile_for_scoring)
            })

        result = {
            "recommendations": recommendations,
            "total_evaluated": len(scholarships),
            "profile_completeness": self._calculate_profile_completeness(profile_for_scoring)
        }
        if not profile_data:
            result["note"] = "Results are not personalized. Complete your profile for better matches."
        return result

    def _calculate_basic_match_score(self, scholarship: Scholarship, profile: Dict) -> int:
        """Calculate a basic match score without LLM."""
        score = 50  # Base score
        eligibility = scholarship.eligibility or {}

        # GPA
        if profile.get("gpa") and eligibility.get("gpa_minimum"):
            if profile["gpa"] >= eligibility["gpa_minimum"]:
                score += 15
            else:
                score -= 20

        # Major
        if profile.get("intended_major") and eligibility.get("majors"):
            if any(m.lower() in profile["intended_major"].lower() for m in eligibility["majors"]):
                score += 15

        # State
        if profile.get("state") and eligibility.get("states"):
            if profile["state"] in eligibility["states"]:
                score += 10
            else:
                score -= 10

        # Citizenship
        if profile.get("citizenship_status") and eligibility.get("citizenship"):
            if profile["citizenship_status"] in eligibility.get("citizenship", []):
                score += 10

        # Keywords match
        if scholarship.keywords and profile.get("intended_major"):
            if any(kw.lower() in profile["intended_major"].lower() for kw in scholarship.keywords):
                score += 10

        return max(0, min(100, score))

    def _get_match_reason(self, scholarship: Scholarship, profile: Dict) -> str:
        """Generate a simple reason why this scholarship matches."""
        reasons = []

        eligibility = scholarship.eligibility or {}

        if profile.get("intended_major") and scholarship.keywords:
            matching_keywords = [kw for kw in scholarship.keywords if kw.lower() in profile["intended_major"].lower()]
            if matching_keywords:
                reasons.append(f"Matches your interest in {matching_keywords[0]}")

        if profile.get("gpa") and eligibility.get("gpa_minimum"):
            if profile["gpa"] >= eligibility["gpa_minimum"]:
                reasons.append("You meet the GPA requirement")

        if scholarship.award_amount and scholarship.award_amount >= 1000:
            reasons.append(f"Significant award amount")

        if not reasons:
            reasons.append("May be a good fit based on your profile")

        return reasons[0]

    def _calculate_profile_completeness(self, profile: Dict) -> int:
        """Calculate how complete the profile is."""
        important_fields = [
            "gpa", "graduation_year", "intended_major", "state",
            "citizenship_status", "current_school"
        ]
        filled = sum(1 for f in important_fields if profile.get(f))
        return int((filled / len(important_fields)) * 100)
