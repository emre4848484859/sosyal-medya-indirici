"""Application configuration helpers."""

from __future__ import annotations

from pydantic import HttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load configuration from environment variables or `.env`."""

    bot_token: str = Field(..., alias="BOT_TOKEN")
    tikwm_api_url: HttpUrl = Field("https://tikwm.com/api/", alias="TIKWM_API_URL")
    http_timeout_seconds: float = Field(30, alias="HTTP_TIMEOUT_SECONDS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
