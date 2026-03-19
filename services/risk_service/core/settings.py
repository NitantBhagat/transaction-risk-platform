from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings

from shared.config import AppSettings


class RiskServiceSettings(AppSettings, BaseSettings):
    service_name: str = "risk-service"
    service_port: int = 8002


@lru_cache
def get_settings() -> RiskServiceSettings:
    return RiskServiceSettings()

