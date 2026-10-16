# v5 검증 기록

2026-10-16 · 기획·디자인·UI 소스 패키지

- preview.html: IDs and references passed
- wireframes.html: IDs and references passed
- tree-catalog.html: IDs and references passed
- 36 tree SVGs + supplementary assets parsed; Pretendard WOFF2 and OFL verified
- Emoji 18.0: all 3972 canonical/component entries, Korean search labels and complex sequences verified
- JavaScript syntax and session reward boundary tests passed
- No audio, vibration or OS notification API in preview
- Standalone preview embeds Pretendard, tree assets, CSS, policy and JavaScript

## 검증 범위와 제한
위 항목은 정적 파일 검증과 순수 보상 함수 검사입니다. 실제 브라우저 렌더링/클릭/드래그·React Vite 빌드·서버 DB·실제 도서관 IP는 검증하지 않았습니다. 이전 브라우저 도구에서 로컬 서버 연결 시간 초과 및 file URL 정책 제한이 있어 우회하지 않았습니다. 시안은 실제 서비스를 구현한 결과가 아닙니다.

## v5 추가 확인
집중 시작 후 전용 화면 이동, 60배속 성장, pause/resume, 포기 확인 취소/확인, 완료 결과, reduced-motion, 로그인/가입 폼과 비밀번호 확인. 실제 서버 JWT 발급/검증/가입 승인/라우터 blocker는 아직 구현하지 않은 개발 범위입니다.

## 브라우저에서 확인할 동작
1. 대시보드 공부 40/50/60분 → 작은2/큰2/큰3, 필요한 칸 수만 선택 후 시작.
2. 시작 뒤 수종/위치 변경 차단, pause/resume, 완료 시연, 포기 확인→회색 시듦과 현재 세션0.
3. 공동 숲 나무 hover/focus/tap → 올바른 프로필, 팀원 카드→공개 WBS.
4. 캘린더 날짜→해당 일일 기록. 비공개 기록 접근 시 '공개 없음'.
5. 시간표 범위 드래그→시각 채움→내용 입력/저장, 블록 클릭→폼 수정, 동일 레이어 겹침 거부.
6. 일일 기록 공개/비공개 저장→광장 반영, 주간 회고/주말 보충 유지.
7. 프로필 변경→광장 카드 반영. 1440/1280/390/360폭, Pretendard, 숲 타일 직접 클릭/키보드 선택 확인.
8. 타이머 카드가 숲 높이에 늘어나지 않는지, 헤더 제거·사이드바 D-day·공동 숲/캘린더/기록 압축 레이아웃 확인.
9. 이모지 선택기 한글/영문/국기 검색, 카테고리, 첫/마지막 페이지, 선택/취소/프로필 저장 확인. 최신 이모지의 OS 표시 지원은 별도 확인.

시간표 기존 블록의 직접 이동/resize, 2단계 계층 WBS 편집, 실제 라우팅·서버 저장은 개발 명세에 포함되지만 HTML 시안은 신규 드래그 생성·폼 수정·간단한 WBS 추가까지 제공합니다. 운영 앱의 완료 버튼이나 강제 시간 조작 API로 시연 기능을 복사하지 마세요.
