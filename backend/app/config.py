from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration sourced from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/recruit_me"

    gemini_api_key: Optional[str] = None
    # Default to a model that's commonly available for generateContent via google-genai.
    # Override with GEMINI_VISION_MODEL as needed.
    gemini_vision_model: str = "gemini-2.0-flash"
    gemini_timeout_seconds: int = 20

    scraper_timeout_seconds: int = 15
    scraper_debug_artifacts: bool = Field(default=False, validation_alias="SCRAPER_DEBUG_ARTIFACTS")
    scraper_artifacts_dir: str = Field(default=".artifacts/linkedin", validation_alias="SCRAPER_ARTIFACTS_DIR")
    # Optional: reuse a logged-in LinkedIn session captured via Playwright storage state.
    # Create it once with scripts/save_linkedin_storage_state.py
    linkedin_storage_state_path: Optional[str] = Field(
        default=None,
        validation_alias="LINKEDIN_STORAGE_STATE_PATH",
        description="Path to Playwright storage_state.json to reuse authenticated LinkedIn session",
    )
    linkedin_login_url: str = Field(
        default="https://www.linkedin.com/login",
        validation_alias="LINKEDIN_LOGIN_URL",
        description="Login URL used by the storage-state capture script",
    )
    scraper_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    )


settings = Settings()
