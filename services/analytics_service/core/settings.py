from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings

from shared.config import AppSettings


class AnalyticsServiceSettings(AppSettings, BaseSettings):
    service_name: str = "analytics-service"
    service_port: int = 8003


@lru_cache
def get_settings() -> AnalyticsServiceSettings:
    return AnalyticsServiceSettings()

