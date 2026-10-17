"""아바타 이모지 서버 허용 목록.

프론트엔드 EmojiPicker와 같은 Unicode Emoji 18.0 목록을 사용한다. 전체 문자열(국기·
피부색·ZWJ 조합 포함)을 하나의 항목으로 비교하며 첫 코드 포인트만 잘라 보지 않는다.
"""
from functools import lru_cache
from pathlib import Path

_PATH = Path(__file__).resolve().parent.parent / "data" / "emoji_allowlist.txt"


@lru_cache
def emoji_allowlist() -> frozenset[str]:
    lines = _PATH.read_text(encoding="utf-8").splitlines()
    return frozenset(line for line in lines if line and not line.startswith("#"))


def is_allowed_emoji(value: str) -> bool:
    return value in emoji_allowlist()
