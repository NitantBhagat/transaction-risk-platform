from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import List, Tuple

from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.db import get_engine
from shared.logging import init_logging
from shared.models import RiskAssessment, Transaction
from shared.observability.metrics import WORKER_RISK_ASSESSMENTS_TOTAL
from shared.pipeline import consume_transaction_ingested
from shared.schemas.events import TransactionIngestedEvent


logger = init_logging("worker-risk-pipeline")


HIGH_RISK_COUNTRIES = {"IR", "KP", "SY", "CU", "RU"}
SUSPICIOUS_MERCHANT_CATEGORIES = {"5967", "7995", "4829"}


def _score_event(event: TransactionIngestedEvent) -> Tuple[float, str, str, List[str]]:
    score = 0.0
    rule_hits: List[str] = []

    if event.amount >= 10_000:
        score += 40.0
        rule_hits.append("high_amount")

    if event.country and event.country.upper() in HIGH_RISK_COUNTRIES:
        score += 30.0
        rule_hits.append("high_risk_country")

    if event.merchant_category and event.merchant_category in SUSPICIOUS_MERCHANT_CATEGORIES:
        score += 20.0
        rule_hits.append("suspicious_merchant_category")

    if 0 <= event.occurred_at.hour <= 5:
        score += 10.0
        rule_hits.append("off_hours_transaction")

    if score >= 50:
        risk_level = "high"
        decision = "decline"
    elif score >= 20:
        risk_level = "medium"
        decision = "review"
    else:
        risk_level = "low"
        decision = "approve"

    return score, risk_level, decision, rule_hits


async def handle_transaction_ingested(event: TransactionIngestedEvent) -> None:
    logger.info(
        "Received transaction for risk evaluation",
        extra={
            "event_id": event.event_id,
            "transaction_external_id": event.transaction_external_id,
        },
    )

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    engine = get_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    attempts = 0
    max_attempts = 3
    while True:
        attempts += 1
        try:
            async with session_factory() as session:
                async with session.begin():
                    existing = await session.scalar(
                        select(RiskAssessment).where(RiskAssessment.event_id == event.event_id)
                    )
                    if existing is not None:
                        logger.info(
                            "Duplicate risk event received; skipping",
                            extra={"event_id": event.event_id, "assessment_id": existing.id},
                        )
                        WORKER_RISK_ASSESSMENTS_TOTAL.labels("duplicate").inc()
                        return

                    tx = await session.scalar(
                        select(Transaction).where(
                            Transaction.external_id == event.transaction_external_id
                        )
                    )
                    if tx is None:
                        logger.warning(
                            "Transaction not found for risk event",
                            extra={
                                "event_id": event.event_id,
                                "transaction_external_id": event.transaction_external_id,
                            },
                        )
                        WORKER_RISK_ASSESSMENTS_TOTAL.labels("missing_transaction").inc()
                        return

                    score, risk_level, decision, rule_hits = _score_event(event)

                    assessment = RiskAssessment(
                        transaction_id=tx.id,
                        event_id=event.event_id,
                        risk_score=score,
                        risk_level=risk_level,
                        decision=decision,
                        rule_hits=json.dumps(rule_hits),
                        processed_at=datetime.now(timezone.utc),
                    )

                    session.add(assessment)

                    try:
                        await session.flush()
                    except IntegrityError:
                        logger.info(
                            "Risk assessment already exists for event",
                            extra={"event_id": event.event_id},
                        )
                        WORKER_RISK_ASSESSMENTS_TOTAL.labels("duplicate").inc()
                        return

                    logger.info(
                        "Risk assessment created",
                        extra={
                            "assessment_id": assessment.id,
                            "event_id": event.event_id,
                            "transaction_id": tx.id,
                            "risk_score": assessment.risk_score,
                            "risk_level": assessment.risk_level,
                            "decision": assessment.decision,
                        },
                    )
                    WORKER_RISK_ASSESSMENTS_TOTAL.labels("success").inc()
                    return
        except OperationalError:
            logger.warning(
                "Transient database error while handling event; attempt %s of %s",
                attempts,
                max_attempts,
                extra={"event_id": event.event_id},
            )
            if attempts >= max_attempts:
                WORKER_RISK_ASSESSMENTS_TOTAL.labels("error").inc()
                raise
            await asyncio.sleep(1 * attempts)


async def run_risk_pipeline() -> None:
    """
    Main async loop for the risk pipeline worker.
    """
    backoff = 1.0
    max_backoff = 10.0
    try:
        while True:
            try:
                async for event in consume_transaction_ingested():
                    await handle_transaction_ingested(event)
                    backoff = 1.0
            except (RedisError, OSError) as exc:
                logger.warning(
                    "Redis error in risk pipeline; backing off",
                    extra={"error": str(exc), "backoff_seconds": backoff},
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
    except asyncio.CancelledError:
        logger.info("Risk pipeline loop cancelled; shutting down")
        raise

