import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _env_files() -> tuple[str, ...]:
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env in {"production", "prod"}:
        return (".env", ".env.production")
    if app_env in {"local", "development", "dev"}:
        return (".env", ".env.local")
    return (".env", f".env.{app_env}")


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Atom MVP Backend"
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_url: str = "sqlite:///./data/app.db"
    session_secret: str = "change-me-in-production"
    session_ttl_hours: int = 168
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-pro"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.deepseek.com"
    openai_model: str = "deepseek-v4-pro"
    exa_api_key: str | None = None
    demo_mode: bool = Field(default=True)
    github_client_id: str | None = None
    github_client_secret: str | None = None
    auth_redirect_base_url: str = "http://127.0.0.1:8000"
    frontend_auth_callback_url: str = "http://127.0.0.1:5173/auth/callback"
    signup_message_quota: int = 6
    email_verification_ttl_minutes: int = 10
    allowed_email_domain: str = "gmail.com"
    resend_api_key: str | None = None
    email_from: str = "Atom MVP <onboarding@resend.dev>"

    model_config = SettingsConfigDict(env_file=_env_files(), env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.backend_cors_origins.split(",") if item.strip()]

    @property
    def use_mock_ai(self) -> bool:
        return self.demo_mode or not self.ai_api_key

    @property
    def ai_api_key(self) -> str | None:
        return self.deepseek_api_key or self.openai_api_key

    @property
    def ai_base_url(self) -> str:
        return self.deepseek_base_url or self.openai_base_url

    @property
    def ai_model(self) -> str:
        return self.deepseek_model or self.openai_model

    @property
    def use_mock_search(self) -> bool:
        return self.demo_mode or not self.exa_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
