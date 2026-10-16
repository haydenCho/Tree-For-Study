"""Application settings loaded from environment / server .env.

Secrets (JWT_SECRET, DATABASE_URL, POSTGRES_PASSWORD) are read here and must never
be exposed to the frontend. VITE_* values are intentionally NOT read by the backend.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://tfs:@db:5432/tree_for_study"

    # JWT / auth
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "tree-for-study"
    jwt_audience: str = "tree-for-study-web"
    access_ttl_seconds: int = 900
    refresh_ttl_seconds: int = 604800

    # Server config
    app_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    trusted_proxy_ips: str = ""
    tz: str = "Asia/Seoul"

    @property
    def trusted_proxy_ip_list(self) -> list[str]:
        return [ip.strip() for ip in self.trusted_proxy_ips.split(",") if ip.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
