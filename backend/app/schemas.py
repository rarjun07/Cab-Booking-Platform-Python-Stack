"""Validate incoming data and expose only safe user fields."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=1, max_length=128, repr=False)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class RegisterInput(LoginInput):
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=12, max_length=128, repr=False)
    role: Literal["rider", "driver"] = "rider"

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name cannot be blank.")
        if "\x00" in value:
            raise ValueError("Name cannot contain a null character.")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("Use valid Unicode text in the name.") from None
        return value.strip()


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    role: Literal["rider", "driver"]
