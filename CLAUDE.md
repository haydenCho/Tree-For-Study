# Tree for Study — working guide for Claude Code

A study-group web app for a small SAA exam cohort (4–10 people). Pomodoro-style focus
sessions grow trees in a personal forest and a shared "plaza" forest. This repo began as
a planning/design package; the running app is being built alongside it.

## Source of truth
The specs in `docs/` are authoritative. Higher version numbers win.
- `docs/01-product-plan.md` — product plan **v5** (overrides earlier versions).
- `docs/10-focus-and-jwt.md` — **takes precedence** for auth + the focus-only screen.
- `docs/03-development-plan.md` — staged plan (0→4) and required tests.
- `docs/05-library-ip.md` — library-bonus IP / proxy details.
Do NOT reorganize `docs/` — files cross-reference each other by filename.

## Layout
- `frontend/` — React + JavaScript + Vite (SPA). Source for UI lives in `ui/` and is
  copied/adapted into `frontend/src/`.
- `backend/` — FastAPI + Uvicorn + Pydantic + SQLAlchemy 2.0 (async) + Alembic.
- `infra/caddy/` — production reverse proxy. `compose.yaml` (dev) / `compose.production.yaml`.
- `ui/`, `design/`, `prompts/`, `tests/` — planning package. Keep as reference; `ui/` is
  the origin of React components, tree SVGs, tokens.css, fonts, and emoji data.

## 개발 규칙 (Development rules)
- **주석은 한글로.** 모든 코드/설정 파일의 주석과 docstring은 한국어로 작성한다.
  식별자(변수·함수·클래스명)와 로그 메시지는 영어를 유지해도 된다.

## Stack decisions (fixed)
React + Vite / FastAPI / PostgreSQL / Docker Compose + EC2 (Caddy). 10-user scale → polling
is enough; no Redis / WebSocket / 3D engine. Dev: Vite proxies `/api` → backend, so the
browser always uses same-origin `VITE_API_BASE_URL=/api`.

## Non-negotiable policies
- **Reward math**: `count = floor(target_seconds / 1200)`; `size = large if target_seconds >= 3000 else small`.
  No mid-session payout, no carryover ledger. Trees are confirmed atomically only on full success.
- **Auth (v5)**: access JWT (15 min, in-memory Bearer) + opaque refresh token (7 days,
  HttpOnly/Secure/SameSite cookie, only a hash stored in DB). Rotate refresh on every use,
  block reuse, revoke on logout. Verify alg/exp/nbf/iss/aud/token_use explicitly. Argon2id
  for passwords. Secrets (`JWT_SECRET`, `DATABASE_URL`, `POSTGRES_PASSWORD`) live in server
  `.env` only — never in `VITE_*`, never in browser storage, never in logs.
- **Membership**: invite + email + real name + password → `pending`; operator approves to
  `active` (transactional seat check, max 10). Plaza shows display name + emoji only.
- **Library bonus**: decided from the server-verified client IP at session start only,
  read from the trusted Caddy connection — never trust raw `X-Forwarded-For`.
- **Silent UX**: visual effects only. No audio/vibration/OS push. Respect reduced-motion.

## Git discipline (from docs/03)
Claude Code **commits only**. Do NOT push, create remotes/PRs — the user pushes.
Stage changed files explicitly; never commit secrets, textbook content, backups, logs,
or node_modules. After finishing a stage, report commit hash + tests run + unfinished
scope, then stop. Do not silently drop planned features — leave them on the checklist.

## Commit trailer
End commit messages with:
Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

## Stage status
- [x] Stage 0 — scaffolding: compose, React, FastAPI, Postgres, health/ready, JWT config
      + auth route skeleton. Docker-verified 2026-10-17 (dev + production/Caddy stacks).
- [x] Stage 1 — invite/auth/profile, dashboard session, fixed placement, basic daily entry.
      Verified 2026-10-17 (pytest 51 + Playwright 11). Details: docs/11-dev-log.md.
- [x] Stage 2 — attendance, library IP, plaza, public WBS read.
      Verified 2026-10-17 (pytest 64 + Playwright 17). Details: docs/11-dev-log.md.
- [x] Stage 3 — calendar/WBS CRUD, drag timetable, make-up, weekly review.
      Verified 2026-10-17 (pytest 71 + Playwright 25). Details: docs/11-dev-log.md.
- [x] Stage 4 — EC2/HTTPS, backup, integration review. Locally verified 2026-10-17 (prod stack via
      Caddy, backup/restore drill, pytest 72 + Playwright 25 + prod smoke). Actual EC2 deploy: docs/12-deploy-ec2.md.
