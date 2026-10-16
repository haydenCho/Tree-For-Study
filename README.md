# Tree for Study · 기획 및 개발 전달 패키지

작성일: 2026-10-16 · 상태: 최종 검토용 제안 v1.0

이 패키지는 서비스 서버 구현물이 아닙니다. 문서, 다운로드용 디자인 시안, 재사용 가능한 UI 소스와 Claude Code 작업 지침입니다. 실제 로그인·기록 저장·알림은 개발 단계에서 연결합니다.

## 읽는 순서
1. `docs/01-product-plan.md` — 서비스 전체 정책과 범위
2. `design/wireframes.html` — PC·모바일 화면 구조
3. `design/preview.html` — 색상 적용 디자인과 칸 클릭 배치 시연
4. `docs/02-design-spec.md` — 화면·컴포넌트·에셋 사용법
5. `docs/03-development-plan.md` — 단계별 검수 기준
6. `prompts/00-setup.md` — Claude Code 개발 환경 구성 프롬프트
7. `prompts/01-first-development.md` — 1차 개발 프롬프트

## 열기
`design/preview.html`과 `design/wireframes.html`은 압축을 모두 풀고 브라우저에서 직접 엽니다. 인터넷이나 빌드가 필요하지 않습니다. 디자인 예시 데이터는 실제 스터디 기록이 아닙니다. 데모 데이터는 새로고침하면 초기화됩니다.

`ui/`에는 원본 SVG, CSS 토큰, React JavaScript 컴포넌트가 있습니다. React 코드는 Vite 프로젝트에 복사해서 사용하는 소스이며, 이 폴더 자체가 설치 가능한 프로젝트는 아닙니다. `ui/README.md`를 참고하세요.

## 확정 조건
- 4~8명, PC 우선·모바일 대응, React + JavaScript + Vite, FastAPI, PostgreSQL.
- 자율 집중, 차단 기능 없음, 일시정지·중도 종료 불이익 없음.
- 2.5D 고정 시점, 칸 클릭 배치, 사용자 수종 편집·회전 없음.
- Docker Compose + EC2. Claude Code는 단계별 개발 및 커밋만, push는 사용자만.

## 검토할 제안값
기본 타이머 50/10분, 누적 25분당 나무 1그루, 10:10까지 정상 출석, 6×6 숲 구역, 도서관 나무의 장식 조건은 제안값입니다. 모두 설정 또는 명시적인 정책 상수로 관리합니다. 이 값들은 사용자에게 확정받은 사실로 간주하지 않습니다.

교재 원문과 기존 Forest 이미지 파일은 패키지에 포함하지 않았습니다. UI SVG는 이 서비스를 위한 별도 도형 소스이며 참조 화면을 복제한 이미지가 아닙니다.
