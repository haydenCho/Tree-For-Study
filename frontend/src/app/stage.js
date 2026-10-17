// 개발 진행 단계 정의와 현재 단계 값.
// 한 단계가 끝날 때마다 아래 currentStage 숫자만 올리면 좌하단 배지가 갱신된다.
export const STAGES = [
  { id: 0, label: '스캐폴딩', desc: 'compose · React · FastAPI · Postgres' },
  { id: 1, label: '인증·대시보드 세션', desc: '가입/승인 · JWT · 세션 · 배치 · 일일 기록' },
  { id: 2, label: '출석·광장', desc: '출석 · 도서관 IP · 공동 숲 · 공개 WBS' },
  { id: 3, label: '캘린더·WBS·기록', desc: '드래그 시간표 · 보충 · 주간 회고' },
  { id: 4, label: '배포·검수', desc: 'EC2/HTTPS · 백업 · 통합 검수' },
]

// 현재 구현이 반영된 개발 단계. 다음 단계 완료 시 이 값을 올린다.
export const currentStage = 1
