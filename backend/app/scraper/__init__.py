"""
Scholarship Scraper Module

This module provides web scraping functionality to discover and import
scholarships from external websites.
"""
from app.scraper.base import BaseScraper
from app.scraper.orchestrator import ScraperOrchestrator

__all__ = ["BaseScraper", "ScraperOrchestrator"]
