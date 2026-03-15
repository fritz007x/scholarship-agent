"""
Scraper Implementations

Each scraper targets a specific scholarship source.
"""
from app.scraper.scrapers.rss_scraper import RssScraper
from app.scraper.scrapers.edu_scraper import EduScholarshipScraper

__all__ = ["RssScraper", "EduScholarshipScraper"]
