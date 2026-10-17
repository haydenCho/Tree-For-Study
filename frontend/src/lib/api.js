// API 클라이언트. 같은 출처 기준 경로(/api)를 백엔드로 프록시한다.
//
// 토큰 규칙(docs/10-focus-and-jwt.md):
// - 액세스 JWT는 이 모듈의 메모리 변수에만 보관한다. localStorage/sessionStorage/URL 금지.
// - refresh 토큰은 HttpOnly 쿠키라 JS가 읽지 못한다. 갱신 요청에는 CSRF 쿠키 값을
//   X-CSRF-Token 헤더로 함께 보낸다(이중 제출).
// - 401을 받으면 single-flight로 refresh를 한 번만 수행하고 원 요청을 한 번만 재시도한다.
//   403은 갱신하지 않는다. 무한 재시도는 하지 않는다.
const BASE = import.meta.env.VITE_API_BASE_URL || '/api'

let accessToken = null
let refreshPromise = null
const listeners = new Set()

export class ApiError extends Error {
  constructor(status, body) {
    const detail = body && typeof body === 'object' ? body.detail : null
    const message =
      (detail && typeof detail === 'object' && detail.message) ||
      (typeof detail === 'string' ? detail : null) ||
      (status === 0 ? '서버에 연결할 수 없어요. 네트워크를 확인해 주세요.' : `요청을 처리하지 못했어요 (${status}).`)
    super(message)
    this.status = status
    this.code = detail && typeof detail === 'object' ? detail.code : null
    this.body = body
  }
}

export function setAccessToken(token) {
  accessToken = token
}

export function hasAccessToken() {
  return Boolean(accessToken)
}

// 인증이 완전히 끊겼을 때(갱신 실패) 알림을 받는다.
export function onAuthLost(fn) {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

function readCookie(name) {
  const hit = document.cookie.split('; ').find((c) => c.startsWith(`${name}=`))
  return hit ? decodeURIComponent(hit.slice(name.length + 1)) : ''
}

export function hasCsrfCookie() {
  return Boolean(readCookie('tfs_csrf'))
}

async function rawFetch(path, { method = 'GET', body, headers = {}, auth = true } = {}) {
  const h = { ...headers }
  if (body !== undefined) h['Content-Type'] = 'application/json'
  if (auth && accessToken) h.Authorization = `Bearer ${accessToken}`
  let res
  try {
    res = await fetch(`${BASE}${path}`, {
      method,
      headers: h,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      credentials: 'same-origin',
      cache: 'no-store',
    })
  } catch {
    throw new ApiError(0, null)
  }
  if (res.status === 204) return { res, data: null }
  const type = res.headers.get('content-type') || ''
  const data = type.includes('application/json') ? await res.json() : await res.text()
  return { res, data }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

// refresh 쿠키로 새 액세스 토큰을 받는다. 동시에 여러 곳에서 불러도 실제 요청은 하나.
export function refreshSession() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      for (let attempt = 0; attempt < 2; attempt += 1) {
        const { res, data } = await rawFetch('/auth/refresh', {
          method: 'POST',
          auth: false,
          headers: { 'X-CSRF-Token': readCookie('tfs_csrf') },
        })
        if (res.ok) {
          accessToken = data.accessToken
          return data
        }
        // 다른 탭이 방금 회전했다면 공유 쿠키가 갱신될 때까지 잠깐 기다렸다 한 번 더.
        if (res.status === 409 && attempt === 0) {
          await sleep(700)
          continue
        }
        accessToken = null
        throw new ApiError(res.status, data)
      }
      throw new ApiError(401, null)
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

export async function api(path, options = {}) {
  let { res, data } = await rawFetch(path, options)
  if (res.status === 401 && options.auth !== false) {
    try {
      await refreshSession()
    } catch (err) {
      listeners.forEach((fn) => fn(err))
      throw err
    }
    ;({ res, data } = await rawFetch(path, options))
  }
  if (!res.ok) throw new ApiError(res.status, data)
  return data
}

// 자주 쓰는 형태의 축약
export const get = (path) => api(path)
export const post = (path, body) => api(path, { method: 'POST', body: body ?? {} })
export const put = (path, body) => api(path, { method: 'PUT', body })
export const patch = (path, body) => api(path, { method: 'PATCH', body })
export const del = (path) => api(path, { method: 'DELETE' })

// 인증 전용 호출(Origin/CSRF는 브라우저 + 아래 헤더로 충족)
export async function login(email, password) {
  const data = await api('/auth/login', { method: 'POST', body: { email, password }, auth: false })
  accessToken = data.accessToken
  return data
}

export async function logout() {
  try {
    await api('/auth/logout', {
      method: 'POST',
      auth: false,
      headers: { 'X-CSRF-Token': readCookie('tfs_csrf') },
    })
  } finally {
    accessToken = null
  }
}

export async function changePassword(body) {
  const data = await post('/auth/password', body)
  accessToken = data.accessToken
  return data
}

// 시작 요청 멱등키
export function newRequestId() {
  if (crypto.randomUUID) return crypto.randomUUID().replace(/-/g, '')
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, '0')).join('')
}
