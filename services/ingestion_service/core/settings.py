from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings

from shared.config import AppSettings


class IngestionServiceSettings(AppSettings, BaseSettings):
    service_name: str = "ingestion-service"
    service_port: int = 8001


@lru_cache
def get_settings() -> IngestionServiceSettings:
    return IngestionServiceSettings()

