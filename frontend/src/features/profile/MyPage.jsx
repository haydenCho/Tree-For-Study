// 마이페이지: 표시 이름·소개·아바타·기본 타이머, 비밀번호 변경, 로그아웃.
// 실명·이메일은 본인에게만 보인다. 비밀번호 입력값은 저장 후 즉시 비운다.
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import EmojiPicker from '../../components/EmojiPicker.jsx'
import { useToast } from '../../components/Toast.jsx'
import { changePassword, patch } from '../../lib/api.js'
import { useAuth } from '../../lib/auth.jsx'

export default function MyPage() {
  const auth = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const u = auth.user
  const [draft, setDraft] = useState({
    displayName: u.displayName,
    bio: u.bio,
    avatarEmoji: u.avatarEmoji,
    defaultFocusMinutes: u.defaultFocusMinutes,
    defaultRestMinutes: u.defaultRestMinutes,
  })
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [pw, setPw] = useState({ currentPassword: '', newPassword: '', newPasswordConfirm: '' })
  const [pwError, setPwError] = useState('')
  const [pwBusy, setPwBusy] = useState(false)

  const set = (key, number) => (e) => setDraft((d) => ({ ...d, [key]: number ? Number(e.target.value) : e.target.value }))

  async function save(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const me = await patch('/me/profile', draft)
      auth.setUser(me)
      toast('프로필을 저장했어요. 공동 숲 카드에도 바로 반영돼요.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function submitPassword(e) {
    e.preventDefault()
    setPwError('')
    if (pw.newPassword !== pw.newPasswordConfirm) return setPwError('새 비밀번호 확인이 일치하지 않아요.')
    setPwBusy(true)
    try {
      await changePassword(pw)
      toast('비밀번호를 바꿨어요. 다른 기기의 로그인은 모두 해제됐어요.')
    } catch (err) {
      setPwError(err.message)
    } finally {
      setPw({ currentPassword: '', newPassword: '', newPasswordConfirm: '' })
      setPwBusy(false)
    }
  }

  return (
    <section id="profile" className="page">
      <div className="heading">
        <div>
          <p className="eyebrow">MY PAGE</p>
          <h1>나의 숲 정보</h1>
          <p>공동 숲에는 표시 이름·아바타·소개만 보여요.</p>
        </div>
        <button
          type="button"
          onClick={async () => {
            await auth.logout()
            navigate('/login')
          }}
        >
          로그아웃
        </button>
      </div>
      <div className="profile-layout">
        <article className="card">
          <form onSubmit={save}>
            <h2>프로필</h2>
            <EmojiPicker value={draft.avatarEmoji} onChange={(emoji) => setDraft((d) => ({ ...d, avatarEmoji: emoji }))} />
            <label>
              표시 이름 <small>(2~20자)</small>
              <input required minLength={2} maxLength={20} value={draft.displayName} onChange={set('displayName')} />
            </label>
            <label>
              소개 <small>({draft.bio.length}/160)</small>
              <textarea rows={3} maxLength={160} value={draft.bio} onChange={set('bio')} />
            </label>
            <div className="inline">
              <label>
                기본 공부(분)
                <input type="number" min={20} max={180} value={draft.defaultFocusMinutes} onChange={set('defaultFocusMinutes', true)} />
              </label>
              <label>
                기본 휴식(분)
                <input type="number" min={1} max={60} value={draft.defaultRestMinutes} onChange={set('defaultRestMinutes', true)} />
              </label>
            </div>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button type="submit" className="primary" disabled={saving}>
              {saving ? '저장 중…' : '프로필 저장'}
            </button>
          </form>
        </article>
        <article className="card">
          <h2>계정</h2>
          <dl className="account-info">
            <dt>이메일</dt>
            <dd>{u.email}</dd>
            <dt>실명</dt>
            <dd>{u.realName}</dd>
            <dt>권한</dt>
            <dd>{u.role === 'operator' ? '운영자' : '멤버'}</dd>
          </dl>
          <form onSubmit={submitPassword}>
            <h3>비밀번호 변경</h3>
            <label>
              현재 비밀번호
              <input
                type="password"
                required
                autoComplete="current-password"
                value={pw.currentPassword}
                onChange={(e) => setPw((p) => ({ ...p, currentPassword: e.target.value }))}
              />
            </label>
            <label>
              새 비밀번호 <small>(12~128자)</small>
              <input
                type="password"
                required
                minLength={12}
                maxLength={128}
                autoComplete="new-password"
                value={pw.newPassword}
                onChange={(e) => setPw((p) => ({ ...p, newPassword: e.target.value }))}
              />
            </label>
            <label>
              새 비밀번호 확인
              <input
                type="password"
                required
                autoComplete="new-password"
                value={pw.newPasswordConfirm}
                onChange={(e) => setPw((p) => ({ ...p, newPasswordConfirm: e.target.value }))}
              />
            </label>
            {pwError && (
              <p className="form-error" role="alert">
                {pwError}
              </p>
            )}
            <button type="submit" disabled={pwBusy}>
              {pwBusy ? '변경 중…' : '비밀번호 변경'}
            </button>
          </form>
        </article>
      </div>
    </section>
  )
}
