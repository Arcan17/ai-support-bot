"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object."""

    openai_api_key: str = "sk-placeholder"
    openai_model: str = "gpt-4o-mini"
    database_url: str = "sqlite:///./support_bot.db"
    app_name: str = "AI Support Bot"
    app_version: str = "1.0.0"
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
