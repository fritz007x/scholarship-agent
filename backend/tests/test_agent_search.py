"""
Tests for agent scholarship search with minimal/incomplete profiles.

Verifies that the agent tools can search, match, and recommend scholarships
when the user profile is missing optional fields (class_rank, class_size,
intended_minor).
"""
import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from app.models.profile import UserProfile
from app.models.scholarship import Scholarship
from app.models.application import Application
from app.services.agent_tools import AgentToolRegistry
from app.services.profile_mapper import ProfileMapper


@pytest.fixture
def minimal_profile(db, test_user):
    """Profile with only core fields — no class_rank, class_size, or intended_minor."""
    profile = UserProfile(
        user_id=test_user.id,
        first_name="Jane",
        last_name="Doe",
        current_school="Springfield High",
        graduation_year=2026,
        gpa=3.8,
        gpa_scale=4.0,
        intended_major="Computer Science",
        state="IL",
        citizenship_status="US Citizen",
        # Explicitly omitted: class_rank, class_size, intended_minor
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@pytest.fixture
def scholarships(db):
    """Several scholarships with different eligibility criteria."""
    future = date.today() + timedelta(days=60)
    items = [
        Scholarship(
            name="STEM Excellence Award",
            provider="Tech Foundation",
            description="For outstanding STEM students pursuing engineering or computer science",
            award_amount=5000.0,
            deadline=future,
            eligibility={"gpa_minimum": 3.5, "majors": ["computer science", "engineering"]},
            application_requirements={"essays": [], "documents": []},
            keywords=["STEM", "computer science"],
        ),
        Scholarship(
            name="Community Leaders Grant",
            provider="Local Foundation",
            description="Supporting students who demonstrate community leadership",
            award_amount=2500.0,
            deadline=future + timedelta(days=30),
            eligibility={"gpa_minimum": 3.0},
            application_requirements={"essays": [], "documents": []},
            keywords=["leadership", "community"],
        ),
        Scholarship(
            name="Future Engineers Scholarship",
            provider="Engineering Society",
            description="For students pursuing mechanical or civil engineering",
            award_amount=10000.0,
            deadline=future + timedelta(days=15),
            eligibility={"gpa_minimum": 3.7, "majors": ["mechanical engineering", "civil engineering"]},
            application_requirements={"essays": [], "documents": []},
            keywords=["engineering"],
        ),
    ]
    db.add_all(items)
    db.commit()
    for s in items:
        db.refresh(s)
    return items


@pytest.fixture
def tools(db, test_user):
    return AgentToolRegistry(db, test_user.id)


# ─── Search without optional fields ───


@pytest.mark.asyncio
async def test_search_no_filters(tools, scholarships):
    """Search with no filters returns all active scholarships."""
    result = await tools.execute_tool("search_scholarships", {})
    assert result["success"] is True
    assert result["data"]["count"] == 3


@pytest.mark.asyncio
async def test_search_by_keyword(tools, scholarships):
    """Keyword search works without profile fields."""
    result = await tools.execute_tool("search_scholarships", {"keywords": ["STEM"]})
    assert result["success"] is True
    assert result["data"]["count"] >= 1
    names = [s["name"] for s in result["data"]["scholarships"]]
    assert "STEM Excellence Award" in names


@pytest.mark.asyncio
async def test_search_by_award_range(tools, scholarships):
    """Award filter works without profile fields."""
    result = await tools.execute_tool("search_scholarships", {
        "min_award": 4000, "max_award": 6000
    })
    assert result["success"] is True
    names = [s["name"] for s in result["data"]["scholarships"]]
    assert "STEM Excellence Award" in names
    assert "Community Leaders Grant" not in names


@pytest.mark.asyncio
async def test_search_with_limit(tools, scholarships):
    """Limit parameter is respected."""
    result = await tools.execute_tool("search_scholarships", {"limit": 1})
    assert result["success"] is True
    assert result["data"]["count"] == 1


@pytest.mark.asyncio
async def test_search_sort_by_award(tools, scholarships):
    """Sort by award_amount returns highest first."""
    result = await tools.execute_tool("search_scholarships", {"sort_by": "award_amount"})
    assert result["success"] is True
    amounts = result["data"]["scholarships"]
    assert amounts[0]["name"] == "Future Engineers Scholarship"


# ─── Profile tools with missing optional fields ───


@pytest.mark.asyncio
async def test_get_profile_without_optional_fields(tools, minimal_profile):
    """get_user_profile works and reports completeness without optional fields."""
    result = await tools.execute_tool("get_user_profile", {})
    assert result["success"] is True
    data = result["data"]
    assert data["profile_exists"] is True
    assert data["gpa"] == 3.8
    assert data["intended_major"] == "Computer Science"
    assert data["intended_minor"] is None
    assert data["completeness"] > 0


# ─── Match evaluation with minimal profile ───


@pytest.mark.asyncio
async def test_basic_match_without_optional_fields(tools, minimal_profile, scholarships):
    """Match evaluation works with a profile missing class_rank, class_size, intended_minor."""
    stem_scholarship = scholarships[0]

    with patch.object(tools.llm_service, "is_available", return_value=False):
        result = await tools.execute_tool("evaluate_scholarship_match", {
            "scholarship_id": stem_scholarship.id
        })

    assert result["success"] is True
    data = result["data"]
    assert "match_score" in data
    assert data["match_score"] > 0
    assert isinstance(data["strengths"], list)
    assert isinstance(data["considerations"], list)


@pytest.mark.asyncio
async def test_match_gpa_meets_requirement(tools, minimal_profile, scholarships):
    """GPA matching works — user 3.8 meets 3.5 minimum."""
    stem_scholarship = scholarships[0]

    with patch.object(tools.llm_service, "is_available", return_value=False):
        result = await tools.execute_tool("evaluate_scholarship_match", {
            "scholarship_id": stem_scholarship.id
        })

    strengths = result["data"]["strengths"]
    assert any("GPA" in s for s in strengths)


@pytest.mark.asyncio
async def test_match_major_alignment(tools, minimal_profile, scholarships):
    """Major matching works — user's 'Computer Science' matches scholarship majors."""
    stem_scholarship = scholarships[0]

    with patch.object(tools.llm_service, "is_available", return_value=False):
        result = await tools.execute_tool("evaluate_scholarship_match", {
            "scholarship_id": stem_scholarship.id
        })

    strengths = result["data"]["strengths"]
    assert any("major" in s.lower() for s in strengths)


# ─── Recommendations with minimal profile ───


@pytest.mark.asyncio
async def test_recommendations_without_optional_fields(tools, minimal_profile, scholarships):
    """Recommendations work without class_rank, class_size, intended_minor."""
    result = await tools.execute_tool("get_recommendations", {"limit": 5})
    assert result["success"] is True
    data = result["data"]
    assert len(data["recommendations"]) > 0
    assert data["profile_completeness"] > 0

    for rec in data["recommendations"]:
        assert "scholarship_id" in rec
        assert "match_score" in rec
        assert "reason" in rec


@pytest.mark.asyncio
async def test_recommendations_exclude_applied(tools, minimal_profile, scholarships, db, test_user):
    """Recommendations exclude scholarships the user already applied to."""
    app = Application(
        user_id=test_user.id,
        scholarship_id=scholarships[0].id,
        status="in_progress",
        checklist=[],
        checklist_total=0,
        checklist_completed=0,
    )
    db.add(app)
    db.commit()

    result = await tools.execute_tool("get_recommendations", {
        "limit": 10, "exclude_applied": True
    })
    assert result["success"] is True
    rec_ids = [r["scholarship_id"] for r in result["data"]["recommendations"]]
    assert scholarships[0].id not in rec_ids


# ─── ProfileMapper with missing optional fields ───


class TestProfileMapperOptionalFields:
    def test_prefilled_omits_missing_class_rank(self, minimal_profile):
        """Pre-filled data omits class_rank when not set."""
        result = ProfileMapper.generate_prefilled_data(minimal_profile)
        assert "class_rank" not in result

    def test_prefilled_omits_missing_minor(self, minimal_profile):
        """Pre-filled data omits intended_minor when not set."""
        result = ProfileMapper.generate_prefilled_data(minimal_profile)
        assert "intended_minor" not in result

    def test_prefilled_includes_core_fields(self, minimal_profile):
        """Pre-filled data still includes all core fields."""
        result = ProfileMapper.generate_prefilled_data(minimal_profile)
        assert result["full_name"] == "Jane Doe"
        assert result["current_school"] == "Springfield High"
        assert result["gpa"] == 3.8
        assert result["intended_major"] == "Computer Science"

    def test_matching_profile_omits_missing_minor(self):
        """Matching profile includes intended_minor as None when not set."""
        db_mock = MagicMock()
        profile = MagicMock()
        profile.intended_minor = None
        profile.class_rank = None
        profile.class_size = None
        profile.gpa = 3.8
        profile.gpa_scale = 4.0
        profile.graduation_year = 2026
        profile.current_school = "Springfield High"
        profile.intended_major = "Computer Science"
        profile.career_interests = []
        profile.state = "IL"
        profile.citizenship_status = "US Citizen"
        profile.gender = None
        profile.ethnicity = None
        profile.first_generation = None
        profile.exclude_demographics_from_matching = False
        profile.estimated_efc = None
        profile.household_income_range = None
        profile.extracurriculars = []
        profile.awards = []
        profile.volunteer_work = []
        profile.work_experience = []
        profile.essay_topics = []

        db_mock.query.return_value.filter.return_value.first.return_value = profile
        mapper = ProfileMapper(db=db_mock)
        result = mapper.get_profile_for_matching(user_id=1)

        assert result is not None
        assert result["intended_minor"] is None
        assert result["intended_major"] == "Computer Science"
        assert result["gpa"] == 3.8
