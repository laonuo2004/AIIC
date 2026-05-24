from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./data/app.sqlite3"
    secret_key: str = "replace_with_a_random_secret_key"
    access_token_expire_minutes: int = 1440
    frontend_origin: str = "http://localhost:3000"

    litellm_model: str = "openrouter/qwen/qwen3.6-flash"
    litellm_fallback_model: str | None = "openrouter/qwen/qwen3.6-flash"
    litellm_temperature: float = 0.2
    litellm_timeout_seconds: int = 60
    openrouter_api_key: str | None = Field(default=None, repr=False)
    openrouter_http_proxy: str | None = Field(default=None, repr=False)
    upload_dir: str = "./data/uploads"
    max_upload_bytes: int = 5 * 1024 * 1024
    max_attachments_per_message: int = 4

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
