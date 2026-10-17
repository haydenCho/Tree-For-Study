// 날짜·시간 표시 helper. 서버는 UTC로 저장하고, 화면은 한국 시간 기준으로 보여 준다.
const KST_FMT = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Seoul',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
})

// 한국 날짜 'YYYY-MM-DD'
export function kstDate(d = new Date()) {
  return KST_FMT.format(d)
}

export function formatClock(seconds) {
  const s = Math.max(0, Math.ceil(seconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  const mm = String(m).padStart(2, '0')
  const ss = String(sec).padStart(2, '0')
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

export function formatDuration(seconds) {
  const m = Math.round(seconds / 60)
  const h = Math.floor(m / 60)
  const rest = m % 60
  if (h && rest) return `${h}시간 ${rest}분`
  if (h) return `${h}시간`
  return `${rest}분`
}

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

export function prettyDate(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  const day = new Date(Date.UTC(y, m - 1, d)).getUTCDay()
  return `${m}월 ${d}일 (${WEEKDAYS[day]})`
}

export function shiftDate(iso, days) {
  const [y, m, d] = iso.split('-').map(Number)
  const t = new Date(Date.UTC(y, m - 1, d + days))
  return t.toISOString().slice(0, 10)
}

export function weekdayOf(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(Date.UTC(y, m - 1, d)).getUTCDay()
}

export function isValidIsoDate(iso) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || '')) return false
  const [y, m, d] = iso.split('-').map(Number)
  const t = new Date(Date.UTC(y, m - 1, d))
  return t.getUTCFullYear() === y && t.getUTCMonth() === m - 1 && t.getUTCDate() === d
}

// 서버 시계 기준 경과 계산: 응답의 serverNow와 수신 시각 차이로 오프셋을 보정한다.
export function serverOffsetMs(serverNowIso) {
  return new Date(serverNowIso).getTime() - Date.now()
}
