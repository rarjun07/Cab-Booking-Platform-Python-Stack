"""Only a rating/comment is accepted; account and recipient IDs stay server-owned."""
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    rating: int = Field(ge=1, le=5, strict=True)
    comment: str | None = Field(default=None, max_length=2000)

    @field_validator("comment")
    @classmethod
    def blank_comment(cls, value):
        if value is not None:
            if "\x00" in value:
                raise ValueError("Comments cannot contain a null character.")
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                raise ValueError("Use valid Unicode text in the comment.") from None
        return value or None


class ReviewPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    rater_id: UUID
    rated_id: UUID
    rating: int
    comment: str | None
    created_at: datetime | None


class RatingSummary(BaseModel):
    user_id: UUID
    name: str
    role: Literal["rider", "driver"]
    average: Decimal | None
    count: int


class TripReviews(BaseModel):
    counterpart: RatingSummary | None
    submitted: ReviewPublic | None
    received: ReviewPublic | None
    can_review: bool
    reason: str | None = None
