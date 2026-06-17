from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CARBEEP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    BOT_TOKEN: SecretStr

    # Delimobil
    REGION_ID: int = 16
    POLL_INTERVAL: int = 15
    NOTIFY_TTL_MINUTES: int = 30

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "carbeep"
    POSTGRES_USER: str = "carbeep"
    POSTGRES_PASSWORD: SecretStr = SecretStr("carbeep")
    POSTGRES_MIN_CONNECTIONS: int = 1
    POSTGRES_MAX_CONNECTIONS: int = 5

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD.get_secret_value()}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    REGIONS: dict[int, str] = {
        1: "Москва", 2: "Санкт-Петербург", 4: "Нижний Новгород",
        5: "Екатеринбург", 6: "Новосибирск", 7: "Самара",
        9: "Краснодар", 12: "Ростов-на-Дону", 14: "Казань",
        15: "Сочи", 16: "Ярославль", 29: "Челябинск",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
