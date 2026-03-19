from __future__ import annotations

from functools import lru_cache

from pydantic import AnyUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseDsn(AnyUrl):
    allowed_schemes = {"postgresql+asyncpg"}


class RedisDsn(AnyUrl):
    allowed_schemes = {"redis", "rediss"}


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"

    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "transaction_risk"
    postgres_user: str = "transaction_risk"
    postgres_password: str = "transaction_risk"

    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    service_name: str = "base"
    service_version: str = "0.1.0"

    auth_secret_key: str = "INSECURE-DEV-ONLY"
    auth_algorithm: str = "HS256"
    auth_audience: str | None = None
    auth_issuer: str | None = None

    @property
    def database_url(self) -> DatabaseDsn:
        return DatabaseDsn(
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> RedisDsn:
        return RedisDsn(
            f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}",
        )


@lru_cache
def get_base_settings() -> AppSettings:
    return AppSettings()

