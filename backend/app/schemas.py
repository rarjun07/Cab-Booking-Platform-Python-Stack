"""Validate incoming data and expose only safe user fields."""

from typing import Literal
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, field_validator


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
    phone: str | None = None
    profile_pic: str | None = None


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    profile_pic: HttpUrl | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        return RegisterInput.clean_name(value)

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value):
        if value is None or value == "": return None
        if not isinstance(value, str): raise ValueError("Use an international phone number.")
        value = re.sub(r"[ ()-]", "", value.strip())
        if not value: return None
        if not re.fullmatch(r"\+[1-9][0-9]{7,14}", value):
            raise ValueError("Use an international phone number beginning with + and 8-15 digits.")
        return value

    @field_validator("profile_pic", mode="before")
    @classmethod
    def empty_photo(cls, value):
        return None if isinstance(value, str) and not value.strip() else value

    @field_validator("profile_pic")
    @classmethod
    def safe_photo_url(cls, value):
        if value is not None and (value.scheme != "https" or not value.host or value.username is not None
                                  or value.password is not None or len(str(value)) > 2048):
            raise ValueError("Use an HTTPS image URL without embedded credentials, up to 2048 characters.")
        return value
