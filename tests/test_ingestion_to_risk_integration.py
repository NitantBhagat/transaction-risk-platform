from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
from collections import deque

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from services.ingestion_service.main import app as ingestion_app
from services.worker.risk_pipeline import handle_transaction_ingested
from shared import pipeline
from shared.db import get_engine
from shared.models import Account, Merchant, RiskAssessment, Transaction
from shared.pipeline import TRANSACTION_INGEST_QUEUE_KEY, consume_transaction_ingested


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingestion_to_risk_assessment_integration() -> None:
    engine = get_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Account.metadata.create_all)
        await conn.run_sync(Merchant.metadata.create_all)
        await conn.run_sync(Transaction.metadata.create_all)
        await conn.run_sync(RiskAssessment.metadata.create_all)

    async with AsyncClient(app=ingestion_app, base_url="http://test") as client:
        payload = {
            "transaction_external_id": "txn-e2e-1",
            "account_external_id": "acc-e2e-1",
            "merchant_external_id": "m-e2e-1",
            "amount": "15000.00",
            "currency": "USD",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "country": "IR",
            "merchant_category": "5967",
        }
        response = await client.post(
            "/api/v1/transactions",
            json=payload,
            headers={"X-Request-ID": "req-e2e-1"},
        )
        assert response.status_code == 201

    agen = consume_transaction_ingested(poll_interval_seconds=0.1)
    event = await agen.__anext__()

    await handle_transaction_ingested(event)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        tx = await session.scalar(
            select(Transaction).where(Transaction.external_id == "txn-e2e-1")
        )
        assert tx is not None

        assessments = (
            await session.execute(
                select(RiskAssessment).where(RiskAssessment.transaction_id == tx.id)
            )
        ).scalars().all()
        assert len(assessments) == 1
        assert assessments[0].risk_level == "high"

