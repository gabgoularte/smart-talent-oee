from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:password@localhost:5432/oeedb"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    model_path: str = "./modelo_manutencao.joblib"
    limiar_atencao: float = Field(default=0.30, ge=0, le=1)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
