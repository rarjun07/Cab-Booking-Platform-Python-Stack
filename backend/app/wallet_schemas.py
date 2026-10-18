from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PromoInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    code: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9]+$")

    @field_validator("code")
    @classmethod
    def normalize(cls, value):
        return value.upper()


class PromoPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    base_amount: Decimal
    discount_amount: Decimal
    final_amount: Decimal


class TopupInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    amount: Decimal = Field(ge=50, le=10000, decimal_places=2)
    request_key: UUID


class TopupPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    amount: Decimal
    currency: str
    status: str
    created_at: datetime
    credited_at: datetime | None


class TopupIntentPublic(BaseModel):
    topup: TopupPublic
    publishable_key: str
    client_secret: str | None
    stripe_status: str


class EntryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    topup_id: UUID
    amount: Decimal
    created_at: datetime


class WalletPublic(BaseModel):
    balance: Decimal
    currency: str = "inr"
    entries: list[EntryPublic]
    topups: list[TopupPublic]
