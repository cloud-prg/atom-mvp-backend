from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "Atom MVP Backend"
    backend_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_url: str = "sqlite:///./data/app.db"
    session_secret: str = "change-me-in-production"
    session_ttl_hours: int = 168
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-5.5"
    exa_api_key: str | None = None
    demo_mode: bool = Field(default=True)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.backend_cors_origins.split(",") if item.strip()]

    @property
    def use_mock_ai(self) -> bool:
        return self.demo_mode or not self.openai_api_key

    @property
    def use_mock_search(self) -> bool:
        return self.demo_mode or not self.exa_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

