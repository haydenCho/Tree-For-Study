// 회원가입: 초대 코드 + 이메일(로그인 ID) + 실명 + 비밀번호/확인 → 승인 대기.
// 이메일 소유 확인 메일은 첫 버전 범위 밖이므로 '이메일 인증 완료'라고 표시하지 않는다.
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { post } from '../../lib/api.js'
import { AuthStory } from './AuthStory.jsx'

export default function RegisterPage() {
  const [form, setForm] = useState({ inviteCode: '', email: '', realName: '', password: '', passwordConfirm: '' })
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (form.password.length < 12) return setError('비밀번호는 12자 이상이어야 해요.')
    if (form.password !== form.passwordConfirm) return setError('비밀번호 확인이 일치하지 않아요.')
    setBusy(true)
    try {
      await post('/auth/register', form)
      setForm({ inviteCode: '', email: '', realName: '', password: '', passwordConfirm: '' })
      setDone(true)
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
          <div className="auth-tabs">
            <Link className="button-like" to="/login">
              로그인
            </Link>
            <button type="button" aria-pressed="true" className="primary">
              회원가입
            </button>
          </div>
          {done ? (
            <div role="status">
              <h2>가입 신청이 접수되었어요.</h2>
              <p>운영자가 실제 멤버와 확인한 뒤 승인하면 이용할 수 있어요. 승인 전에도 로그인해서 상태를 확인할 수 있어요.</p>
              <Link className="button-like primary" to="/login">
                로그인하러 가기
              </Link>
            </div>
          ) : (
            <form onSubmit={submit}>
              <label>
                초대 코드
                <input required autoComplete="off" value={form.inviteCode} onChange={set('inviteCode')} />
              </label>
              <label>
                이메일 (로그인 ID)
                <input type="email" required autoComplete="username" value={form.email} onChange={set('email')} />
              </label>
              <label>
                실명 <small>(본인과 운영자만 볼 수 있어요)</small>
                <input required maxLength={40} autoComplete="name" value={form.realName} onChange={set('realName')} />
              </label>
              <label>
                비밀번호 <small>(12~128자)</small>
                <input
                  type="password"
                  required
                  minLength={12}
                  maxLength={128}
                  autoComplete="new-password"
                  value={form.password}
                  onChange={set('password')}
                />
              </label>
              <label>
                비밀번호 확인
                <input
                  type="password"
                  required
                  autoComplete="new-password"
                  value={form.passwordConfirm}
                  onChange={set('passwordConfirm')}
                />
              </label>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <button type="submit" className="primary full" disabled={busy}>
                {busy ? '신청 중…' : '가입 신청'}
              </button>
              <p className="hint">공동 숲에는 실명 대신 마이페이지에서 정한 표시 이름과 이모지만 보여요.</p>
            </form>
          )}
        </section>
      </div>
    </main>
  )
}
