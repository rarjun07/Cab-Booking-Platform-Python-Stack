"""Private history pages and minimal receipt queue status."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ride_schemas import RidePublic


class HistoryRide(RidePublic):
    fare_actual: Decimal | None
    payment_status: str | None
    payment_amount: Decimal | None
    receipt_available: bool


class HistoryPage(BaseModel):
    items: list[HistoryRide]
    next_cursor: UUID | None


class EmailReceiptInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReceiptEmailPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: Literal["queued", "sent", "failed"]
    attempts: int
    created_at: datetime
    sent_at: datetime | None
