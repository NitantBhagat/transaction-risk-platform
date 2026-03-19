from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from uuid import uuid4

from redis.asyncio import Redis

from shared.redis import get_redis_client
from shared.schemas.events import TransactionIngestedEvent


TRANSACTION_INGEST_QUEUE_KEY = "risk:transaction_ingested"


def _get_redis() -> Redis:
    return get_redis_client()


_logger = logging.getLogger(__name__)


async def publish_transaction_ingested(event: TransactionIngestedEvent | None = None, **kwargs) -> None:
    """
    Enqueue a transaction into the async risk pipeline.

    This uses a Redis list as a simple, reliable queue. The payload is stored as JSON.
    """
    if event is None:
        event_id = str(uuid4())
        event = TransactionIngestedEvent(event_id=event_id, **kwargs)

    redis = _get_redis()
    envelope = {
        "type": "transaction_ingested",
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "payload": event.model_dump(),
    }
    await redis.lpush(TRANSACTION_INGEST_QUEUE_KEY, json.dumps(envelope))


async def consume_transaction_ingested(
    poll_interval_seconds: float = 1.0,
) -> AsyncIterator[TransactionIngestedEvent]:
    """
    Async iterator over ingested transactions for the risk pipeline.

    This function blocks on Redis (BRPOP) with a short timeout and yields
    `TransactionIngestedEvent` instances as they arrive.
    """
    redis = _get_redis()

    while True:
        result = await redis.brpop(TRANSACTION_INGEST_QUEUE_KEY, timeout=int(poll_interval_seconds))
        if result is None:
            # No message within timeout window; yield control to event loop.
            await asyncio.sleep(poll_interval_seconds)
            continue

        _, raw = result
        try:
            data = json.loads(raw)
            event = TransactionIngestedEvent.model_validate(data["payload"])
        except Exception:
            _logger.warning("Failed to decode transaction_ingested event", exc_info=True)
            continue

        yield event

