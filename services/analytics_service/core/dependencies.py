from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends

from .settings import AnalyticsServiceSettings, get_settings


def get_app_settings() -> AnalyticsServiceSettings:
    return get_settings()


def settings_dependency(
    settings: AnalyticsServiceSettings = Depends(get_app_settings),
) -> Generator:
    """
    Wrapper dependency to allow future extension (e.g., per-request overrides).
    """
    yield settings

