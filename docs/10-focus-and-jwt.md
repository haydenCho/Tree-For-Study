# v5 집중 전용 화면과 JWT 인증

이 문서는 기존 인증 및 집중 화면 정책보다 우선한다. 다른 나무 지급·배치·출석 정책은 유지한다.

## 집중 화면
시작 전 대시보드에서 시간·수종·위치를 설정한다. 서버의 세션 생성과 칸 예약이 성공하면 `/focus/:sessionId`로 이동한다. 이 화면에서는 사이드바·일반 메뉴·footer를 숨긴다. 남은 시간, 성장하는 나무, 진행률, 일시정지/재개, 중도 포기만 제공한다. 완료 전까지 다른 서비스 페이지로 이동하지 못한다.
성장 단계는 씨앗→새싹→어린 나무→완성. 서버가 확인한 집중 경과/목표 비율로 렌더링하며 일시정지 시간은 제외. 중간 성장 표현은 보상 확정이 아니다. 6수종과 작은/큰 결과, 도서관 장식을 반영한다. 포기하면 회색 시듦, 성공하면 지정된 모든 칸의 나무 확정. 소리·진동 없음, reduced-motion에서는 흔들림/입자/연속 전환 제거, 단계별 정적 변화만 유지.

## 이탈의 정확한 범위
- 서비스 내부 다른 route, 뒤로/앞으로, 로고, 계정/로그아웃: Router blocker로 이동을 보류하고 포기 확인. 취소하면 현재 공부 유지. 확인하면 서버 abandon 성공 후 인정 시간0/시듦을 반영하고 이동한다. 서버 실패 시 이동하지 않고 재시도 안내.
- 일시정지 중에도 동일한 이탈 규칙. 새 탭에서 서비스에 접근하거나 주소로 다른 내부 route를 직접 열면 활성 세션을 조회해 해당 집중 화면으로 유도한다.
- 외부 교재 탭·다른 앱·화면 잠금은 이번 내부 route 이탈에 포함하지 않는다. 페이지 차단 기능을 재도입하지 않는다. visibilitychange만으로 포기 처리하지 않는다.
- 새로고침은 활성 집중 화면 복원 대상으로 둔다. beforeunload는 브라우저 경고를 보조하지만 사용자 정의 문구/실행/이동 방지를 보장하지 않는다.
- 브라우저 닫기·강제 종료·OS 중단은 포기 신호 전달을 100% 보장하지 못한다. 감지 가능한 종료 신호를 전송하더라도 전달/처리 여부는 서버 확인이 필요하다. 초기 버전은 서버에 명시적으로 접수된 abandon만 포기, 접수되지 않으면 기존 서버 타이머 상태를 유지하고 재접속 복원한다. 이것을 '닫으면 항상 즉시 포기'라고 안내하지 않는다.
- 단순 heartbeat 중단으로 자동 포기하지 않는다. 절전·인터넷 끊김과 실제 이탈을 구별할 수 없기 때문이다. 모든 브라우저 이탈까지 강제 포기해야 한다면 별도 정책 승인이 필요하다.
- 성공과 포기 경합은 서버 목표 도달 시각으로 결정. 완료가 이미 확정되면 포기 API는 완료 상태를 반환하고 성공 나무를 회수하지 않는다.

React Router의 지원되는 navigation blocker를 사용하고 강제 history trap을 만들지 않는다. 상태는 URL만으로 판단하지 않고 서버 세션을 조회한다. 클라이언트 인터벌/애니메이션 완료 이벤트를 보상 근거로 쓰지 않는다.

## 회원가입과 멤버 식별
초대 코드 + 이메일(로그인 ID) + 실명 + 비밀번호/확인. 이메일은 고유 정규화 규칙을 문서화하고 DB unique로 검사. 표시 이름/이모지는 가입 후 마이페이지에서 수정. 실명과 이메일은 운영자/본인만, 공동 숲은 표시 이름과 이모지만 공개한다.
초대 코드만으로 실제 신원 확인이 끝난 것으로 보지 않는다. 소규모 대면 스터디이므로 가입은 pending, 운영자가 실제 멤버와 대조해 active 승인하는 방식을 기본으로 한다. pending은 인증되어도 스터디 데이터 접근 불가. 거부/탈퇴/차단 상태도 API에서 검사한다. 이메일 소유 확인 메일은 첫 버전 범위 밖이므로 이메일 인증 완료라고 표시하지 않는다.
활성 멤버 최대10명, 승인 시 트랜잭션 안에서 정원 확인. pending 가입 남용을 방지하기 위해 초대 사용 횟수와 속도 제한. 비밀번호는 12~128자와 Argon2id 해시, 평문 저장/로그 출력 금지. 운영자 생성 CLI와 계정 복구는 별도 안전한 절차.

## JWT와 토큰 저장
FastAPI + PyJWT(또는 유지보수되는 동등 라이브러리) + pwdlib Argon2. 설치 시 호환 버전 고정.
- Access: 서명된 JWT, 기본15분, `Authorization: Bearer`로 전송. 브라우저 메모리에만 저장. localStorage/sessionStorage/URL 금지.
- Claims: sub(불변 사용자 ID), sid(토큰 세션 ID), jti, iat, nbf, exp, iss, aud, token_use=access. 실명·이메일·비밀번호·공부 기록 넣지 않는다. JWT는 암호화된 저장소가 아니다.
- 서버는 알고리즘을 명시적으로 고정하고 서명·exp/nbf·issuer/audience·용도를 검증한다. 헤더의 alg를 그대로 받아들이지 않고 none/서명 오류/갱신 토큰의 access 사용 거부.
- 초기 단일 API는 HS256, 강한 256bit 이상 난수 JWT_SECRET을 서버 .env에만 보관. JWT_ISSUER, JWT_AUDIENCE, ACCESS_TTL_SECONDS=900, REFRESH_TTL_SECONDS=604800 설정. 키를 프론트 VITE_*로 내보내지 않음.
- Refresh: 암호학적으로 무작위인 opaque 토큰(반드시 JWT일 필요 없음), 기본7일. HttpOnly+Secure+SameSite=Lax 쿠키, 명시적 Path=/api/auth. DB에는 해시만 저장. HttpOnly라 JS로 읽지 않지만 자동 전송되므로 refresh/logout은 CSRF 토큰과 Origin 검사.
- 갱신마다 refresh를 회전하고 이전 것을 소모 처리. 재사용 감지 시 해당 token family 폐기. 동시에 여러 API가401을 받아도 프론트는 single-flight refresh, 한 번만 재시도. 403은 갱신하지 않음. 오래된 네트워크 요청 무한 재시도 금지.
- 매 API에서 sid의 폐기 상태와 회원 승인/소속을 DB로 확인한다(10명 규모). 로그아웃/비밀번호 변경/차단 시 해당 token session 또는 전체 family 폐기하여 access JWT도 즉시 거부할 수 있게 한다.
- 새로고침 시 refresh cookie로 access 재발급 후 /me 및 활성 공부 세션을 조회. 인증 갱신 자체가 공부 포기를 유발하지 않게 한다. 갱신 실패는 재로그인 안내, 공부 상태는 서버 판단; 다른 계정의 세션을 복원하지 않는다.

## API 및 데이터
POST /api/auth/register, /login, /refresh, /logout, /password; GET /api/me; GET /api/admin/membership-requests; POST /api/admin/membership-requests/:id/approve,reject.
users: email_normalized, real_name, display_name, avatar_emoji, password_hash, status. auth_token_sessions: sid,user_id,family_id,refresh_hash,expires_at,rotated_at,revoked_at. jwt jti/sid는 노출 로그에 넣지 않는다. 기존 서버 세션 쿠키 인증은 JWT 방식으로 교체하며 기존 사용자가 있다면 비밀번호 해시·프로필은 보존하고 기존 로그인만 만료시킨다.

## 테스트와 단계
단계0에 JWT 설정·문서·auth 라우트 뼈대, 단계1에 실제 가입/로그인/JWT 갱신·승인 게이트·집중 전용 라우트/애니메이션/이탈 처리 포함. 승인 UI 최소 기능도 단계1 완료 기준이다.
검증: 가입→pending→운영자 승인→접근, 잘못된 비밀번호/토큰/서명/alg/iss/aud/용도/만료, rotation 재사용·동시 refresh, logout 후 기존 JWT 거부, 타인 세션/비공개 데이터 차단, 11번째 승인 거부, CSRF, 재로그인/집중 복원.
집중 검증: 시작 성공 후에만 이동, 내부 이동 취소 유지/확인 포기, 서버 실패 시 이동 보류, pause에서도 blocker, 성장 pause/resume, reduced-motion, 완료/포기 경합. 실제 서버 테스트는 주입 시계 사용. HTML 시안의 60배속·즉시 완료 버튼은 개발/운영 코드에 복사하지 않는다.

공식 근거: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ · https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeunload_event · https://developer.mozilla.org/en-US/docs/Web/API/Navigator/sendBeacon
