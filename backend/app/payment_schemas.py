from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PaymentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaymentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ride_id: UUID
    amount: Decimal
    currency: str
    status: str
    created_at: datetime
    paid_at: datetime | None


class PaymentIntentPublic(BaseModel):
    payment: PaymentPublic
    publishable_key: str
    client_secret: str | None
    stripe_status: str
