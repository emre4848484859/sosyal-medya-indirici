"""Application configuration helpers."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load configuration from environment variables or `.env`."""

    bot_token: str = Field(..., alias="BOT_TOKEN")
    tikwm_api_url: HttpUrl = Field("https://tikwm.com/api/", alias="TIKWM_API_URL")
    http_timeout_seconds: float = Field(30, alias="HTTP_TIMEOUT_SECONDS")
    bot_mode: Literal["polling", "webhook"] = Field("polling", alias="BOT_MODE")
    webhook_base_url: HttpUrl | None = Field(None, alias="WEBHOOK_BASE_URL")
    webhook_path: str = Field("/webhook", alias="WEBHOOK_PATH")
    webhook_secret: str | None = Field(None, alias="WEBHOOK_SECRET")
    port: int = Field(8080, alias="PORT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def webhook_url(self) -> str:
        if not self.webhook_base_url:
            msg = "WEBHOOK_BASE_URL tanımlanmadı."
            raise ValueError(msg)

        path = self.webhook_path.strip() or "/webhook"
        if not path.startswith("/"):
            path = f"/{path}"

        return f"{str(self.webhook_base_url).rstrip('/')}{path}"


settings = Settings()
