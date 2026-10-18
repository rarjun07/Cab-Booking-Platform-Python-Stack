"""Local configuration, loaded from backend/.env or environment variables."""

from functools import lru_cache
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import EmailStr, Field, HttpUrl, SecretStr, field_validator, model_validator
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
    redis_url: SecretStr = SecretStr("redis://127.0.0.1:6379/0")
    rate_limit_prefix: str = Field(default="cab_booking:limits:v1", pattern=r"^[a-zA-Z0-9:_-]{1,80}$")
    max_request_body_bytes: int = Field(default=65536, ge=16384, le=1048576)
    realtime_channel_prefix: str = Field(default="cab_booking:realtime:v1", pattern=r"^[a-zA-Z0-9:_-]{1,80}$")
    websocket_session_check_seconds: float = Field(default=2.0, ge=0.1, le=10)
    websocket_sync_seconds: float = Field(default=15.0, ge=1, le=60)
    stripe_secret_key: SecretStr | None = None
    stripe_publishable_key: str | None = None
    stripe_webhook_secret: SecretStr | None = None
    receipt_email_enabled: bool = False
    celery_broker_url: SecretStr | None = None
    celery_key_prefix: str = Field(default="cab_booking:tasks:v1:", pattern=r"^[a-zA-Z0-9:_-]{1,80}$")
    smtp_host: str = Field(default="127.0.0.1", min_length=1, max_length=253)
    smtp_port: int = Field(default=1025, ge=1, le=65535)
    smtp_starttls: bool = True
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: EmailStr = "receipts@example.com"
    allowed_origins: list[str] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]

    @field_validator("allowed_origins")
    @classmethod
    def explicit_origins(cls, values):
        if not 1 <= len(values) <= 20:
            raise ValueError("Configure 1-20 explicit HTTP(S) origins.")
        normalized = []
        for value in values:
            try:
                parts = urlsplit(value)
                port = parts.port
                if (parts.scheme not in {"http", "https"} or not parts.hostname or parts.username is not None
                        or parts.password is not None or parts.path or parts.query or parts.fragment
                        or "*" in value or not value.isascii() or any(char.isspace() for char in value)):
                    raise ValueError
                host = parts.hostname.lower()
                if ":" in host:
                    host = f"[{host}]"
                origin = f"{parts.scheme}://{host}"
                if port is not None and port != (443 if parts.scheme == "https" else 80):
                    origin += f":{port}"
            except ValueError:
                raise ValueError("Use explicit HTTP(S) origins without wildcards, credentials, paths or query strings.") from None
            if origin not in normalized:
                normalized.append(origin)
        return normalized

    @field_validator("jwt_secret")
    @classmethod
    def reject_example_secret(cls, value: SecretStr) -> SecretStr:
        if value.get_secret_value().startswith("REPLACE_"):
            raise ValueError("Generate a random JWT_SECRET; do not use the example value.")
        return value

    @field_validator("stripe_secret_key")
    @classmethod
    def test_secret_only(cls, value):
        if value is not None and not value.get_secret_value().startswith("sk_test_"):
            raise ValueError("Day 6 accepts only Stripe test secret keys.")
        return value

    @field_validator("stripe_publishable_key")
    @classmethod
    def test_publishable_only(cls, value):
        if value is not None and not value.startswith("pk_test_"):
            raise ValueError("Day 6 accepts only Stripe test publishable keys.")
        return value

    @field_validator("stripe_webhook_secret")
    @classmethod
    def webhook_secret_prefix(cls, value):
        if value is not None and not value.get_secret_value().startswith("whsec_"):
            raise ValueError("Use the signing secret for the test webhook listener.")
        return value

    @model_validator(mode="after")
    def smtp_transport(self):
        if not self.smtp_starttls and self.smtp_host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Unencrypted SMTP is allowed only for a loopback mail catcher.")
        if bool(self.smtp_username) != bool(self.smtp_password):
            raise ValueError("Configure both SMTP_USERNAME and SMTP_PASSWORD, or neither.")
        return self

    @field_validator("smtp_username", "smtp_password", mode="before")
    @classmethod
    def empty_smtp_credentials(cls, value):
        return None if value == "" else value


@lru_cache
def get_settings() -> Settings:
    return Settings()
