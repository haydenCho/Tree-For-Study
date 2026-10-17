"""DB 기반 세션 완료 워커.

브라우저 interval이 아니라 서버가 목표 시각이 지난 세션을 확정한다. 서버가 재시작돼도
DB의 target_end_at을 기준으로 다시 찾아 완료하므로 복구된다. 조회 요청도 같은 settle을
호출하므로 워커가 늦어도 사용자에게는 정확한 상태가 보인다.
"""
import asyncio
import logging

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.services.focus import settle_due

log = logging.getLogger("tfs.worker")


async def run_forever() -> None:
    interval = get_settings().worker_interval_seconds
    while True:
        try:
            async with SessionLocal() as db:
                done = await settle_due(db)
            if done:
                log.info("completed %d due focus sessions", done)
        except asyncio.CancelledError:
            raise
        except Exception:  # 워커는 죽지 않고 다음 주기에 재시도한다.
            log.exception("focus completer iteration failed")
        await asyncio.sleep(interval)
