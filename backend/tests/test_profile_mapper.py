import pytest
from unittest.mock import MagicMock
from datetime import date
from app.services.profile_mapper import ProfileMapper


def make_profile(**kwargs):
    profile = MagicMock()
    defaults = {
        "first_name": None, "middle_name": None, "last_name": None,
        "date_of_birth": None, "phone": None,
        "street_address": None, "city": None, "state": None,
        "zip_code": None, "country": None,
        "current_school": None, "graduation_year": None,
        "gpa": None, "gpa_scale": 4.0,
        "class_rank": None, "class_size": None,
        "intended_major": None, "intended_minor": None,
        "career_interests": None, "test_scores": None,
        "extracurriculars": None, "awards": None,
        "volunteer_work": None, "work_experience": None,
        "estimated_efc": None, "household_income_range": None,
        "gender": None, "ethnicity": None,
        "citizenship_status": None, "first_generation": None,
        "exclude_demographics_from_matching": False,
        "essay_topics": None,
    }
    defaults.update(kwargs)
    for key, value in defaults.items():
        setattr(profile, key, value)
    return profile


class TestGeneratePrefilledData:
    def test_none_profile(self):
        result = ProfileMapper.generate_prefilled_data(None)
        assert result == {}

    def test_full_name(self):
        profile = make_profile(first_name="John", middle_name="M", last_name="Doe")
        result = ProfileMapper.generate_prefilled_data(profile)
        assert result["full_name"] == "John M Doe"
        assert result["first_name"] == "John"

    def test_name_without_middle(self):
        profile = make_profile(first_name="Jane", last_name="Smith")
        result = ProfileMapper.generate_prefilled_data(profile)
        assert result["full_name"] == "Jane Smith"

    def test_address(self):
        profile = make_profile(
            street_address="123 Main St", city="Springfield",
            state="IL", zip_code="62701"
        )
        result = ProfileMapper.generate_prefilled_data(profile)
        assert "123 Main St" in result["full_address"]
        assert "Springfield" in result["full_address"]

    def test_gpa_formatted(self):
        profile = make_profile(gpa=3.85, gpa_scale=4.0)
        result = ProfileMapper.generate_prefilled_data(profile)
        assert result["gpa_formatted"] == "3.85/4.0"

    def test_class_rank(self):
        profile = make_profile(class_rank=5, class_size=200)
        result = ProfileMapper.generate_prefilled_data(profile)
        assert result["class_rank"] == "5/200"

    def test_test_scores_formatted(self):
        profile = make_profile(test_scores={"SAT": 1500, "ACT": 34})
        result = ProfileMapper.generate_prefilled_data(profile)
        assert "SAT: 1500" in result["test_scores_formatted"]

    def test_volunteer_total_hours(self):
        profile = make_profile(volunteer_work=[
            {"name": "Food Bank", "hours": 100},
            {"name": "Tutoring", "hours": 50}
        ])
        result = ProfileMapper.generate_prefilled_data(profile)
        assert result["total_volunteer_hours"] == 150

    def test_demographics_excluded(self):
        profile = make_profile(
            gender="Female", ethnicity=["Asian"],
            exclude_demographics_from_matching=True
        )
        result = ProfileMapper.generate_prefilled_data(profile)
        assert "gender" not in result
        assert "ethnicity" not in result

    def test_demographics_included(self):
        profile = make_profile(
            gender="Male", ethnicity=["Hispanic"],
            citizenship_status="US Citizen", first_generation=True,
            exclude_demographics_from_matching=False
        )
        result = ProfileMapper.generate_prefilled_data(profile)
        assert result["gender"] == "Male"
        assert result["first_generation"] is True
