"""운영자 CLI(서버 셸에서만 실행).

    docker compose exec backend python -m app.cli create-operator --email a@b.c --real-name 홍길동
    docker compose exec backend python -m app.cli create-invite --max-uses 10 --ttl-days 7

비밀번호는 getpass로 입력받아 화면/로그에 남기지 않는다. 초대 코드 원문은 생성 시
한 번만 출력되고 DB에는 해시만 저장된다.
"""
import argparse
import asyncio
import getpass
import sys

from sqlalchemy import select

from app.core.clock import utcnow
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import User
from app.services.auth import normalize_email, validate_email, validate_password
from app.services.membership import create_invite


async def _create_operator(email: str, real_name: str, display_name: str) -> None:
    email_n = normalize_email(email)
    validate_email(email_n)
    if sys.stdin.isatty():
        password = getpass.getpass("운영자 비밀번호(12~128자): ")
        confirm = getpass.getpass("비밀번호 확인: ")
    else:
        # 자동화용: 표준 입력 첫 줄을 비밀번호로 읽는다(명령줄 인자로 받지 않는다).
        password = confirm = sys.stdin.readline().rstrip("\n")
    if password != confirm:
        sys.exit("비밀번호 확인이 일치하지 않습니다.")
    validate_password(password)
    async with SessionLocal() as db:
        existing = (await db.execute(select(User).where(User.email_normalized == email_n))).scalar_one_or_none()
        if existing is not None:
            sys.exit("이미 존재하는 이메일입니다.")
        now = utcnow()
        db.add(
            User(
                email_normalized=email_n,
                real_name=real_name,
                display_name=display_name or "운영자",
                password_hash=hash_password(password),
                status="active",
                role="operator",
                created_at=now,
                approved_at=now,
            )
        )
        await db.commit()
    print("운영자 계정을 만들었습니다.")


async def _create_invite(max_uses: int, ttl_days: int, label: str) -> None:
    async with SessionLocal() as db:
        invite, code = await create_invite(db, None, max_uses=max_uses, ttl_days=ttl_days, label=label)
    print(f"초대 코드(한 번만 표시): {code}")
    print(f"만료: {invite.expires_at.isoformat()} · 최대 사용 {invite.max_uses}회")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    op = sub.add_parser("create-operator", help="운영자 계정 생성")
    op.add_argument("--email", required=True)
    op.add_argument("--real-name", required=True)
    op.add_argument("--display-name", default="운영자")
    inv = sub.add_parser("create-invite", help="초대 코드 발급")
    inv.add_argument("--max-uses", type=int, default=10)
    inv.add_argument("--ttl-days", type=int, default=7)
    inv.add_argument("--label", default="")
    args = parser.parse_args()
    if args.cmd == "create-operator":
        asyncio.run(_create_operator(args.email, args.real_name, args.display_name))
    elif args.cmd == "create-invite":
        asyncio.run(_create_invite(args.max_uses, args.ttl_days, args.label))


if __name__ == "__main__":
    main()
