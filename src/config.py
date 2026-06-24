from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/events"
    events_provider_base_url: str = (
        "http://student-system-events-provider-web.student-system-events-provider.svc:8000"
    )
    events_provider_api_key: str


settings = Settings()
