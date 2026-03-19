from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings

from shared.config import AppSettings


class GatewayServiceSettings(AppSettings, BaseSettings):
    service_name: str = "gateway"
    service_port: int = 8000


@lru_cache
def get_settings() -> GatewayServiceSettings:
    return GatewayServiceSettings()

