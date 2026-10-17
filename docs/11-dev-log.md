# 개발 진행 기록 (단계별 체크리스트·API·검증)

docs/03-development-plan.md의 단계 계획을 실제 구현과 대조해 기록한다. "통과"는 실제로
실행한 검사만 적는다. 실행하지 않은 항목은 "미실행"으로 남긴다.

## 실행 방법
- 개발 스택: `docker compose up -d` (backend는 시작 시 `alembic upgrade head` 적용)
- 백엔드 테스트: `docker compose run --rm --no-deps -T backend pytest -q`
  (개발 DB 서버 안에 `<DB>_test` 데이터베이스를 따로 만들어 사용, 주입 시계로 시간 이동)
- 브라우저 E2E: `./e2e/run.sh` (별도 프로젝트 `tfs-e2e`로 스택을 띄우고 Playwright 실행 후 정리.
  시간 경과는 E2E 전용 DB의 세션 시각을 과거로 옮겨 흉내 낸다. 운영 API에는 시간 조작 기능 없음)
- 프론트 빌드: `docker run --rm -v "$PWD/frontend":/app -v tfs_fe_node_modules:/app/node_modules -w /app node:20-alpine sh -c "npm install && npm run build"`
- 운영자 생성: `docker compose exec backend python -m app.cli create-operator --email ... --real-name ...`
- 초대 발급: `docker compose exec backend python -m app.cli create-invite --max-uses 10 --ttl-days 7`

## 1단계 — 초대·인증·프로필·대시보드 세션·고정 배치·기본 일일 기록

### 구현 체크리스트
- [x] 초대 코드 발급/폐기/만료(기본 7일)·사용 횟수 제한, 코드 원문은 생성 시 한 번만 표시(DB 해시)
- [x] 가입(초대+이메일+실명+비밀번호 12~128자, Argon2id) → pending, 운영자 승인 → active
- [x] 승인 시 활성 정원 10명 트랜잭션 검사(advisory lock), 거부/중지 시 토큰 전부 폐기
- [x] access JWT(15분, 메모리 Bearer) + opaque refresh(7일, HttpOnly·SameSite=Lax·Path=/api/auth, DB 해시)
- [x] refresh 회전, 재사용 감지 시 패밀리 폐기, 동시 refresh는 10초 유예 409 → 프론트 1회 재시도
- [x] alg 고정, 서명·exp·nbf·iss·aud·token_use 명시 검증(exp/nbf는 주입 시계 기준), 매 요청 sid 폐기·회원 상태 DB 확인
- [x] refresh/logout CSRF 이중 제출(X-CSRF-Token == tfs_csrf 쿠키) + Origin(없으면 Referer) 검사, 로그인/가입 Origin 검사
- [x] 로그인 실패 기반 속도 제한(계정 10회/5분, IP 30회/5분), 가입 IP 20회/10분
- [x] 비밀번호 변경(현재 비밀번호 확인, 모든 세션 폐기 후 새 세션), 로그아웃
- [x] 운영자 CLI(create-operator, create-invite) — 비밀번호는 getpass/표준 입력, 인자로 받지 않음
- [x] 프로필: 표시 이름 2~20자, 소개 160자, 이모지 서버 허용 목록(Unicode Emoji 18.0, 3,972개), 기본 공부/휴식
- [x] 세션 시작: 수종·목표(20~180분)·서로 다른 빈 칸 N개 검증, 세션+칸 예약 원자적 생성, 요청 ID 멱등
- [x] 두 탭 경합: 사용자 행 잠금 + 활성 세션 부분 unique 인덱스 + 칸 unique
- [x] 6×6 구역, 기존 구역에 필요한 빈 칸이 없을 때만 새 구역 생성
- [x] pause(구간 종료)/resume(새 구간, 수종·크기·도서관 판정·위치 유지)
- [x] 완료: DB 기반 워커(5초) + 조회 시 settle, 완료 시각 = 목표 도달 시각, 나무 일괄 확정
- [x] 포기: 인정 0초, 예약 칸 전부 시든 나무, 이전 기록 유지, 목표 도달 후 포기 요청은 완료 우선
- [x] 정상 완료 후 수동 휴식 시작/종료(보상 무관)
- [x] 집중 전용 화면 /focus/:id: 메뉴 숨김, 서버 시각 기반 성장(씨앗→새싹→어린 나무→완성), pause 시 성장 정지
- [x] 이탈 guard: React Router useBlocker → 포기 확인 → 서버 abandon 성공 후 이동, 실패 시 머묾
- [x] 새로고침/직접 주소 진입 시 활성 세션 화면으로 유도, beforeunload 보조 경고, 탭 제목 진행 표시
- [x] reduced-motion: 흔들림·입자·전환 제거(시안 CSS 규칙 유지)
- [x] 대시보드: 타이머·수종 6종·크기/개수 미리보기·숲 타일 직접 선택(클릭/Tab·Enter)·오늘 성공 집계
- [x] 일일 기록 /records/:date: 계획·체크 목표·실제 기록·공개 토글(기본 비공개), 서버 공개 필터
- [x] 팀원 공개 기록 API(/api/members/:id/daily-entries/:date): 비공개·없음 동일 응답
- [x] 좌하단 단계 배지 1단계로 갱신
- [ ] 도서관 IP 판정(2단계에서 연결. 1단계에서는 항상 false, 예시 IP로 인정하지 않음)
- [ ] 출석·공동 숲·팀원 카드(2단계), 시간표·주간 회고·주말 보충(3단계)

### 정책 해석(문서에 명시되지 않아 정한 값)
- 운영자 계정도 활성 멤버 정원(10명)에 포함한다.
- 이메일 정규화: 앞뒤 공백 제거 + 전체 소문자.
- 기본 표시 이름은 `새싹NNNN`(실명·이메일 노출 방지). 가입 후 마이페이지에서 바꾼다.
- 스터디 종료일(11/19) 다음 날부터 새 집중 세션 시작을 막는다. 시작일 이전 시작은 허용(준비 기간).

### API (1단계)
| 메서드 | 경로 | 권한 |
|---|---|---|
| POST | /api/auth/register, /login | 공개(Origin 검사) |
| POST | /api/auth/refresh, /logout | refresh 쿠키 + CSRF + Origin |
| POST | /api/auth/password | 로그인 |
| GET | /api/me | 로그인(pending 허용) |
| GET/PATCH | /api/me/profile | active |
| POST | /api/presence | active(30초 heartbeat) |
| GET | /api/study | 공개(D-day) |
| GET | /api/dashboard | active |
| POST | /api/sessions | active |
| GET | /api/sessions/active, /api/sessions/:id | active(본인) |
| POST | /api/sessions/:id/pause, resume, abandon, rest | active(본인) |
| GET/PUT | /api/daily-entries/:date | active(본인) |
| GET | /api/members/:id/daily-entries/:date | active(공개 필터) |
| POST, PATCH, DELETE | /api/goals, /api/goals/:id | active(본인) |
| GET/POST | /api/admin/membership-requests, …/:id/approve, …/:id/reject | operator |
| GET/POST | /api/admin/members, …/:id/disable | operator |
| GET/POST | /api/admin/invites, …/:id/revoke | operator |

### 데이터 모델 (마이그레이션 0001)
users, invites, auth_token_sessions, audit_events, personal_zones, focus_sessions, focus_intervals,
session_plots, trees, daily_entries, goals.

### 검증 기록 — 2026-10-17
- 백엔드 pytest 51개 통과: 보상 경계(20/40/49/50/60/80/180분), 30분×2=2그루, 59분 포기 0초·이전 기록 유지,
  pause 시간 제외·resume 설정 유지, 목표 도달 후 포기=완료, 완료/포기/워커 동시 경합 시 나무 중복 없음,
  두 탭 시작 경합 하나만 성공, 요청 ID 멱등, 칸 점유·이동 API 없음, 새 구역 조건, 워커 재시작 복구,
  가입→pending→승인, 초대 만료/무효, 중복 이메일, 잘못된 비밀번호/서명/alg none/iss/aud/token_use/만료,
  refresh 회전·재사용 패밀리 폐기·동시 refresh, CSRF/Origin, 로그아웃 후 기존 JWT 거부, 비밀번호 변경 후
  다른 세션 거부, 11번째 승인 거부(동시 승인), 중지 회원 즉시 차단, 로그인 속도 제한, 공개/비공개 필터,
  목표 소유권, 프로필 이모지 허용 목록(ZWJ·피부색 조합 허용, 임의 문자열 거부), KST 자정 분할,
  신뢰 프록시 IP 판정(위조 헤더 무시).
- Alembic: upgrade → downgrade base → upgrade → `alembic check` 차이 없음.
- 프론트 `npm run build` 성공.
- Playwright E2E 11개 통과(Chromium): 가입 대기 게이트, 운영자 승인, 40분 세션 시작·pause/resume·뒤로 가기
  포기 확인 취소·새로고침 복원·직접 주소 진입 유도·정상 완료·휴식, 이탈 확인 후 서버 포기→시든 나무,
  중도 포기 결과, 일일 기록·목표·공개 저장 유지, 이모지 프로필 저장, 1440/1280/390/360 가로 넘침 없음 +
  키보드(Tab·Enter) 칸 선택, 오디오/진동/알림 API 미사용.
- 미실행: Firefox/Safari 실기기, 실제 Windows 이모지 글꼴 표시, 15분 이상 실제 대기(주입 시계로 대체).
