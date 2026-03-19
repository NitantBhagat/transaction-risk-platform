from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TransactionIngestedEvent(BaseModel):
    """
    Canonical event representing a transaction that should enter the risk pipeline.
    """

    event_id: str = Field(..., description="Unique identifier for this ingestion event")

    transaction_external_id: str = Field(..., description="External transaction identifier")
    account_external_id: str = Field(..., description="External account identifier")
    merchant_external_id: Optional[str] = Field(
        default=None, description="External merchant identifier, if available"
    )

    amount: Decimal = Field(..., description="Transaction amount in minor or major units")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO currency code")

    occurred_at: datetime = Field(..., description="When the transaction occurred in the source")

    transaction_id: Optional[int] = Field(
        default=None, description="Internal transaction identifier, if available"
    )
    country: Optional[str] = Field(
        default=None, description="ISO country code associated with the transaction"
    )
    merchant_category: Optional[str] = Field(
        default=None, description="Merchant category code or label"
    )

