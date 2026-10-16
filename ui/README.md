# UI 소스 v2

ui/ 폴더를 Vite src/ui/에 복사하고 tokens.css를 import하세요. fonts/도 함께 복사해야 Pretendard가 표시됩니다. tree-catalog.js의 asset 경로는 Vite new URL 방식입니다.

ForestGrid는 시작 전 빈 칸 선택 전용 controlled 컴포넌트입니다. props: placements, selectedCells, requiredCount, locked, onCellToggle. 기존 배치 클릭/이동/수납 동작은 없습니다. 시작 API 성공 시 부모가 locked=true와 예약된 placements를 전달합니다. 선택 취소는 시작 전만 가능. API 권한·예약 충돌·성공/포기 처리는 서버에서 구현하세요.

trees/에는 36개 SVG 원본, seedling.svg는 진행 대기 묘목입니다. catalog HTML로 디자인 확인이 가능합니다. 수종 ID는 oak/fir/cherry/ginkgo/willow/blossom. 상태 normal/library/wilted, 크기 small/large.

SessionPolicy.js와 순수 함수 검사는 계산 명세 검증용이며 서비스 타이머가 아닙니다. 실제 데이터는 서버 결과로 갱신합니다. preview HTML/CSS/JS에는 전체 화면 디자인과 로컬 상호작용이 있습니다. 시간표 생성 드래그/폼, 팀원 공개 WBS, 날짜별 기록, 프로필, 세션 시작/완료/포기 시연을 제공합니다. 메모리 예시이므로 새로고침 시 초기화됩니다.

## v3 추가 변경 — 2026-10-16
- 대시보드 카드 높이 자동 늘림 제거, 타이머 가로형으로 축소, 숲 최대 폭360px, 요약 카드는 짧은 바로가기로 압축. 칸 목록은 제거하고 숲에서 직접 선택. 작은 화면은 순서대로 세로 배치.
- 황금 은행은 둥근 참나무/벚꽃과 같은 둥근 수관에 부채꼴 은행잎을 부착. 작은/큰·일반/도서관/시듦 여섯 변형 모두 갱신.
- 아바타는 Unicode Emoji 18.0의 canonical fully-qualified+component 전체 3,972개 선택. 카테고리·한글/영문 검색·120개씩 페이지 이동. 국기·성별·피부색·ZWJ 문자열을 보존. Windows/Notion 고유 스티커나 업로드 이미지는 범위 밖이며 시스템 기본 이모지 글꼴로 표시. 플랫폼별 지원/모양은 다를 수 있음.
- 한글 검색어는 Unicode CLDR, 영문명은 emoji-test 데이터. 원본·라이선스·버전 포함, 오프라인 사용 가능. 프로필 저장 전에 이모지 하나가 목록에 존재하는지 검증; 서버도 동일 allowlist로 검증. 글자 하나로 잘라 저장하지 않음.
- React EmojiPicker.jsx, emoji-data.json, CSS를 함께 제공. 선택은 초안만 갱신하며 프로필 저장 버튼으로 확정.

## v4 레이아웃 수정 — 2026-10-16
- 모든 화면의 공통 헤더 제거. D-day는 PC 좌측 사이드바에 표시, 모바일에서는 하단 내비게이션 영역 상단의 작은 줄로 유지. 페이지 제목은 본문에 남김.
- 칸 목록 버튼·다이얼로그·React 대체 목록 삭제. 숲의 실제 빈 칸을 클릭/터치하거나 키보드 Tab·Enter로 직접 선택. 수종/위치 고정 정책은 유지.
- 공동 숲은 숲 최대 폭과 팀원 카드 높이를 줄이고 공개 피드를 압축. 멤버가 많을 때 목록 영역 안에서 스크롤.
- 캘린더 날짜 셀과 WBS 카드 간격 축소. 작업 추가 폼은 접기/펼치기로 필요한 때만 표시.
- 기록 페이지의 편집 필드·시간표 높이·주간 회고·주말 보충 간격 축소. 데스크톱은 2열 본문과 3열 회고, 작은 화면은 세로 배치. 전체 내용을 숨기거나 기능을 삭제하지 않음.
- 최신 납품본은 v4. 과거 변경 로그의 칸 목록 요구는 이 변경으로 폐기. 코드·디자인·Claude Code 지침 모두 최신 규칙 적용.

## v5 집중 화면·인증 수정 — 최우선 구현 지침
1. D-day는 시험까지 / D-n / 시험일을 한 줄로 배치, 줄 사이 여백 제거.
2. 시작 API 성공 후 /focus/:sessionId로 이동. 메뉴를 숨기고 서버 경과 시간에 따라 나무 성장 애니메이션. pause는 성장 중지. 다른 내부 페이지로 이동 시 취소/포기 확인, 서버 abandon 성공 후 이동. 브라우저 종료의 완전 감지/차단은 보장하지 않는다. 외부 교재 탭 전환을 실패로 취급하지 않음.
3. 초대 기반 이메일·실명·비밀번호 회원가입/로그인, 운영자 승인 상태를 도입. 실명은 본인/운영자만 조회하고 광장은 표시 이름 사용.
4. 서버 세션 쿠키 인증 대신 access JWT(15분, 메모리 Bearer)+refresh opaque token(7일, HttpOnly/Secure/SameSite cookie, DB 해시)로 교체. rotation/재사용 차단/로그아웃 폐기·서명과 claims 검사·CSRF/Origin 검사. JWT_SECRET은 서버 .env, 브라우저 저장소에 토큰 저장 금지.
5. 상세 정책·API·검증은 docs/10-focus-and-jwt.md가 기존 인증 지침보다 우선. 단계1에 로그인·가입·승인 게이트·JWT 갱신·집중 전용 페이지·이탈 guard까지 구현. UI 시안은 서버/인증을 구현하지 않으며 입력 자격 증명을 저장하거나 가짜 JWT를 만들지 않음.
6. PomodoroView.jsx는 표시 전용 컴포넌트. 부모가 서버 시간·상태·이탈 확인을 연결하고 디자인 preview.css의 focus/growth 스타일을 앱 스타일로 분리한다. 시안의 60배속/즉시 완료는 운영에 포함하지 않는다.
