// 로그인 화면. 입력한 자격 증명은 저장하지 않고, 응답의 액세스 토큰은 메모리에만 둔다.
import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../../lib/auth.jsx'
import { AuthStory } from './AuthStory.jsx'

export default function LoginPage() {
  const auth = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(location.state?.expired ? '로그인이 만료되었어요. 다시 로그인해 주세요.' : '')
  const [busy, setBusy] = useState(false)

  if (auth.phase === 'ready' && auth.user) return <Navigate to={location.state?.from || '/'} replace />

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await auth.login(email, password)
      setPassword('')
      navigate(location.state?.from || '/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth-page">
      <div className="auth-layout">
        <AuthStory />
        <section className="card auth-card">
          <div className="auth-tabs" role="tablist">
            <button type="button" aria-pressed="true" className="primary">
              로그인
            </button>
            <Link className="button-like" to="/register">
              회원가입
            </Link>
          </div>
          <form onSubmit={submit}>
            <label>
              이메일
              <input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <label>
              비밀번호
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button type="submit" className="primary full" disabled={busy}>
              {busy ? '로그인 중…' : '로그인'}
            </button>
          </form>
          <p className="hint">계정 복구는 운영자에게 문의해 주세요.</p>
        </section>
      </div>
    </main>
  )
}
