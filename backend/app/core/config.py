"""환경 변수 / 서버 .env에서 불러오는 애플리케이션 설정.

비밀값(JWT_SECRET, DATABASE_URL, POSTGRES_PASSWORD)은 여기서만 읽으며
절대 프론트엔드로 노출하지 않는다. VITE_* 값은 의도적으로 백엔드에서 읽지 않는다.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 데이터베이스
    database_url: str = "postgresql+asyncpg://tfs:@db:5432/tree_for_study"

    # JWT / 인증
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "tree-for-study"
    jwt_audience: str = "tree-for-study-web"
    access_ttl_seconds: int = 900
    refresh_ttl_seconds: int = 604800

    # 서버 설정
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
