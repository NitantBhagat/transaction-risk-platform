from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.analytics_service.core.dependencies import settings_dependency
from services.analytics_service.core.settings import AnalyticsServiceSettings
from services.analytics_service.schemas import (
    AnalyticsSummary,
    Envelope,
    RiskDistributionBucket,
    TopRiskMerchant,
    TransactionSearchItem,
    TransactionSearchResult,
    VolumeByDayBucket,
)
from shared.auth import require_roles
from shared.db import get_db_session
from shared.models import Merchant, RiskAssessment, Transaction
from shared.schemas import HealthResponse


router = APIRouter()

logger = logging.getLogger("analytics-service")


def _get_request_id(request: Request) -> str:
    header = request.headers.get("X-Request-ID")
    if header:
        return header
    return f"analytics-{datetime.utcnow().isoformat()}"


@router.get("/health", response_model=HealthResponse, summary="Analytics service health check")
async def health(
    settings: AnalyticsServiceSettings = Depends(settings_dependency),
) -> HealthResponse:
    return HealthResponse(status="ok", service=settings.service_name, version=settings.service_version)


@router.get("/api/v1/analytics/summary", response_model=Envelope)
async def analytics_summary(
    request: Request,
    user=Depends(require_roles(["admin", "analyst"])),
    db: AsyncSession = Depends(get_db_session),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    decision: Optional[str] = Query(default=None),
    merchant_category: Optional[str] = Query(default=None),
    external_id: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
) -> Envelope:
    if country is not None:
        raise HTTPException(status_code=400, detail="country filter is not supported in this phase")

    request_id = _get_request_id(request)

    tx_stmt = select(func.count(Transaction.id))

    if start_date is not None:
        tx_stmt = tx_stmt.where(Transaction.occurred_at >= start_date)
    if end_date is not None:
        tx_stmt = tx_stmt.where(Transaction.occurred_at <= end_date)
    if external_id is not None:
        tx_stmt = tx_stmt.where(Transaction.external_id == external_id)

    if merchant_category is not None:
        tx_stmt = tx_stmt.join(Merchant).where(Merchant.category == merchant_category)

    total_transactions = (await db.execute(tx_stmt)).scalar_one()

    ra_base = select(func.count(RiskAssessment.id)).join(
        Transaction, RiskAssessment.transaction_id == Transaction.id
    )

    if start_date is not None:
        ra_base = ra_base.where(Transaction.occurred_at >= start_date)
    if end_date is not None:
        ra_base = ra_base.where(Transaction.occurred_at <= end_date)
    if external_id is not None:
        ra_base = ra_base.where(Transaction.external_id == external_id)
    if merchant_category is not None:
        ra_base = ra_base.join(Merchant).where(Merchant.category == merchant_category)
    if risk_level is not None:
        ra_base = ra_base.where(RiskAssessment.risk_level == risk_level)
    if decision is not None:
        ra_base = ra_base.where(RiskAssessment.decision == decision)

    total_assessed = (await db.execute(ra_base)).scalar_one()

    counts = {}
    for level in ("low", "medium", "high"):
        stmt = ra_base.where(RiskAssessment.risk_level == level)
        counts[level] = (await db.execute(stmt)).scalar_one()

    data = AnalyticsSummary(
        total_transactions=total_transactions,
        total_assessed=total_assessed,
        high_risk_count=counts["high"],
        medium_risk_count=counts["medium"],
        low_risk_count=counts["low"],
    )

    logger.info("analytics_summary computed", extra={"request_id": request_id})
    return Envelope(request_id=request_id, data=data, error=None)


@router.get("/api/v1/analytics/risk-distribution", response_model=Envelope)
async def analytics_risk_distribution(
    request: Request,
    user=Depends(require_roles(["admin", "analyst"])),
    db: AsyncSession = Depends(get_db_session),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    decision: Optional[str] = Query(default=None),
    merchant_category: Optional[str] = Query(default=None),
    external_id: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
) -> Envelope:
    if country is not None:
        raise HTTPException(status_code=400, detail="country filter is not supported in this phase")

    request_id = _get_request_id(request)

    stmt = (
        select(RiskAssessment.risk_level, func.count(RiskAssessment.id))
        .join(Transaction, RiskAssessment.transaction_id == Transaction.id)
        .group_by(RiskAssessment.risk_level)
    )

    if start_date is not None:
        stmt = stmt.where(Transaction.occurred_at >= start_date)
    if end_date is not None:
        stmt = stmt.where(Transaction.occurred_at <= end_date)
    if external_id is not None:
        stmt = stmt.where(Transaction.external_id == external_id)
    if merchant_category is not None:
        stmt = stmt.join(Merchant).where(Merchant.category == merchant_category)
    if risk_level is not None:
        stmt = stmt.where(RiskAssessment.risk_level == risk_level)
    if decision is not None:
        stmt = stmt.where(RiskAssessment.decision == decision)

    result = await db.execute(stmt)
    buckets = [
        RiskDistributionBucket(risk_level=row[0], count=row[1]) for row in result.all()
    ]

    logger.info("analytics_risk_distribution computed", extra={"request_id": request_id})
    return Envelope(request_id=request_id, data=buckets, error=None)


@router.get("/api/v1/analytics/volume-by-day", response_model=Envelope)
async def analytics_volume_by_day(
    request: Request,
    user=Depends(require_roles(["admin", "analyst"])),
    db: AsyncSession = Depends(get_db_session),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    decision: Optional[str] = Query(default=None),
    merchant_category: Optional[str] = Query(default=None),
    external_id: Optional[str] = Query(default=None),
    country: Optional[str] = Query(default=None),
) -> Envelope:
    if country is not None:
        raise HTTPException(status_code=400, detail="country filter is not supported in this phase")

    request_id = _get_request_id(request)

    day = func.date(Transaction.occurred_at)
    stmt = (
        select(
            day.label("day"),
            func.count(Transaction.id).label("tx_count"),
            func.count(RiskAssessment.id).label("assessed_count"),
        )
        .select_from(Transaction)
        .outerjoin(RiskAssessment, RiskAssessment.transaction_id == Transaction.id)
        .group_by(day)
        .order_by(day)
    )

    if start_date is not None:
        stmt = stmt.where(Transaction.occurred_at >= start_date)
    if end_date is not None:
        stmt = stmt.where(Transaction.occurred_at <= end_date)
    if external_id is not None:
        stmt = stmt.where(Transaction.external_id == external_id)
    if merchant_category is not None:
        stmt = stmt.join(Merchant).where(Merchant.category == merchant_category)
    if risk_level is not None:
        stmt = stmt.where(RiskAssessment.risk_level == risk_level)
    if decision is not None:
        stmt = stmt.where(RiskAssessment.decision == decision)

    result = await db.execute(stmt)
    buckets = [
        VolumeByDayBucket(
            date=row.day,
            transaction_count=row.tx_count,
            assessed_count=row.assessed_count,
        )
        for row in result.all()
    ]

    logger.info("analytics_volume_by_day computed", extra={"request_id": request_id})
    return Envelope(request_id=request_id, data=buckets, error=None)


@router.get("/api/v1/analytics/top-risk-merchants", response_model=Envelope)
async def analytics_top_risk_merchants(
    request: Request,
    user=Depends(require_roles(["admin", "analyst"])),
    db: AsyncSession = Depends(get_db_session),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    decision: Optional[str] = Query(default=None),
    merchant_category: Optional[str] = Query(default=None),
    external_id: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    country: Optional[str] = Query(default=None),
) -> Envelope:
    if country is not None:
        raise HTTPException(status_code=400, detail="country filter is not supported in this phase")

    request_id = _get_request_id(request)

    stmt = (
        select(
            Merchant.external_id,
            func.count(Transaction.id).label("tx_count"),
            func.sum(
                func.case((RiskAssessment.risk_level == "high", 1), else_=0)
            ).label("high_risk_count"),
            func.avg(RiskAssessment.risk_score).label("avg_score"),
        )
        .select_from(Merchant)
        .join(Transaction, Transaction.merchant_id == Merchant.id)
        .join(RiskAssessment, RiskAssessment.transaction_id == Transaction.id)
        .group_by(Merchant.external_id)
        .order_by(func.avg(RiskAssessment.risk_score).desc())
        .limit(limit)
    )

    if start_date is not None:
        stmt = stmt.where(Transaction.occurred_at >= start_date)
    if end_date is not None:
        stmt = stmt.where(Transaction.occurred_at <= end_date)
    if external_id is not None:
        stmt = stmt.where(Transaction.external_id == external_id)
    if merchant_category is not None:
        stmt = stmt.where(Merchant.category == merchant_category)
    if risk_level is not None:
        stmt = stmt.where(RiskAssessment.risk_level == risk_level)
    if decision is not None:
        stmt = stmt.where(RiskAssessment.decision == decision)

    result = await db.execute(stmt)
    merchants = [
        TopRiskMerchant(
            merchant_external_id=row.external_id,
            transaction_count=row.tx_count,
            high_risk_count=row.high_risk_count or 0,
            average_risk_score=row.avg_score or 0,
        )
        for row in result.all()
    ]

    logger.info("analytics_top_risk_merchants computed", extra={"request_id": request_id})
    return Envelope(request_id=request_id, data=merchants, error=None)


@router.get("/api/v1/analytics/transactions/search", response_model=Envelope)
async def analytics_transactions_search(
    request: Request,
    user=Depends(require_roles(["admin", "analyst"])),
    db: AsyncSession = Depends(get_db_session),
    start_date: Optional[datetime] = Query(default=None),
    end_date: Optional[datetime] = Query(default=None),
    risk_level: Optional[str] = Query(default=None),
    decision: Optional[str] = Query(default=None),
    merchant_category: Optional[str] = Query(default=None),
    external_id: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    country: Optional[str] = Query(default=None),
) -> Envelope:
    if country is not None:
        raise HTTPException(status_code=400, detail="country filter is not supported in this phase")

    request_id = _get_request_id(request)

    base_stmt = (
        select(
            Transaction.external_id,
            Transaction.amount,
            Transaction.currency,
            Transaction.occurred_at,
            RiskAssessment.risk_level,
            RiskAssessment.decision,
        )
        .select_from(Transaction)
        .outerjoin(RiskAssessment, RiskAssessment.transaction_id == Transaction.id)
    )

    count_stmt = select(func.count(Transaction.id)).select_from(Transaction).outerjoin(
        RiskAssessment, RiskAssessment.transaction_id == Transaction.id
    )

    if start_date is not None:
        base_stmt = base_stmt.where(Transaction.occurred_at >= start_date)
        count_stmt = count_stmt.where(Transaction.occurred_at >= start_date)
    if end_date is not None:
        base_stmt = base_stmt.where(Transaction.occurred_at <= end_date)
        count_stmt = count_stmt.where(Transaction.occurred_at <= end_date)
    if external_id is not None:
        base_stmt = base_stmt.where(Transaction.external_id == external_id)
        count_stmt = count_stmt.where(Transaction.external_id == external_id)
    if merchant_category is not None:
        base_stmt = base_stmt.join(Merchant).where(Merchant.category == merchant_category)
        count_stmt = count_stmt.join(Merchant).where(Merchant.category == merchant_category)
    if risk_level is not None:
        base_stmt = base_stmt.where(RiskAssessment.risk_level == risk_level)
        count_stmt = count_stmt.where(RiskAssessment.risk_level == risk_level)
    if decision is not None:
        base_stmt = base_stmt.where(RiskAssessment.decision == decision)
        count_stmt = count_stmt.where(RiskAssessment.decision == decision)

    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    base_stmt = base_stmt.order_by(Transaction.occurred_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(base_stmt)
    items = [
        TransactionSearchItem(
            transaction_external_id=row.external_id,
            account_external_id="",
            merchant_external_id=None,
            amount=row.amount,
            currency=row.currency,
            occurred_at=row.occurred_at,
            risk_level=row.risk_level,
            decision=row.decision,
        )
        for row in result.all()
    ]

    data = TransactionSearchResult(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )

    logger.info("analytics_transactions_search computed", extra={"request_id": request_id})
    return Envelope(request_id=request_id, data=data, error=None)
