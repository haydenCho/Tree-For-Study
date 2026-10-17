// 운영자 설정: 가입 승인/거부, 회원 중지, 초대 코드 발급/폐기.
// 이 화면의 실명·이메일은 운영자에게만 보인다.
import { useCallback, useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import ConfirmDialog from '../../components/ConfirmDialog.jsx'
import { useToast } from '../../components/Toast.jsx'
import { get, post } from '../../lib/api.js'
import { useAuth } from '../../lib/auth.jsx'
import { AdminExtras } from './AdminExtras.jsx'

const STATUS = { pending: '승인 대기', active: '활성', rejected: '거부', disabled: '중지' }
const INVITE_STATE = { active: '사용 가능', expired: '만료', revoked: '폐기', used_up: '소진' }

export default function AdminPage() {
  const auth = useAuth()
  if (auth.user?.role !== 'operator') return <Navigate to="/" replace />
  return <Admin />
}

function Admin() {
  const toast = useToast()
  const [members, setMembers] = useState([])
  const [invites, setInvites] = useState([])
  const [newCode, setNewCode] = useState(null)
  const [inviteForm, setInviteForm] = useState({ label: '', maxUses: 10, ttlDays: 7 })
  const [disableTarget, setDisableTarget] = useState(null)

  const load = useCallback(async () => {
    try {
      const [m, i] = await Promise.all([get('/admin/members'), get('/admin/invites')])
      setMembers(m.items)
      setInvites(i.items)
    } catch (err) {
      toast(err.message)
    }
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  async function act(path, message) {
    try {
      await post(path)
      toast(message)
      load()
    } catch (err) {
      toast(err.message)
    }
  }

  async function createInvite(e) {
    e.preventDefault()
    try {
      const inv = await post('/admin/invites', inviteForm)
      setNewCode(inv.code)
      load()
    } catch (err) {
      toast(err.message)
    }
  }

  const active = members.filter((m) => m.status === 'active').length
  const pending = members.filter((m) => m.status === 'pending')

  return (
    <section id="admin" className="page">
      <div className="heading">
        <div>
          <p className="eyebrow">OPERATOR</p>
          <h1>운영자 설정</h1>
          <p>활성 멤버 {active} / 10명</p>
        </div>
      </div>
      <div className="profile-layout admin-layout">
        <article className="card">
          <h2>가입 승인 대기</h2>
          {!pending.length && <p className="hint">대기 중인 신청이 없어요.</p>}
          {pending.map((m) => (
            <div className="admin-row" key={m.id}>
              <div>
                <strong>{m.realName}</strong> <small>{m.email}</small>
                <br />
                <small>신청 {new Date(m.createdAt).toLocaleString('ko-KR')}</small>
              </div>
              <div className="inline">
                <button type="button" className="primary" onClick={() => act(`/admin/membership-requests/${m.id}/approve`, '승인했어요.')}>
                  승인
                </button>
                <button type="button" onClick={() => act(`/admin/membership-requests/${m.id}/reject`, '거부했어요.')}>
                  거부
                </button>
              </div>
            </div>
          ))}
          <h2 className="spaced">전체 멤버</h2>
          {members.map((m) => (
            <div className="admin-row" key={m.id}>
              <div>
                <span className="emoji-glyph">{m.avatarEmoji}</span> <strong>{m.displayName}</strong> <small>({m.realName} · {m.email})</small>
                <br />
                <small>
                  {STATUS[m.status]} · {m.role === 'operator' ? '운영자' : '멤버'}
                </small>
              </div>
              {m.status === 'active' && m.id !== undefined && m.role !== 'operator' && (
                <button type="button" className="danger" onClick={() => setDisableTarget(m)}>
                  중지
                </button>
              )}
            </div>
          ))}
        </article>
        <article className="card">
          <h2>초대 코드</h2>
          <form onSubmit={createInvite}>
            <label>
              메모
              <input maxLength={60} value={inviteForm.label} onChange={(e) => setInviteForm((f) => ({ ...f, label: e.target.value }))} />
            </label>
            <div className="inline">
              <label>
                최대 사용
                <input type="number" min={1} max={50} value={inviteForm.maxUses} onChange={(e) => setInviteForm((f) => ({ ...f, maxUses: Number(e.target.value) }))} />
              </label>
              <label>
                유효(일)
                <input type="number" min={1} max={30} value={inviteForm.ttlDays} onChange={(e) => setInviteForm((f) => ({ ...f, ttlDays: Number(e.target.value) }))} />
              </label>
            </div>
            <button type="submit" className="primary">
              초대 코드 발급
            </button>
          </form>
          {newCode && (
            <p className="reward" role="status">
              새 코드(지금 한 번만 표시): <code>{newCode}</code>
            </p>
          )}
          {invites.map((i) => (
            <div className="admin-row" key={i.id}>
              <div>
                <strong>{i.label || '초대'}</strong> <small>{INVITE_STATE[i.state]}</small>
                <br />
                <small>
                  {i.useCount}/{i.maxUses}회 · {new Date(i.expiresAt).toLocaleDateString('ko-KR')} 만료
                </small>
              </div>
              {i.state === 'active' && (
                <button type="button" onClick={() => act(`/admin/invites/${i.id}/revoke`, '초대를 폐기했어요.')}>
                  폐기
                </button>
              )}
            </div>
          ))}
        </article>
      </div>
      <AdminExtras />
      <ConfirmDialog
        open={Boolean(disableTarget)}
        title="이 멤버를 중지할까요?"
        confirmLabel="중지"
        danger
        onCancel={() => setDisableTarget(null)}
        onConfirm={async () => {
          const target = disableTarget
          setDisableTarget(null)
          await act(`/admin/members/${target.id}/disable`, '중지했어요. 기존 로그인도 즉시 해제됩니다.')
        }}
      >
        <p>{disableTarget?.displayName} 님의 모든 로그인이 해제되고 다시 로그인할 수 없어요.</p>
      </ConfirmDialog>
    </section>
  )
}
