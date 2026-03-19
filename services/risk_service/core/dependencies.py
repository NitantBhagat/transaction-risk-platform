from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends

from .settings import RiskServiceSettings, get_settings


def get_app_settings() -> RiskServiceSettings:
    return get_settings()


def settings_dependency(
    settings: RiskServiceSettings = Depends(get_app_settings),
) -> Generator:
    yield settings

