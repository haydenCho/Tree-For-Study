"""주입 가능한 서버 시계.

모든 서버 판정(세션 완료 시각, 토큰 만료, 출석 날짜)은 DB의 now()가 아니라 이 시계를
사용한다. 테스트는 `clock.set()` / `clock.advance()`로 시간을 옮겨 실제 분 단위 대기
없이 검증한다. 운영 코드에는 시간을 조작하는 API를 두지 않는다.
"""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


class Clock:
    def __init__(self) -> None:
        self._fixed: datetime | None = None

    def now(self) -> datetime:
        """항상 UTC aware datetime을 돌려준다."""
        if self._fixed is not None:
            return self._fixed
        return datetime.now(timezone.utc)

    # ── 테스트 전용 조작 ──────────────────────────────────────────
    def set(self, value: datetime) -> None:
        self._fixed = value.astimezone(timezone.utc)

    def advance(self, seconds: float) -> None:
        self._fixed = self.now() + timedelta(seconds=seconds)

    def reset(self) -> None:
        self._fixed = None


clock = Clock()


def utcnow() -> datetime:
    return clock.now()


def kst_today() -> date:
    return clock.now().astimezone(KST).date()


def kst_date_of(value: datetime) -> date:
    return value.astimezone(KST).date()


def kst_day_bounds(day: date) -> tuple[datetime, datetime]:
    """한국 날짜 하루의 [시작, 끝) 경계를 UTC로 돌려준다."""
    start = datetime(day.year, day.month, day.day, tzinfo=KST)
    end = start + timedelta(days=1)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def split_by_kst_date(start: datetime, end: datetime) -> dict[date, int]:
    """[start, end) 구간을 한국 날짜별 초로 나눈다(자정 구간 분할)."""
    result: dict[date, int] = {}
    cursor = start
    while cursor < end:
        day = kst_date_of(cursor)
        _, day_end = kst_day_bounds(day)
        seg_end = min(end, day_end)
        result[day] = result.get(day, 0) + int((seg_end - cursor).total_seconds())
        cursor = seg_end
    return result
