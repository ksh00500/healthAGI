from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://healthagi:changeme@localhost:5432/healthagi"
    )

    # Auth
    jwt_secret: str = Field(default="dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:8081,http://localhost:19006"

    # LLM (placeholder for later phases)
    ollama_base_url: str = "http://localhost:11434"
    llm_text_model: str = "gemma3:12b"
    llm_vision_model: str = "qwen2-vl:7b"
    llm_voice_model: str = "gemma3:4b"

    # Storage (placeholder for later phases)
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "healthagi"
    minio_root_password: str = "changeme-minio"
    minio_bucket: str = "healthagi"
    minio_secure: bool = False

    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
