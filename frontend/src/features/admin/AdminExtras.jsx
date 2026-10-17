// 운영자 추가 설정: 도서관 IP 등록과 접속 IP 진단, 휴무일 지정, 출석 정정(사유 필수).
// 접속 IP 진단은 운영자 전용 API이며 일반 사용자 화면에는 IP를 보여 주지 않는다.
import { useCallback, useEffect, useState } from 'react'
import { useToast } from '../../components/Toast.jsx'
import { api, get, post, put } from '../../lib/api.js'
import { kstDate } from '../../lib/time.js'

const ATTEND = { present: '출석', not_checked: '미체크인', absent: '결석', holiday: '휴무', self: '자율일', none: '기간 외' }
const KIND = { in_person: '대면', self: '자율', holiday: '휴무' }

export function AdminExtras() {
  return (
    <div className="profile-layout admin-layout admin-extras">
      <LibrarySettings />
      <AttendanceSettings />
    </div>
  )
}

function LibrarySettings() {
  const toast = useToast()
  const [diag, setDiag] = useState(null)
  const [nets, setNets] = useState({ items: [], ruleVersion: 0 })
  const [form, setForm] = useState({ network: '', label: '' })

  const load = useCallback(async () => {
    try {
      const [d, n] = await Promise.all([get('/admin/network-diagnostic'), get('/admin/library-networks')])
      setDiag(d)
      setNets(n)
    } catch (err) {
      toast(err.message)
    }
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  async function add(e) {
    e.preventDefault()
    try {
      await post('/admin/library-networks', form)
      setForm({ network: '', label: '' })
      toast('도서관 주소를 등록했어요.')
      load()
    } catch (err) {
      toast(err.message)
    }
  }

  async function remove(id) {
    try {
      await api(`/admin/library-networks/${id}`, { method: 'DELETE' })
      load()
    } catch (err) {
      toast(err.message)
    }
  }

  return (
    <article className="card">
      <h2>도서관 네트워크</h2>
      <p className="hint">
        도서관 Wi-Fi에 연결하고 VPN을 끈 상태에서 아래 '서버가 본 접속 IP'를 확인해 등록하세요. 다른 기기에서도 같은 값인지 확인하고,
        확인하지 않은 넓은 범위는 등록하지 마세요.
      </p>
      {diag && (
        <p className="reward" role="status">
          서버가 본 접속 IP: <code>{diag.observedIp || '알 수 없음'}</code> · {diag.recognized ? '도서관으로 인식됨' : '미등록'}
          {diag.viaTrustedProxy ? ' · 프록시 경유' : ' · 직접 연결'}
        </p>
      )}
      <form onSubmit={add}>
        <div className="inline">
          <label>
            IP 또는 CIDR
            <input required value={form.network} onChange={(e) => setForm((f) => ({ ...f, network: e.target.value }))} placeholder="예: 203.0.113.7" />
          </label>
          <label>
            메모
            <input maxLength={60} value={form.label} onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))} />
          </label>
        </div>
        <div className="inline">
          <button type="submit" className="primary">
            등록
          </button>
          {diag?.observedIp && (
            <button type="button" onClick={() => setForm((f) => ({ ...f, network: diag.observedIp }))}>
              현재 접속 IP 채우기
            </button>
          )}
        </div>
      </form>
      <p className="hint">규칙 버전 {nets.ruleVersion} · 판정은 세션 시작 요청 시점에만 적용돼요.</p>
      {nets.items.map((n) => (
        <div className="admin-row" key={n.id}>
          <div>
            <code>{n.network}</code> <small>{n.label}</small>
          </div>
          <button type="button" className="danger" onClick={() => remove(n.id)}>
            삭제
          </button>
        </div>
      ))}
    </article>
  )
}

function AttendanceSettings() {
  const toast = useToast()
  const [day, setDay] = useState(kstDate())
  const [roster, setRoster] = useState(null)
  const [kindNote, setKindNote] = useState('')
  const [fix, setFix] = useState({ userId: '', status: 'present', reason: '' })

  const load = useCallback(async () => {
    try {
      setRoster(await get(`/admin/attendance?day=${day}`))
    } catch (err) {
      toast(err.message)
    }
  }, [day, toast])

  useEffect(() => {
    load()
  }, [load])

  async function setKind(kind) {
    try {
      await put(`/admin/study-dates/${day}`, { kind, note: kindNote })
      toast(`${day}을(를) ${KIND[kind]}일로 지정했어요.`)
      load()
    } catch (err) {
      toast(err.message)
    }
  }

  async function submitFix(e) {
    e.preventDefault()
    try {
      await put(`/admin/attendance/${fix.userId}/${day}`, { status: fix.status, reason: fix.reason })
      toast('출석을 정정했어요.')
      setFix({ userId: '', status: 'present', reason: '' })
      load()
    } catch (err) {
      toast(err.message)
    }
  }

  return (
    <article className="card">
      <h2>출석·휴무</h2>
      <label>
        날짜
        <input type="date" value={day} min="2026-10-20" max="2026-11-19" onChange={(e) => setDay(e.target.value)} />
      </label>
      <p className="hint">현재 종류: {roster?.kind ? KIND[roster.kind] : '기간 외'} · 휴무일은 출석률 분모에서 빠져요.</p>
      <div className="inline">
        <label>
          메모
          <input maxLength={100} value={kindNote} onChange={(e) => setKindNote(e.target.value)} placeholder="예: 도서관 휴관" />
        </label>
      </div>
      <div className="inline">
        {Object.entries(KIND).map(([k, v]) => (
          <button type="button" key={k} onClick={() => setKind(k)} aria-pressed={roster?.kind === k}>
            {v}일로 지정
          </button>
        ))}
      </div>
      <h3>멤버 출석</h3>
      {roster?.items.map((m) => (
        <div className="admin-row" key={m.userId}>
          <div>
            <strong>{m.displayName}</strong> <small>({m.realName})</small>
            <br />
            <small>
              {ATTEND[m.status]}
              {m.reason ? ` · 정정 사유: ${m.reason}` : ''}
            </small>
          </div>
        </div>
      ))}
      <form onSubmit={submitFix}>
        <h3>출석 정정</h3>
        <label>
          멤버
          <select required value={fix.userId} onChange={(e) => setFix((f) => ({ ...f, userId: e.target.value }))}>
            <option value="">선택</option>
            {roster?.items.map((m) => (
              <option key={m.userId} value={m.userId}>
                {m.displayName} ({m.realName})
              </option>
            ))}
          </select>
        </label>
        <label>
          상태
          <select value={fix.status} onChange={(e) => setFix((f) => ({ ...f, status: e.target.value }))}>
            <option value="present">출석</option>
            <option value="absent">결석</option>
            <option value="holiday">휴무</option>
          </select>
        </label>
        <label>
          사유(필수)
          <input required maxLength={300} value={fix.reason} onChange={(e) => setFix((f) => ({ ...f, reason: e.target.value }))} />
        </label>
        <button type="submit">정정 저장</button>
      </form>
    </article>
  )
}
