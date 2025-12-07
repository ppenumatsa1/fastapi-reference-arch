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
    )

    app_name: str = "todo-api"
    api_prefix: str = "/api/v1"
    app_env: str = "development"
    app_debug: bool = True

    database_host: str = "postgres"
    database_port: int = 5432
    database_user: str = "todo_user"
    database_password: str = "todo_pass"
    database_name: str = "todo_db"
    database_echo: bool = False
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")
    async_database_url_override: str | None = Field(
        default=None,
        alias="ASYNC_DATABASE_URL",
    )
    log_level: str = "INFO"

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg2://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def async_database_url(self) -> str:
        if self.async_database_url_override:
            return self.async_database_url_override
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
