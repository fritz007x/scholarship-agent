from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Scholarship(Base):
    __tablename__ = "scholarships"

    id = Column(Integer, primary_key=True, index=True)

    # Basic Information
    name = Column(String, nullable=False, index=True)
    provider = Column(String)
    description = Column(String)
    url = Column(String)
    award_amount = Column(Float)
    award_amount_min = Column(Float)
    award_amount_max = Column(Float)
    number_of_awards = Column(Integer)
    is_renewable = Column(Boolean, default=False)
    deadline = Column(Date)
    is_recurring = Column(Boolean, default=False)

    # Requirements (stored as JSON for flexibility)
    eligibility = Column(JSON, default=dict)
    # {
    #   "gpa_minimum": 3.0,
    #   "grade_levels": ["junior", "senior"],
    #   "majors": ["engineering", "computer science"],
    #   "states": ["CA", "NY"],
    #   "citizenship": ["US Citizen", "Permanent Resident"],
    #   "demographics": {"gender": "female", "first_generation": true}
    # }

    application_requirements = Column(JSON, default=dict)
    # {
    #   "essays": [{"prompt": "...", "word_count": 500}],
    #   "documents": ["transcript", "recommendation_letter"],
    #   "other": ["interview", "portfolio"]
    # }

    # Metadata for matching
    keywords = Column(JSON, default=list)  # ["STEM", "leadership", "community service"]
    categories = Column(JSON, default=list)  # ["merit-based", "need-based", "field-specific"]
    source = Column(String)  # 'manual', 'scholarships_com', 'bold_org', 'rss', etc.
    raw_text = Column(String)  # Original text for re-parsing
    is_verified = Column(Boolean, default=False)

    # Scraping metadata
    source_url = Column(String, unique=True)  # Original URL where scholarship was found
    scrape_hash = Column(String, index=True)  # Hash for deduplication
    last_scraped_at = Column(DateTime(timezone=True))
    verification_status = Column(String, default='unverified')  # unverified, verified, outdated, removed

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    applications = relationship("Application", back_populates="scholarship")
