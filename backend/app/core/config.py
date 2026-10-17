"""환경 변수 / 서버 .env에서 불러오는 애플리케이션 설정.

비밀값(JWT_SECRET, DATABASE_URL, POSTGRES_PASSWORD)은 여기서만 읽으며
절대 프론트엔드로 노출하지 않는다. VITE_* 값은 의도적으로 백엔드에서 읽지 않는다.
"""
from datetime import date
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 데이터베이스
    database_url: str = "postgresql+asyncpg://tfs:@db:5432/tree_for_study"
    # 테스트처럼 이벤트 루프가 바뀌는 환경에서는 커넥션 풀을 쓰지 않는다.
    db_nullpool: bool = False

    # JWT / 인증
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "tree-for-study"
    jwt_audience: str = "tree-for-study-web"
    access_ttl_seconds: int = 900
    refresh_ttl_seconds: int = 604800
    # 동시 refresh(여러 탭) 경합을 탈취로 오인하지 않기 위한 짧은 유예(초)
    refresh_race_grace_seconds: int = 10

    # 서버 설정
    # 쉼표로 여러 출처를 허용할 수 있다. CSRF Origin 검사에도 사용한다.
    app_origin: str = "http://localhost:5173"
    cookie_secure: bool = False
    trusted_proxy_ips: str = ""
    tz: str = "Asia/Seoul"

    # 스터디 운영 정책 상수(docs/01-product-plan.md §1, §7)
    study_start: date = date(2026, 10, 20)
    study_end: date = date(2026, 11, 19)
    exam_date: date = date(2026, 11, 20)
    max_active_members: int = 10
    invite_ttl_days: int = 7
    invite_default_max_uses: int = 10

    # 백그라운드 완료 워커(테스트에서는 끈다)
    run_workers: bool = True
    worker_interval_seconds: float = 5.0

    @property
    def trusted_proxy_ip_list(self) -> list[str]:
        return [ip.strip() for ip in self.trusted_proxy_ips.split(",") if ip.strip()]

    @property
    def app_origin_list(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.app_origin.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
