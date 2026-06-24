import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    database_url: str | None = None
    events_provider_base_url: str = "https://events-provider.dev-2.python-labs.ru"
    events_provider_api_key: str = (
        "EFyEe5G6vy1GLV8khDYwDSndSKYo0UMPYRZszM6Pxm0"
    )

    def __init__(self, **kwargs):
        if not kwargs.get("database_url"):
            conn_string = os.getenv("POSTGRES_CONNECTION_STRING")
            if conn_string:
                kwargs["database_url"] = conn_string.replace(
                    "postgres://", "postgresql+asyncpg://", 1
                )
            else:
                db_host = os.getenv("POSTGRES_HOST", "localhost")
                db_port = os.getenv("POSTGRES_PORT", "5432")
                db_name = os.getenv("POSTGRES_DATABASE_NAME", "events")
                db_user = os.getenv("POSTGRES_USERNAME", "postgres")
                db_password = os.getenv("POSTGRES_PASSWORD", "postgres")
                kwargs["database_url"] = (
                    f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
                )
        super().__init__(**kwargs)


settings = Settings()
