from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
import os


class Settings(BaseSettings):
    secret_key: str = "dev-secret-key-change-in-production"
    database_url: str = "sqlite:///./scholarship_agent.db"
    access_token_expire_days: int = 7
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 10
    algorithm: str = "HS256"

    # LLM settings
    google_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"

    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v):
        # Allow weak key only in development
        weak_keys = {'dev-secret-key-change-in-production', 'your-secret-key-here-change-in-production'}
        if v in weak_keys:
            # Check if we're in production
            if os.getenv('ENVIRONMENT', 'development').lower() == 'production':
                raise ValueError('SECRET_KEY must be set to a secure value in production')
        return v

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
