"""Local configuration, loaded from backend/.env or environment variables."""

from functools import lru_cache
from decimal import Decimal
from pathlib import Path

from pydantic import Field, HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        extra="ignore",
        hide_input_in_errors=True,
    )

    database_url: SecretStr
    jwt_secret: SecretStr = Field(min_length=48)
    cookie_secure: bool = True
    access_token_minutes: int = Field(default=30, ge=1, le=120)
    osrm_base_url: HttpUrl = "https://router.project-osrm.org"
    quote_lifetime_seconds: int = Field(default=300, ge=60, le=900)
    fare_base: Decimal = Field(default=Decimal("50.00"), ge=0, le=10000, decimal_places=2)
    fare_per_km: Decimal = Field(default=Decimal("12.00"), ge=0, le=1000, decimal_places=2)
    fare_per_minute: Decimal = Field(default=Decimal("1.00"), ge=0, le=100, decimal_places=2)
    fare_minimum: Decimal = Field(default=Decimal("80.00"), ge=0, le=10000, decimal_places=2)
    matching_radius_meters: int = Field(default=5000, ge=100, le=50000)
    driver_location_max_age_seconds: int = Field(default=300, ge=60, le=3600)
    allowed_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]

    @field_validator("jwt_secret")
    @classmethod
    def reject_example_secret(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value().startswith("REPLACE_"):
            raise ValueError("Generate a random JWT_SECRET; do not use the example value.")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
