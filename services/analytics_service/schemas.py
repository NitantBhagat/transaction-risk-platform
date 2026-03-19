from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class AnalyticsSummary(BaseModel):
    total_transactions: int
    total_assessed: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


class RiskDistributionBucket(BaseModel):
    risk_level: str
    count: int


class VolumeByDayBucket(BaseModel):
    date: date
    transaction_count: int
    assessed_count: int


class TopRiskMerchant(BaseModel):
    merchant_external_id: str
    transaction_count: int
    high_risk_count: int
    average_risk_score: Decimal


class TransactionSearchItem(BaseModel):
    transaction_external_id: str
    account_external_id: str
    merchant_external_id: Optional[str]
    amount: Decimal
    currency: str
    occurred_at: datetime
    risk_level: Optional[str]
    decision: Optional[str]


class TransactionSearchResult(BaseModel):
    items: List[TransactionSearchItem]
    page: int
    page_size: int
    total: int


class Envelope(BaseModel):
    request_id: str
    data: object | None
    error: Optional[str] = None

