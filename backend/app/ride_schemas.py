"""Validated coordinates, signed quote contents, and ride responses."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Coordinate(BaseModel):
    model_config = ConfigDict(frozen=True, allow_inf_nan=False, extra="forbid")
    latitude: float = Field(ge=-90, le=90, strict=True)
    longitude: float = Field(ge=-180, le=180, strict=True)


class RouteMetrics(BaseModel):
    distance_meters: int = Field(gt=0, le=10_000_000)
    duration_secs: int = Field(gt=0, le=604800)


class FareBreakdown(BaseModel):
    base_fare: Decimal
    distance_charge: Decimal
    time_charge: Decimal
    minimum_adjustment: Decimal
    total: Decimal


class QuoteContents(RouteMetrics):
    pickup: Coordinate
    destination: Coordinate
    fare_estimate: Decimal = Field(ge=0, le=Decimal("99999999.99"), decimal_places=2)
    currency: Literal["INR"] = "INR"


class FareEstimate(QuoteContents):
    quote_token: str
    expires_at: datetime
    breakdown: FareBreakdown
    routing_provider: str = "OSRM"


class RideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    quote_token: str = Field(min_length=1, max_length=4096, repr=False)


class RidePublic(QuoteContents):
    distance_meters: int | None = Field(default=None, ge=0)
    duration_secs: int | None = Field(default=None, ge=0)
    id: UUID
    status: str
    driver_id: UUID | None
    created_at: datetime
