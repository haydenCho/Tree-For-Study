// Thin fetch wrapper. Same-origin base (/api) proxied to the backend.
// Access JWT (stage 1) will be held in memory and attached here as a Bearer header;
// it is never read from localStorage/sessionStorage/URL.
const BASE = import.meta.env.VITE_API_BASE_URL || '/api'

let accessToken = null

export function setAccessToken(token) {
  accessToken = token
}

export async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}) }
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include', // send the refresh cookie on auth routes
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
