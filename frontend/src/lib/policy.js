// 화면 미리보기용 보상 계산(ui/SessionPolicy.js와 같은 규칙).
// 서버가 같은 규칙을 독립적으로 검증하며, 실제 결과는 항상 서버 응답이 권위다.
export const FOCUS_MIN = 20
export const FOCUS_MAX = 180
export const REST_MIN = 1
export const REST_MAX = 60

export function treeCount(minutes) {
  return Math.floor((minutes * 60) / 1200)
}

export function treeSize(minutes) {
  return minutes * 60 >= 3000 ? 'large' : 'small'
}

export function validFocusMinutes(m) {
  return Number.isInteger(m) && m >= FOCUS_MIN && m <= FOCUS_MAX
}

export function validRestMinutes(m) {
  return Number.isInteger(m) && m >= REST_MIN && m <= REST_MAX
}
