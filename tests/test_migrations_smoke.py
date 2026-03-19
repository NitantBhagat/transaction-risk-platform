from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import OperationalError

from shared.db import get_engine


@pytest.mark.integration
def test_migrations_upgrade_head_smoke() -> None:
    engine = get_engine()

    async def _check_connection() -> None:
        async with engine.begin() as conn:  # type: ignore[unused-variable]
            return

    try:
        asyncio.run(_check_connection())
    except OperationalError:
        pytest.skip("Database is unavailable for migration smoke test")

    cfg = Config(str(Path("alembic.ini").resolve()))
    cfg.set_main_option("sqlalchemy.url", str(engine.url))

    command.upgrade(cfg, "head")

