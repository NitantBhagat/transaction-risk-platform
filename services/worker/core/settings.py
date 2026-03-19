from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings

from shared.config import AppSettings


class WorkerServiceSettings(AppSettings, BaseSettings):
    service_name: str = "worker"
    service_port: int = 8004


@lru_cache
def get_settings() -> WorkerServiceSettings:
    return WorkerServiceSettings()

