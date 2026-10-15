"""Local configuration, loaded from backend/.env or environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
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
