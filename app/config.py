from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str = Field(..., alias="API_KEY")
    database_path: str = Field("./data/aggregator.db", alias="DATABASE_PATH")
    refresh_interval_minutes: int = Field(30, alias="REFRESH_INTERVAL_MINUTES")
    rate_limit_per_minute: int = Field(10, alias="RATE_LIMIT_PER_MINUTE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
