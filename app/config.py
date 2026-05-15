"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration object.

    All values can be overridden via environment variables or a .env file.
    OPENAI_API_KEY is required at runtime for /chat — tests mock the LLM
    so no real key is needed to run the test suite.
    """

    # Empty string by default so the app starts without crashing.
    # llm_service raises LLMError (→ HTTP 503) when a real call is attempted
    # without a valid key.
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    database_url: str = "sqlite:///./support_bot.db"
    app_name: str = "AI Support Bot"
    app_version: str = "1.0.0"
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
