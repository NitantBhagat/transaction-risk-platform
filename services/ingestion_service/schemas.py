from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class TransactionCreateRequest(BaseModel):
    transaction_external_id: str = Field(..., max_length=64)
    account_external_id: str = Field(..., max_length=64)
    merchant_external_id: str | None = Field(default=None, max_length=64)

    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)

    occurred_at: datetime
    country: str | None = Field(default=None, max_length=2)
    merchant_category: str | None = Field(default=None, max_length=64)


class TransactionResource(BaseModel):
    id: int
    external_id: str
    account_external_id: str
    merchant_external_id: str | None
    amount: Decimal
    currency: str
    occurred_at: datetime
    status: str


class TransactionCreateResponse(BaseModel):
    request_id: str
    data: TransactionResource | None = None
    error: str | None = None

