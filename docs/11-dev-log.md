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

## 2단계 — 출석·도서관 시작 IP·공동 광장·공개 WBS 조회

### 구현 체크리스트
- [x] 스터디 날짜 종류: 기본값(10/20~11/19, 화~금 대면·그 외 자율)은 코드 계산, 운영자 지정(휴무 등)만 study_dates에 저장
- [x] 출석 체크인(당일 23:59:59 KST까지 출석), 다음 날 00:00부터 미체크인 대면일 결석, 지각 상태 없음
- [x] 휴무는 출석률 분모 제외, 결석으로 나무 차감 없음, 운영자 정정은 사유 필수 + 감사 기록
- [x] 도서관 네트워크 등록(정확한 IPv4/IPv6 기본, /24·/56보다 넓은 범위 거부), 규칙 버전 기록
- [x] 세션 시작 시점에만 판정(library_at_start + network_rule_version 고정), 재개·종료 IP 재판정 없음
- [x] 신뢰 프록시(TRUSTED_PROXY_IPS) 연결에서만 X-Forwarded-For 사용, 오른쪽부터 첫 비신뢰 주소 채택, 직접 연결의 위조 헤더 무시
- [x] uvicorn `--no-proxy-headers`로 전달 헤더 해석을 앱 한 곳(app.core.client_ip)으로 일원화
- [x] 운영자 전용 접속 IP 진단(캐시 금지), 일반 사용자는 인식 여부만(/api/library-status)
- [x] 공동 숲: 정상 완료 나무만, 서버 무작위 빈 칸(최근 구역부터, 가득 차면 새 구역), advisory lock + unique 제약
- [x] 광장 API: 요약(전체 성공 집중·성공 나무·오늘 출석), 팀원 카드(공부 중/일시정지/휴식/대기·접속 여부), 공개 기록 피드
- [x] 광장 화면: 나무 hover/focus/click → 소유자 카드(표시 이름·아바타·소개·공개 WBS 링크), Escape/닫기
- [x] 공개 WBS 읽기 API: 공개 행만, 비공개 부모 이름 숨김(공개 자식은 독립 행), 비공개 자식 제외
- [x] 캘린더 조회 API + 월간 달력, 팀원 캘린더(/calendar?member=id)는 공개 기록 날짜만 표시, 날짜 → /members/:id/records/:date
- [x] 대시보드: 출석 체크 버튼·출석 요약, 도서관 인식 안내, 멤버 요약
- [x] 운영자 화면: 도서관 IP 등록/삭제·진단, 날짜 종류 지정, 출석 현황·정정
- [x] 좌하단 단계 배지 2단계로 갱신
- [ ] 본인 WBS 생성·편집, 드래그 시간표, 주간 회고, 주말 보충(3단계)

### API (2단계 추가)
| 메서드 | 경로 | 권한 |
|---|---|---|
| GET | /api/plaza | active |
| POST | /api/attendance/check-in | active |
| GET | /api/attendance/me?month= | active |
| GET | /api/members/:id/wbs | active(공개 필터) |
| GET | /api/calendar?month=&member= | active(팀원은 공개 날짜만) |
| GET | /api/library-status | active(인식 여부만) |
| GET | /api/admin/network-diagnostic | operator |
| GET/POST/DELETE | /api/admin/library-networks[/:id] | operator |
| PUT | /api/admin/study-dates/:date | operator |
| GET | /api/admin/attendance?day= | operator |
| PUT | /api/admin/attendance/:userId/:date | operator(사유 필수) |

### 데이터 모델 (마이그레이션 0002)
study_dates, attendance, library_networks, app_settings, community_placements, wbs_tasks.

### 검증 기록 — 2026-10-17
- 백엔드 pytest 64개 통과(2단계 14개 추가): 도서관에서 시작 → 다른 IP에서 완료해도 장식, 반대는 장식 없음,
  직접 연결의 위조 X-Forwarded-For 거부, 신뢰 프록시 오른쪽 주소 사용·왼쪽 위조 무시, 넓은 CIDR·중복 거부,
  진단 API 운영자 전용·no-store, 공동 숲은 성공 나무만·새로고침 안정, 40그루 배치 시 36칸 후 새 구역·겹침 없음,
  4명 동시 완료 워커 경합 시 공동 칸 고유, 출석 체크인·늦은 체크인도 출석·다음 날 결석·지각 없음, 휴무 체크인 거부,
  정정 사유 필수, 10명 광장에 이메일·실명·비공개 계획 미노출, 공개 해제 즉시 피드 제외, 공부/일시정지/휴식 상태,
  비공개 부모 이름 숨김 WBS, 팀원 캘린더 공개 날짜만.
- Alembic 0002 upgrade/downgrade/upgrade + `alembic check` 차이 없음.
- Playwright E2E 17개 통과(1단계 11 + 2단계 6): 2명 가입·승인·표시 이름, 운영자 IP 진단→등록·대면일 지정,
  출석 체크, 도서관 시작 세션→장식 나무, 공개 기록→다른 멤버 광장/읽기 전용 기록, 나무 focus 소유자 카드(이메일 미노출)·Escape,
  팀원 공개 WBS 캘린더, 공개 해제 후 '공개된 기록 없음'·피드 제외, 광장 390/360 가로 넘침 없음.
- E2E 하네스 수정: 세션 시각 이동을 한 트랜잭션으로 묶어 워커가 중간 상태를 보지 않게 함(이전엔 간헐 실패).
- 미실행: 실제 도서관 Wi-Fi·Caddy 경유 IP 확인(4단계 배포 후 현장 절차 필요, docs/05-library-ip.md).

## 3단계 — 캘린더/WBS CRUD·드래그 시간표·주말 보충·주간 회고

### 구현 체크리스트
- [x] WBS 생성·수정·삭제·공개 전환(명확한 폼), 상위/하위 최대 2단계, 하위는 상위 기간 안, 종료>=시작, 진행률 0~100
- [x] 상위 기간을 줄여 하위가 밖으로 나가면 거부, 상위 삭제 시 하위 함께 삭제(FK cascade)
- [x] 캘린더: 날짜 링크 → /records/YYYY-MM-DD, WBS 막대 선택(편집)과 날짜 이동 동작 분리, 작업 추가 폼 접기/펼치기
- [x] 드래그 시간표: 00:00~24:00·15분 스냅, 09:00 근처 초기 스크롤, 왼쪽 계획/오른쪽 실제 열
- [x] 빈 곳 드래그로 범위 선택(역방향 정규화, 6px threshold로 클릭 구별), pointer capture, pointercancel 시 복구
- [x] 기존 블록 이동(본문 드래그)·끝 조절(아래 손잡이), 클릭/Enter로 폼 수정·삭제
- [x] 키보드·터치 대안: '블록 추가' 폼(시작/종료 시각 선택)
- [x] 서버 검증: 15분 스냅·최소 15분·24:00은 종료만·같은 레이어 겹침 거부(사용자별 advisory lock), 레이어 간 겹침 허용
- [x] 공개 일일 기록에 시간표 포함, 비공개면 타인에게 노출 없음, 시간표는 나무 지급과 무관
- [x] 주말 보충: 미완료 목표를 토/일로 이월, 원본 유지·링크(carried_from_id), 같은 대상일 중복 거부
- [x] 주간 회고: 잘한 점/어려웠던 점/다음 주 계획, 기본 비공개·공개 토글, 공개 시 광장 피드와 팀원 기록 화면에 표시
- [x] 주간 합계: 성공 세션 집중 구간만, 한국 날짜 기준 자정 분할(요일별 막대)
- [x] 기록 화면: 시간표·보충 변경 시 해당 부분만 다시 읽어 작성 중 초안 보존
- [x] 좌하단 단계 배지 3단계로 갱신

### API (3단계 추가)
| 메서드 | 경로 | 권한 |
|---|---|---|
| GET/POST | /api/wbs | active(본인) |
| PATCH/DELETE | /api/wbs/:id | active(본인) |
| GET | /api/timetable-blocks?date= | active(본인) |
| POST, PATCH, DELETE | /api/timetable-blocks[/:id] | active(본인) |
| GET | /api/goals?from=&to=&done= | active(본인) |
| POST | /api/goals/:id/carry | active(본인, 토/일만) |
| GET/PUT | /api/weekly-reviews/:date | active(본인, 날짜가 속한 월요일 시작 주) |
| GET | /api/members/:id/weekly-reviews/:date | active(공개만) |

### 데이터 모델 (마이그레이션 0003)
timetable_blocks(15분 스냅·범위 CHECK), weekly_reviews.

### 검증 기록 — 2026-10-17
- 백엔드 pytest 71개 통과(3단계 7개 추가): WBS 3단계 금지·부모 기간 밖 거부·역순 거부·진행률 범위·부모 축소 거부·
  계단식 삭제, 공개 전환 즉시 반영·타인 수정 불가, 시간표 미스냅/0분/역방향/자정 넘김 거부·24:00 종료 허용·같은 레이어
  겹침 거부·다른 레이어 허용·맞닿음 허용·이동/끝 조절 겹침 거부, 두 탭 동시 겹침 생성 시 하나만 성공, 비공개 기록의
  시간표 비노출, 주말 보충 요일·중복·완료 목표 거부, 일요일 23:40 시작 40분 세션의 주간 합계 자정 분할(20분/20분),
  공개 회고만 팀원·광장 노출.
- Alembic 0003 upgrade/downgrade/upgrade + `alembic check` 차이 없음.
- Playwright 3단계 8개 통과: 캘린더 날짜 → 정확한 기록, WBS 상위/하위 생성·기간 밖 거부 메시지·상태 편집,
  역방향 드래그 생성(10:00~11:15)·겹침 거부·계획 레이어 겹침 허용·블록 1시간 이동·폼 대안·새로고침 유지·Enter 수정,
  주간 회고 공개 저장·주말 보충 이월(보충 배지), 1440/390/360 가로 넘침 없음.
- 수정한 결함: 빠른 드래그 놓기에서 React 상태가 갱신되기 전 값을 읽어 이동이 무시되던 문제(미리보기를 ref에도 보관).

## 4단계 — EC2/HTTPS 준비·백업·통합 검수

### 구현 체크리스트
- [x] Caddyfile: SITE_ADDRESS로 자동 HTTPS(Let's Encrypt), http→https 리디렉트, 보안 헤더(HSTS·CSP·X-Frame-Options·nosniff·Permissions-Policy), 관리 API off, 해시 자원 장기 캐시·index.html no-cache, 접근 로그에서 쿠키·인증 헤더 제거
- [x] 운영 compose: 고정 내부 대역(172.30.0.0/24), Caddy 고정 IP를 TRUSTED_PROXY_IPS로 주입, db/backend 호스트 포트 없음, ENVIRONMENT=production·COOKIE_SECURE=true 강제
- [x] backend 운영 가드: 짧은 JWT_SECRET·Secure 쿠키 꺼짐·http APP_ORIGIN·신뢰 프록시 없음이면 시작 거부, 운영에서 API 문서 비공개, /api/ready 실패 시 503(오류 원문 미노출)
- [x] 백업: infra/backup/backup.sh(pg_dump -Fc, 형식 검사, sha256, 14일 보관, 선택적 S3 업로드·SSE)
- [x] 복원: infra/backup/restore.sh --verify(임시 DB 복원 후 행 수 확인) / --replace(RESTORE 입력 확인, 교체 전 자동 백업, backend 정지 후 복원)
- [x] 운영 빌드 스모크 테스트(e2e/prod.config.js + e2e/prod/smoke.spec.js, 읽기 위주)
- [x] 배포 절차 문서(docs/12-deploy-ec2.md), README 갱신, .env.example에 ENVIRONMENT·SITE_ADDRESS·BACKUP_S3_URI 추가
- [x] 좌하단 단계 배지 4단계로 갱신
- [ ] 실제 EC2 배포·DNS·인증서 발급(서버 접근 권한이 없어 운영자가 docs/12 절차로 수행)
- [ ] 도서관 현장 IP 확인·등록(현장 절차, docs/05)
- [ ] S3 백업 업로드 실제 확인(IAM Role 필요)

### 검증 기록 — 2026-10-17 (로컬에서 운영 스택을 별도 포트로 띄워 확인)
- 운영 스택(compose.production.yaml, SITE_ADDRESS=localhost → Caddy 내부 CA HTTPS): /api/ready 200, SPA 경로 폴백 200,
  http → https 308, 보안 헤더 적용, /api/docs 404, backend·db 호스트 포트 없음.
- Caddy 경유 로그인: refresh 쿠키 Secure·HttpOnly·Path=/api/auth 확인, 다른 Origin refresh 403, 정상 refresh 200.
- 위조 X-Forwarded-For(203.0.113.77) 전송 → 진단 API가 실제 접속 주소(도커 게이트웨이)를 관측, 위조 값 무시.
- 재시작 복구: 60분 세션 진행 중 backend 재시작 → 목표 시각 경과 후 워커가 완료 확정(나무 3, 공동 숲 배치 3).
- 백업 → restore --verify: 행 수 일치(users 1, focus_sessions 1, trees 3, community_placements 3, daily_entries 1, alembic 0003).
- restore --replace: 변경한 데이터가 덤프 시점으로 되돌아가고 /api/ready 정상.
- 운영 빌드 브라우저 스모크 1개 통과: 로그인·대시보드·광장·캘린더·기록·이모지 지연 청크·Pretendard 로드·새로고침 로그인 유지, 콘솔/CSP 오류 없음.
- 무음·저장소 점검: 프론트/백엔드 소스에 Audio·vibrate·Notification·PushManager·serviceWorker 사용 없음, 토큰을 localStorage/sessionStorage에 저장하지 않음.
- 최종 회귀: 백엔드 pytest 72개 통과, Playwright E2E 25개 통과(1·2·3단계 전체).
- 점검용 로컬 운영 스택과 테스트 덤프는 확인 후 삭제했다.
