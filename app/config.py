from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    api_key: str = Field(..., alias="API_KEY", min_length=1)
    database_path: str = Field("./data/aggregator.db", alias="DATABASE_PATH")
    refresh_interval_minutes: int = Field(30, alias="REFRESH_INTERVAL_MINUTES", ge=1)
    rate_limit_per_minute: int = Field(60, alias="RATE_LIMIT_PER_MINUTE", ge=1)
    # Comma-separated list of extra origins allowed to call the API from a browser.
    cors_origins_raw: str = Field("", alias="CORS_ORIGINS")

    @property
    def cors_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]


settings = Settings()
