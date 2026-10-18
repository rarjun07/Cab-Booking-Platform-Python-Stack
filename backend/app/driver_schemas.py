"""Driver-owned inputs and minimal matching responses."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.ride_schemas import Coordinate, RidePublic


class VehicleInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    make: str = Field(min_length=2, max_length=50)
    model: str = Field(min_length=1, max_length=50)
    plate: str = Field(min_length=3, max_length=20)

    @field_validator("make", "model", "plate")
    @classmethod
    def safe_vehicle_text(cls, value):
        if "\x00" in value:
            raise ValueError("Vehicle details cannot contain a null character.")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("Use valid Unicode text in vehicle details.") from None
        return value


class DriverProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    vehicle_info: VehicleInfo


class AvailabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["active", "offline"]
    location: Coordinate | None = None

    @model_validator(mode="after")
    def active_requires_location(self):
        if self.status == "active" and self.location is None:
            raise ValueError("Provide your current location to go online.")
        return self


class DriverPublic(BaseModel):
    user_id: UUID
    vehicle_info: dict
    verified: bool
    status: str
    current_location: Coordinate | None
    location_updated_at: datetime | None
    location_expires_at: datetime | None
    available_for_matching: bool


class NearbyDriver(BaseModel):
    driver_id: UUID
    name: str
    vehicle_info: dict
    verified: bool
    distance_meters: int


class RideOffer(BaseModel):
    ride: RidePublic
    pickup_distance_meters: int


class DriverLocationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: Coordinate


class TripStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["arriving", "in_progress", "completed"]


class DriverLocationPublic(BaseModel):
    driver_id: UUID
    ride_id: UUID
    location: Coordinate | None
    updated_at: datetime | None
    expires_at: datetime | None
