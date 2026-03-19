from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends

from .settings import GatewayServiceSettings, get_settings


def get_app_settings() -> GatewayServiceSettings:
    return get_settings()


def settings_dependency(
    settings: GatewayServiceSettings = Depends(get_app_settings),
) -> Generator:
    yield settings

