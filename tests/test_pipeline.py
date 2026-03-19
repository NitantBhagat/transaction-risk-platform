from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

import pytest

from shared import pipeline
from shared.pipeline import (
    TRANSACTION_INGEST_QUEUE_KEY,
    consume_transaction_ingested,
    publish_transaction_ingested,
)
from shared.schemas.events import TransactionIngestedEvent


class _FakeRedis:
    def __init__(self) -> None:
        self.queues: dict[str, deque[str]] = {TRANSACTION_INGEST_QUEUE_KEY: deque()}

    async def lpush(self, key: str, value: str) -> None:
        self.queues.setdefault(key, deque()).appendleft(value)

    async def brpop(self, key: str, timeout: int) -> Any:
        queue = self.queues.setdefault(key, deque())
        # immediate pop for tests; ignore timeout
        try:
            value = queue.pop()
        except IndexError:
            await asyncio.sleep(0)  # yield control
            return None
        return key, value


@pytest.mark.asyncio
async def test_publish_and_consume_transaction_ingested(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = _FakeRedis()

    def _fake_get_redis_client() -> _FakeRedis:
        return fake_redis

    monkeypatch.setattr(pipeline, "_get_redis", _fake_get_redis_client)

    event = TransactionIngestedEvent(
        transaction_external_id="txn-1",
        account_external_id="acc-1",
        merchant_external_id=None,
        amount="100.00",
        currency="USD",
        occurred_at="2024-01-01T00:00:00Z",
    )

    await publish_transaction_ingested(event)

    # Consume a single event from the async iterator.
    agen = consume_transaction_ingested(poll_interval_seconds=0.1)
    received = await agen.__anext__()

    assert received.transaction_external_id == event.transaction_external_id
    assert received.account_external_id == event.account_external_id
    assert received.amount == event.amount
    assert received.currency == event.currency

