"""Application configuration using Pydantic Settings.

This module provides centralized configuration management with:
- Environment variable loading with prefixes
- Type validation and coercion
- Sensible defaults for development
- Clear documentation for each setting

Usage:
    from async_task_q_monitor.config import get_settings

    settings = get_settings()
    print(settings.cors_origins)
"""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables with the
    prefix 'MONITOR_'. For example, 'MONITOR_DEBUG=true' sets debug mode.

    Attributes:
        debug: Enable debug mode with verbose logging.
        host: Host address for the API server.
        port: Port for the API server.
        cors_origins: Comma-separated list of allowed CORS origins.
        enable_auth: Enable JWT authentication (disable for local dev).
        secret_key: Secret key for JWT signing (required if auth enabled).
        polling_interval_seconds: How often to poll drivers for updates.
        metrics_retention_days: How long to keep historical metrics.
        websocket_heartbeat_seconds: WebSocket ping interval.

    """

    model_config = SettingsConfigDict(
        env_prefix="MONITOR_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server Configuration
    debug: bool = Field(
        default=False,
        description="Enable debug mode with verbose logging",
    )
    host: str = Field(
        default="127.0.0.1",
        description="Host address for the API server",
    )
    port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="Port for the API server",
    )

    # CORS Configuration
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins (comma-separated in env)",
    )

    # Authentication
    enable_auth: bool = Field(
        default=False,
        description="Enable JWT authentication",
    )
    secret_key: str | None = Field(
        default=None,
        description="Secret key for JWT signing (required if auth enabled)",
        min_length=32,
    )

    # Polling & Real-time
    polling_interval_seconds: int = Field(
        default=5,
        ge=1,
        le=60,
        description="How often to poll drivers for metric updates",
    )
    websocket_heartbeat_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="WebSocket ping interval for connection health",
    )

    # Metrics Storage
    metrics_retention_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="How long to keep historical metrics data",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated CORS origins from environment variable."""
        if isinstance(v, str):
            # Handle comma-separated string from env
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("log_level", mode="before")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Normalize log level to uppercase."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        normalized = v.upper()
        if normalized not in valid_levels:
            msg = f"Invalid log level: {v}. Must be one of {valid_levels}"
            raise ValueError(msg)
        return normalized


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Settings are loaded once and cached for the lifetime of the application.
    Use this function instead of instantiating Settings directly.

    Returns:
        Configured Settings instance.

    Example:
        >>> settings = get_settings()
        >>> settings.debug
        False
    """
    return Settings()
