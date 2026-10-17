# Tree for Study

SAA 시험을 함께 준비하는 소규모 스터디(최대 10명)를 위한 공부 숲 웹앱입니다. 집중 세션을 끝까지
마치면 개인 숲과 스터디 공동 숲에 나무가 자라고, 날짜별 계획·기록·시간표·WBS·주간 회고를 함께
관리합니다. 소리·진동·OS 알림 없이 화면의 시각 효과만 사용합니다.

- 프론트엔드: React + JavaScript + Vite (`frontend/`)
- 백엔드: FastAPI + SQLAlchemy 2.0(async) + Alembic (`backend/`)
- DB: PostgreSQL 16 · 운영: Docker Compose + Caddy(HTTPS) on EC2

## 문서
| 문서 | 내용 |
|---|---|
| `docs/01-product-plan.md` | 기획서 v5(정책의 기준) |
| `docs/10-focus-and-jwt.md` | 집중 화면·JWT 인증(인증 관련 최우선) |
| `docs/03-development-plan.md` | 단계별 계획과 필수 테스트 |
| `docs/05-library-ip.md` | 도서관 IP·프록시 설명과 현장 절차 |
| `docs/11-dev-log.md` | 단계별 구현 체크리스트·API·검증 기록 |
| `docs/12-deploy-ec2.md` | EC2 배포·백업/복원·운영 절차 |
| `design/`, `ui/` | 디자인 시안과 원본 컴포넌트·에셋(참고용) |

## 로컬 개발
```bash
cp .env.example .env            # 비밀값(POSTGRES_PASSWORD, DATABASE_URL, JWT_SECRET)을 채운다
docker compose up -d --build    # db + backend(시작 시 마이그레이션) + frontend(Vite)
open http://localhost:5173      # 포트는 .env의 *_HOST_PORT로 바꿀 수 있다
docker compose exec backend python -m app.cli create-operator --email you@example.com --real-name 홍길동
docker compose exec backend python -m app.cli create-invite --max-uses 10
docker compose down             # 중지(볼륨 보존). 데이터까지 지우려면 -v (주의)
```
- 마이그레이션 수동 실행: `docker compose exec backend alembic upgrade head`
- 새 마이그레이션: `docker compose exec backend alembic revision --autogenerate -m "..."`

## 테스트
```bash
docker compose run --rm --no-deps -T backend pytest -q   # 백엔드(개발 DB 서버의 *_test DB 사용, 주입 시계)
./e2e/run.sh                                             # 브라우저 E2E(Playwright, 분리된 tfs-e2e 스택)
docker run --rm -v "$PWD/frontend":/app -v tfs_fe_node_modules:/app/node_modules -w /app node:20-alpine \
  sh -c "npm install && npm run build"                   # 프론트 빌드
```

## 운영
`docs/12-deploy-ec2.md`를 따른다. 요약: `.env` 작성(SITE_ADDRESS, https APP_ORIGIN) →
`docker compose -f compose.production.yaml up -d --build` → 운영자/초대 생성 → 도서관 IP 등록 →
`infra/backup/backup.sh` cron + 주간 `restore.sh --verify`.

## 보안 원칙
- 비밀값은 서버 `.env`에만. `VITE_*`는 공개 번들이므로 비밀 금지. 액세스 토큰은 브라우저 메모리에만.
- refresh 토큰은 HttpOnly·Secure·SameSite 쿠키, DB에는 해시만. 회전·재사용 차단·로그아웃 폐기.
- 도서관 판정은 Caddy가 전달한 주소를 신뢰 프록시 연결에서만 읽는다. DB/백엔드 포트는 외부 비공개.

폰트: Pretendard(SIL OFL, `frontend/src/assets/fonts/LICENSE.txt`). 이모지 데이터: Unicode Emoji 18.0 / CLDR
(`frontend/src/data/EMOJI-LICENSE.txt`).
