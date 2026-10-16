// 얇은 fetch 래퍼. 같은 출처 기준 경로(/api)를 백엔드로 프록시한다.
// 액세스 JWT(1단계)는 메모리에만 보관하고 Bearer 헤더로 붙인다.
// localStorage/sessionStorage/URL에는 토큰을 저장하지 않는다.
const BASE = import.meta.env.VITE_API_BASE_URL || '/api'

let accessToken = null

export function setAccessToken(token) {
  accessToken = token
}

export async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include', // 인증 라우트에서 refresh 쿠키를 함께 전송
    ...options,
    headers,
  })
  const contentType = res.headers.get('content-type') || ''
  const body = contentType.includes('application/json') ? await res.json() : await res.text()
  if (!res.ok) {
    const err = new Error(`API ${res.status}`)
    err.status = res.status
    err.body = body
    throw err
  }
  return body
}
