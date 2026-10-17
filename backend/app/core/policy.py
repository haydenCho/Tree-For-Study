"""서버 권위 정책 상수와 순수 계산 함수.

프론트엔드의 SessionPolicy와 같은 규칙을 서버에서 독립적으로 구현한다.
결과는 항상 서버 값이 권위다(docs/01-product-plan.md §3).
"""
SPECIES = ("oak", "fir", "cherry", "ginkgo", "willow", "blossom")

FOCUS_MIN_MINUTES = 20
FOCUS_MAX_MINUTES = 180
REST_MIN_MINUTES = 1
REST_MAX_MINUTES = 60

REWARD_UNIT_SECONDS = 1200  # 20분당 한 그루
LARGE_THRESHOLD_SECONDS = 3000  # 50분 이상은 큰 나무

ZONE_SIZE = 6  # 6×6 구역


def tree_count(target_seconds: int) -> int:
    """count = floor(target_seconds / 1200)."""
    return target_seconds // REWARD_UNIT_SECONDS


def tree_size(target_seconds: int) -> str:
    """size = large if target_seconds >= 3000 else small."""
    return "large" if target_seconds >= LARGE_THRESHOLD_SECONDS else "small"


def validate_focus_minutes(minutes: int) -> None:
    if not isinstance(minutes, int) or not FOCUS_MIN_MINUTES <= minutes <= FOCUS_MAX_MINUTES:
        raise ValueError(f"공부 시간은 {FOCUS_MIN_MINUTES}~{FOCUS_MAX_MINUTES}분 정수여야 합니다.")


def validate_rest_minutes(minutes: int) -> None:
    if not isinstance(minutes, int) or not REST_MIN_MINUTES <= minutes <= REST_MAX_MINUTES:
        raise ValueError(f"휴식 시간은 {REST_MIN_MINUTES}~{REST_MAX_MINUTES}분 정수여야 합니다.")
