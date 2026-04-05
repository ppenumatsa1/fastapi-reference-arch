"""Application configuration powered by Pydantic settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "user-api"
    api_prefix: str = "/api/v1"
    app_env: str = "development"
    app_debug: bool = True

    # Database connection settings
    db_auth_mode: str = Field(default="password", alias="DB_AUTH_MODE")
    database_host: str = "localhost"
    database_port: int = 5432
    database_user: str = "user_user"
    database_password: str = "user_pass"
    database_name: str = "user_db"
    azure_client_id: str | None = Field(default=None, alias="AZURE_CLIENT_ID")
    database_echo: bool = False
    database_pool_size: int = Field(default=5, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, alias="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=1800, alias="DATABASE_POOL_RECYCLE")
    database_pool_pre_ping: bool = Field(default=True, alias="DATABASE_POOL_PRE_PING")
    entra_db_token_lifetime_seconds: int = Field(
        default=3600,
        alias="ENTRA_DB_TOKEN_LIFETIME_SECONDS",
    )
    entra_db_token_refresh_skew_seconds: int = Field(
        default=300,
        alias="ENTRA_DB_TOKEN_REFRESH_SKEW_SECONDS",
    )
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")
    async_database_url_override: str | None = Field(
        default=None,
        alias="ASYNC_DATABASE_URL",
    )

    # Application Insights
    applicationinsights_connection_string: str | None = None
    enable_telemetry: bool = Field(default=False, alias="ENABLE_TELEMETRY")

    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        """Sync database URL (used by Alembic)."""
        if self.database_url_override:
            return self.database_url_override

        if self.use_entra_db_auth:
            return (
                f"postgresql+psycopg2://{self.database_user}@"
                f"{self.database_host}:{self.database_port}/{self.database_name}"
            )

        return (
            f"postgresql+psycopg2://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def async_database_url(self) -> str:
        """Async database URL (used by application runtime)."""
        if self.async_database_url_override:
            return self.async_database_url_override

        if self.use_entra_db_auth:
            return (
                f"postgresql+asyncpg://{self.database_user}@"
                f"{self.database_host}:{self.database_port}/{self.database_name}"
            )

        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def use_entra_db_auth(self) -> bool:
        return self.db_auth_mode.lower() in {"aad", "entra"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
