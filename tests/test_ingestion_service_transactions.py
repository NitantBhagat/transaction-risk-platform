from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from services.ingestion_service.main import app
from shared.db import get_engine
from shared.models import Account, Transaction, TransactionAuditLog
from shared import pipeline


@pytest.mark.asyncio
async def test_create_transaction_success() -> None:
    engine = get_engine()
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Account.metadata.create_all)

    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "transaction_external_id": "txn-success-1",
            "account_external_id": "acc-success-1",
            "merchant_external_id": "m-success-1",
            "amount": "123.45",
            "currency": "USD",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "country": "US",
            "merchant_category": "5967",
        }
        response = await client.post(
            "/api/v1/transactions",
            json=payload,
            headers={"X-Request-ID": "req-success-1"},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["request_id"] == "req-success-1"
        assert body["data"]["external_id"] == "txn-success-1"

    async with async_session() as session:
        tx = await session.scalar(
            select(Transaction).where(Transaction.external_id == "txn-success-1")
        )
        assert tx is not None

        logs = (
            await session.execute(
                select(TransactionAuditLog).where(TransactionAuditLog.transaction_id == tx.id)
            )
        ).scalars().all()
        assert len(logs) == 1
        assert logs[0].action == "created"
        assert logs[0].request_id == "req-success-1"


@pytest.mark.asyncio
async def test_event_published_after_successful_ingestion(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    async def fake_publish_transaction_ingested(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})

    monkeypatch.setattr(pipeline, "publish_transaction_ingested", fake_publish_transaction_ingested)

    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "transaction_external_id": "txn-event-1",
            "account_external_id": "acc-event-1",
            "merchant_external_id": None,
            "amount": "10.00",
            "currency": "USD",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "country": "US",
            "merchant_category": None,
        }
        response = await client.post(
            "/api/v1/transactions",
            json=payload,
            headers={"X-Request-ID": "req-event-1"},
        )
        assert response.status_code == 201

    assert len(calls) == 1


@pytest.mark.asyncio
async def test_invalid_payload_returns_422() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "transaction_external_id": "txn-invalid-1",
            "account_external_id": "acc-invalid-1",
            "amount": "-10.00",
            "currency": "US",
            "occurred_at": "not-a-datetime",
        }
        response = await client.post("/api/v1/transactions", json=payload)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_submission_is_idempotent_and_logs_audit() -> None:
    engine = get_engine()
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "transaction_external_id": "txn-dup-1",
            "account_external_id": "acc-dup-1",
            "merchant_external_id": None,
            "amount": "50.00",
            "currency": "USD",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "country": "US",
            "merchant_category": None,
        }
        first = await client.post(
            "/api/v1/transactions",
            json=payload,
            headers={"X-Request-ID": "req-dup-1"},
        )
        assert first.status_code == 201

        second = await client.post(
            "/api/v1/transactions",
            json=payload,
            headers={"X-Request-ID": "req-dup-2"},
        )
        assert second.status_code == 201

    async with async_session() as session:
        tx = await session.scalar(
            select(Transaction).where(Transaction.external_id == "txn-dup-1")
        )
        assert tx is not None

        logs = (
            await session.execute(
                select(TransactionAuditLog).where(TransactionAuditLog.transaction_id == tx.id)
            )
        ).scalars().all()
        assert len(logs) == 2
        actions = {log.action for log in logs}
        assert actions == {"created", "duplicate"}

