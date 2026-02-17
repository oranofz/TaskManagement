"""Application configuration module."""
import os
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # Redis
    redis_url: str = Field(..., alias="REDIS_URL")

    # Security
    secret_key: str = Field(..., alias="SECRET_KEY")
    jwt_private_key_path: str = Field(..., alias="JWT_PRIVATE_KEY_PATH")
    jwt_public_key_path: str = Field(..., alias="JWT_PUBLIC_KEY_PATH")
    jwt_algorithm: str = Field(default="RS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Application
    environment: str = Field(default="development", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # CORS - will be parsed from comma-separated string
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    # Rate Limiting
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")

    # HaveIBeenPwned
    haveibeenpwned_api_key: Optional[str] = Field(default=None, alias="HAVEIBEENPWNED_API_KEY")

    # OpenTelemetry / Distributed Tracing
    otlp_endpoint: Optional[str] = Field(default=None, alias="OTLP_ENDPOINT")
    otel_service_name: str = Field(default="task-management-system", alias="OTEL_SERVICE_NAME")
    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def jwt_private_key(self) -> str:
        """Load JWT private key from file."""
        if not os.path.exists(self.jwt_private_key_path):
            raise FileNotFoundError(f"JWT private key not found: {self.jwt_private_key_path}")
        with open(self.jwt_private_key_path, "r") as f:
            return f.read()

    @property
    def jwt_public_key(self) -> str:
        """Load JWT public key from file."""
        if not os.path.exists(self.jwt_public_key_path):
            raise FileNotFoundError(f"JWT public key not found: {self.jwt_public_key_path}")
        with open(self.jwt_public_key_path, "r") as f:
            return f.read()


def get_settings() -> Settings:
    """Get application settings singleton."""
    return Settings()


settings = get_settings()
