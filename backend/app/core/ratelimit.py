"""단일 프로세스용 고정 창 속도 제한(로그인·가입·초대 사용 남용 방지).

10명 규모 단일 API 인스턴스를 전제로 메모리에 보관한다. 여러 인스턴스로 늘리면
DB나 외부 저장소 기반으로 바꿔야 한다.
"""
import threading

from app.core.clock import utcnow


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> list[float]:
        return [t for t in self._hits.get(key, []) if now - t < self.window]

    def allowed(self, key: str) -> bool:
        """기록하지 않고 현재 창에서 한도 미만인지 확인한다."""
        now = utcnow().timestamp()
        with self._lock:
            hits = self._recent(key, now)
            self._hits[key] = hits
            return len(hits) < self.limit

    def record(self, key: str) -> None:
        now = utcnow().timestamp()
        with self._lock:
            hits = self._recent(key, now)
            hits.append(now)
            self._hits[key] = hits

    def hit(self, key: str) -> bool:
        """허용되면 True. 창 안에서 limit를 넘으면 False."""
        now = utcnow().timestamp()
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < self.window]
            if len(hits) >= self.limit:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# 로그인은 '실패'만 센다. 도서관처럼 여러 멤버가 같은 공인 IP(NAT)를 공유하므로
# IP 한도는 넉넉히, 계정(이메일) 한도는 엄격히 둔다.
login_ip_limiter = RateLimiter(limit=30, window_seconds=300)
login_limiter = RateLimiter(limit=10, window_seconds=300)
register_limiter = RateLimiter(limit=20, window_seconds=600)
