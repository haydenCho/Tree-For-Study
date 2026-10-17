// 인증 상태 컨텍스트.
// 새로고침 시 refresh 쿠키로 액세스 토큰을 다시 받고 /me를 조회한다. 갱신 자체는
// 공부 세션에 영향을 주지 않는다(세션 상태는 항상 서버가 판단).
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import * as api from './api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [state, setState] = useState({ phase: 'loading', user: null })

  const loadMe = useCallback(async () => {
    const me = await api.get('/me')
    setState({ phase: 'ready', user: me })
    return me
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!api.hasCsrfCookie()) {
        if (!cancelled) setState({ phase: 'ready', user: null })
        return
      }
      try {
        await api.refreshSession()
        if (!cancelled) await loadMe()
      } catch {
        if (!cancelled) setState({ phase: 'ready', user: null })
      }
    })()
    const off = api.onAuthLost(() => setState({ phase: 'ready', user: null, expired: true }))
    return () => {
      cancelled = true
      off()
    }
  }, [loadMe])

  const value = useMemo(
    () => ({
      ...state,
      async login(email, password) {
        const data = await api.login(email, password)
        setState({ phase: 'ready', user: data.user })
        return data.user
      },
      async logout() {
        try {
          await api.logout()
        } finally {
          setState({ phase: 'ready', user: null })
        }
      },
      setUser(user) {
        setState((s) => ({ ...s, user }))
      },
      reload: loadMe,
    }),
    [state, loadMe],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
