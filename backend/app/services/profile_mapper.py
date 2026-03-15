from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.profile import UserProfile


class ProfileMapper:
    """Maps user profile data to pre-filled application fields."""

    def __init__(self, db: Session = None):
        self.db = db

    def get_profile_for_matching(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user profile data formatted for LLM matching analysis."""
        if not self.db:
            return None

        profile = self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not profile:
            return None

        return {
            "gpa": profile.gpa,
            "gpa_scale": profile.gpa_scale or 4.0,
            "graduation_year": profile.graduation_year,
            "current_school": profile.current_school,
            "intended_major": profile.intended_major,
            "intended_minor": profile.intended_minor,
            "career_interests": profile.career_interests or [],
            "state": profile.state,
            "citizenship_status": profile.citizenship_status,
            "gender": profile.gender if not profile.exclude_demographics_from_matching else None,
            "ethnicity": profile.ethnicity if not profile.exclude_demographics_from_matching else None,
            "first_generation": profile.first_generation if not profile.exclude_demographics_from_matching else None,
            "estimated_efc": profile.estimated_efc,
            "household_income_range": profile.household_income_range,
            "extracurriculars": profile.extracurriculars or [],
            "awards": profile.awards or [],
            "volunteer_work": profile.volunteer_work or [],
            "work_experience": profile.work_experience or [],
            "essay_topics": profile.essay_topics or [],
        }

    @staticmethod
    def generate_prefilled_data(profile: Optional[UserProfile]) -> Dict[str, Any]:
        if not profile:
            return {}

        data = {}

        # Personal Information
        if profile.first_name or profile.last_name:
            name_parts = [profile.first_name, profile.middle_name, profile.last_name]
            data["full_name"] = " ".join(filter(None, name_parts))

        if profile.first_name:
            data["first_name"] = profile.first_name
        if profile.middle_name:
            data["middle_name"] = profile.middle_name
        if profile.last_name:
            data["last_name"] = profile.last_name
        if profile.date_of_birth:
            data["date_of_birth"] = profile.date_of_birth.isoformat()
        if profile.phone:
            data["phone"] = profile.phone

        # Address
        address_parts = []
        if profile.street_address:
            address_parts.append(profile.street_address)
            data["street_address"] = profile.street_address
        if profile.city:
            address_parts.append(profile.city)
            data["city"] = profile.city
        if profile.state:
            address_parts.append(profile.state)
            data["state"] = profile.state
        if profile.zip_code:
            address_parts.append(profile.zip_code)
            data["zip_code"] = profile.zip_code
        if profile.country:
            data["country"] = profile.country

        if address_parts:
            data["full_address"] = ", ".join(address_parts)

        # Academic Information
        if profile.current_school:
            data["current_school"] = profile.current_school
        if profile.graduation_year:
            data["graduation_year"] = profile.graduation_year
        if profile.gpa is not None:
            data["gpa"] = profile.gpa
            scale = profile.gpa_scale or 4.0
            data["gpa_formatted"] = f"{profile.gpa}/{scale}"
        if profile.class_rank and profile.class_size:
            data["class_rank"] = f"{profile.class_rank}/{profile.class_size}"
        if profile.intended_major:
            data["intended_major"] = profile.intended_major
        if profile.intended_minor:
            data["intended_minor"] = profile.intended_minor
        if profile.career_interests:
            data["career_interests"] = profile.career_interests

        # Test Scores
        if profile.test_scores:
            data["test_scores"] = profile.test_scores
            # Format as string for display
            score_parts = [f"{k}: {v}" for k, v in profile.test_scores.items()]
            data["test_scores_formatted"] = ", ".join(score_parts)

        # Activities Summary
        activities_summary = []

        if profile.extracurriculars:
            for activity in profile.extracurriculars:
                name = activity.get("name", "")
                role = activity.get("role", "")
                years = activity.get("years", "")
                if name:
                    summary = name
                    if role:
                        summary += f" ({role})"
                    if years:
                        summary += f" - {years} years"
                    activities_summary.append(summary)
            data["extracurriculars"] = profile.extracurriculars

        if activities_summary:
            data["activities_summary"] = "; ".join(activities_summary)

        # Awards
        if profile.awards:
            award_summaries = []
            for award in profile.awards:
                name = award.get("name", "")
                year = award.get("year", "")
                level = award.get("level", "")
                if name:
                    summary = name
                    if level:
                        summary += f" ({level})"
                    if year:
                        summary += f" - {year}"
                    award_summaries.append(summary)
            data["awards"] = profile.awards
            data["awards_summary"] = "; ".join(award_summaries)

        # Volunteer Work
        if profile.volunteer_work:
            data["volunteer_work"] = profile.volunteer_work
            total_hours = sum(v.get("hours", 0) for v in profile.volunteer_work)
            data["total_volunteer_hours"] = total_hours

        # Work Experience
        if profile.work_experience:
            data["work_experience"] = profile.work_experience

        # Financial
        if profile.estimated_efc is not None:
            data["estimated_efc"] = profile.estimated_efc
        if profile.household_income_range:
            data["household_income_range"] = profile.household_income_range

        # Demographics (only if not excluded)
        if not profile.exclude_demographics_from_matching:
            if profile.gender:
                data["gender"] = profile.gender
            if profile.ethnicity:
                data["ethnicity"] = profile.ethnicity
            if profile.citizenship_status:
                data["citizenship_status"] = profile.citizenship_status
            if profile.first_generation is not None:
                data["first_generation"] = profile.first_generation

        return data
