"""순수 정책 함수: 보상 경계와 KST 자정 분할."""
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.core.clock import split_by_kst_date
from app.core.policy import tree_count, tree_size

KST = ZoneInfo("Asia/Seoul")


@pytest.mark.parametrize(
    "minutes,count,size",
    [(20, 1, "small"), (40, 2, "small"), (49, 2, "small"), (50, 2, "large"), (60, 3, "large"), (80, 4, "large"), (180, 9, "large")],
)
def test_reward_boundaries(minutes, count, size):
    assert tree_count(minutes * 60) == count
    assert tree_size(minutes * 60) == size


def test_no_carryover_two_30_minute_sessions():
    # 30분 두 번 = 각각 1그루 → 2그루(이월 없음). 60분 한 번 = 3그루.
    assert tree_count(1800) + tree_count(1800) == 2
    assert tree_count(3600) == 3


def test_split_by_kst_midnight():
    start = datetime(2026, 10, 21, 23, 40, tzinfo=KST)
    end = datetime(2026, 10, 22, 0, 30, tzinfo=KST)
    parts = split_by_kst_date(start, end)
    assert parts == {start.date(): 20 * 60, end.date(): 30 * 60}
