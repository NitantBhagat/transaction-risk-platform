from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from services.worker.risk_pipeline import _score_event, handle_transaction_ingested
from shared.db import get_engine
from shared.models import RiskAssessment, Transaction
from shared.schemas.events import TransactionIngestedEvent


@pytest.mark.asyncio
async def test_score_event_is_deterministic() -> None:
    event = TransactionIngestedEvent(
        event_id="evt-1",
        transaction_external_id="txn-1",
        account_external_id="acc-1",
        merchant_external_id=None,
        amount=10_000,
        currency="USD",
        occurred_at=datetime(2024, 1, 1, 2, 0, tzinfo=timezone.utc),
        transaction_id=1,
        country="IR",
        merchant_category="5967",
    )

    first = _score_event(event)
    second = _score_event(event)
    assert first == second


@pytest.mark.asyncio
async def test_handle_event_persists_assessment_and_is_idempotent() -> None:
    engine = get_engine()
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(RiskAssessment.metadata.create_all)
        await conn.run_sync(Transaction.metadata.create_all)

    async with async_session() as session:
        tx = Transaction(
            external_id="txn-risk-1",
            account_id=1,
            merchant_id=None,
            amount=1000,
            currency="USD",
            occurred_at=datetime.now(timezone.utc),
        )
        session.add(tx)
        await session.commit()

    event = TransactionIngestedEvent(
        event_id="evt-risk-1",
        transaction_external_id="txn-risk-1",
        account_external_id="acc-1",
        merchant_external_id=None,
        amount=1000,
        currency="USD",
        occurred_at=datetime.now(timezone.utc),
        transaction_id=None,
        country=None,
        merchant_category=None,
    )

    await handle_transaction_ingested(event)
    await handle_transaction_ingested(event)

    async with async_session() as session:
        assessments = (
            await session.execute(
                select(RiskAssessment).where(RiskAssessment.event_id == "evt-risk-1")
            )
        ).scalars().all()
        assert len(assessments) == 1


@pytest.mark.asyncio
async def test_handle_event_retries_on_operational_error(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = get_engine()
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(RiskAssessment.metadata.create_all)
        await conn.run_sync(Transaction.metadata.create_all)

    async with async_session() as session:
        tx = Transaction(
            external_id="txn-risk-2",
            account_id=1,
            merchant_id=None,
            amount=1000,
            currency="USD",
            occurred_at=datetime.now(timezone.utc),
        )
        session.add(tx)
        await session.commit()

    event = TransactionIngestedEvent(
        event_id="evt-risk-2",
        transaction_external_id="txn-risk-2",
        account_external_id="acc-1",
        merchant_external_id=None,
        amount=1000,
        currency="USD",
        occurred_at=datetime.now(timezone.utc),
        transaction_id=None,
        country=None,
        merchant_category=None,
    )

    call_count = {"n": 0}

    original_get_engine = get_engine

    def flaky_get_engine():
        from sqlalchemy.exc import OperationalError
        from sqlalchemy.engine import Connection

        if call_count["n"] == 0:
            call_count["n"] += 1
            raise OperationalError("flaky", params=None, orig=None)
        return original_get_engine()

    monkeypatch.setattr("services.worker.risk_pipeline.get_engine", flaky_get_engine)

    await handle_transaction_ingested(event)

    async with async_session() as session:
        assessments = (
            await session.execute(
                select(RiskAssessment).where(RiskAssessment.event_id == "evt-risk-2")
            )
        ).scalars().all()
        assert len(assessments) == 1


@pytest.mark.asyncio
async def test_invalid_event_transaction_missing_is_handled_safely() -> None:
    engine = get_engine()
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(RiskAssessment.metadata.create_all)

    event = TransactionIngestedEvent(
        event_id="evt-missing-1",
        transaction_external_id="non-existent",
        account_external_id="acc-1",
        merchant_external_id=None,
        amount=100,
        currency="USD",
        occurred_at=datetime.now(timezone.utc),
        transaction_id=None,
        country=None,
        merchant_category=None,
    )

    await handle_transaction_ingested(event)

    async with async_session() as session:
        assessments = (
            await session.execute(select(RiskAssessment).where(RiskAssessment.event_id == "evt-missing-1"))
        ).scalars().all()
        assert len(assessments) == 0

