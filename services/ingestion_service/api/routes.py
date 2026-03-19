from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.ingestion_service.core.dependencies import settings_dependency
from services.ingestion_service.core.settings import IngestionServiceSettings
from services.ingestion_service.schemas import (
    TransactionCreateRequest,
    TransactionCreateResponse,
    TransactionResource,
)
from shared.db import get_db_session
from shared.models import Account, Merchant, Transaction, TransactionAuditLog
from shared.pipeline import publish_transaction_ingested
from shared.schemas.events import TransactionIngestedEvent
from shared.schemas import HealthResponse


router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Ingestion service health check")
async def health(
    settings: IngestionServiceSettings = Depends(settings_dependency),
) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name, version=settings.service_version)


logger = logging.getLogger("ingestion-service.transactions")


@router.post(
    "/api/v1/transactions",
    response_model=TransactionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new transaction",
)
async def create_transaction(
    request: Request,
    payload: TransactionCreateRequest,
    db_session: AsyncSession = Depends(get_db_session),
) -> TransactionCreateResponse:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())

    logger.info(
        "Received transaction ingestion request",
        extra={
            "request_id": request_id,
            "transaction_external_id": payload.transaction_external_id,
        },
    )

    async with db_session.begin():
        existing_tx = await db_session.scalar(
            select(Transaction).where(Transaction.external_id == payload.transaction_external_id)
        )

        if existing_tx is None:
            account = await db_session.scalar(
                select(Account).where(Account.external_id == payload.account_external_id)
            )
            if account is None:
                account = Account(external_id=payload.account_external_id)
                db_session.add(account)

            merchant = None
            if payload.merchant_external_id is not None:
                merchant = await db_session.scalar(
                    select(Merchant).where(
                        Merchant.external_id == payload.merchant_external_id
                    )
                )
                if merchant is None:
                    merchant = Merchant(external_id=payload.merchant_external_id)
                    db_session.add(merchant)

            await db_session.flush()

            tx = Transaction(
                external_id=payload.transaction_external_id,
                account_id=account.id,
                merchant_id=merchant.id if merchant is not None else None,
                amount=payload.amount,
                currency=payload.currency,
                occurred_at=payload.occurred_at,
            )
            db_session.add(tx)
            await db_session.flush()

            audit = TransactionAuditLog(
                transaction_id=tx.id,
                action="created",
                request_id=request_id,
            )
            db_session.add(audit)

            logger.info(
                "Transaction created",
                extra={"request_id": request_id, "transaction_id": tx.id},
            )

            event = TransactionIngestedEvent(
                event_id=str(uuid4()),
                transaction_external_id=tx.external_id,
                account_external_id=payload.account_external_id,
                merchant_external_id=payload.merchant_external_id,
                amount=tx.amount,
                currency=tx.currency,
                occurred_at=tx.occurred_at,
                transaction_id=tx.id,
                country=payload.country,
                merchant_category=payload.merchant_category,
            )
            await publish_transaction_ingested(event=event)

            resource = TransactionResource(
                id=tx.id,
                external_id=tx.external_id,
                account_external_id=payload.account_external_id,
                merchant_external_id=payload.merchant_external_id,
                amount=tx.amount,
                currency=tx.currency,
                occurred_at=tx.occurred_at,
                status=tx.status,
            )

            return TransactionCreateResponse(request_id=request_id, data=resource, error=None)

        audit = TransactionAuditLog(
            transaction_id=existing_tx.id,
            action="duplicate",
            request_id=request_id,
        )
        db_session.add(audit)

        logger.info(
            "Duplicate transaction submission",
            extra={"request_id": request_id, "transaction_id": existing_tx.id},
        )

        account = await db_session.scalar(
            select(Account).where(Account.id == existing_tx.account_id)
        )
        merchant = None
        if existing_tx.merchant_id is not None:
            merchant = await db_session.scalar(
                select(Merchant).where(Merchant.id == existing_tx.merchant_id)
            )

        resource = TransactionResource(
            id=existing_tx.id,
            external_id=existing_tx.external_id,
            account_external_id=account.external_id if account is not None else "",
            merchant_external_id=merchant.external_id if merchant is not None else None,
            amount=existing_tx.amount,
            currency=existing_tx.currency,
            occurred_at=existing_tx.occurred_at,
            status=existing_tx.status,
        )

        return TransactionCreateResponse(request_id=request_id, data=resource, error=None)

