from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30

    database_url: str = "postgresql+asyncpg://computeswarm:changeme@db:5432/computeswarm"

    redis_url: str = "redis://redis:6379/0"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "computeswarm"
    minio_use_ssl: bool = False

    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None

    cors_origins: str = "*"


settings = Settings()
