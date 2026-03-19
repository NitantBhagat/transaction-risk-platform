from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends

from .settings import WorkerServiceSettings, get_settings


def get_app_settings() -> WorkerServiceSettings:
    return get_settings()


def settings_dependency(
    settings: WorkerServiceSettings = Depends(get_app_settings),
) -> Generator:
    yield settings

