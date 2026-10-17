// 날짜별 기록 /records/:date (본인) 및 /members/:id/records/:date (팀원 공개 기록, 읽기 전용).
// 오늘 계획 텍스트·체크 목표·실제 기록·공개 토글(기본 비공개)을 제공한다.
import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import { useToast } from '../../components/Toast.jsx'
import { del, get, patch, post, put } from '../../lib/api.js'
import { isValidIsoDate, kstDate, prettyDate, shiftDate } from '../../lib/time.js'
import { RecordsExtras } from './RecordsExtras.jsx'

export default function RecordsPage({ readOnly = false }) {
  const { date, memberId } = useParams()
  if (!isValidIsoDate(date)) return <Navigate to={`/records/${kstDate()}`} replace />
  return readOnly ? <MemberRecord memberId={memberId} date={date} /> : <OwnRecord key={date} date={date} />
}

function DateNav({ date, base }) {
  return (
    <div className="inline date-nav">
      <Link className="button-like" to={`${base}/${shiftDate(date, -1)}`} aria-label="이전 날짜">
        ← 이전
      </Link>
      <Link className="button-like" to={`${base}/${kstDate()}`}>
        오늘
      </Link>
      <Link className="button-like" to={`${base}/${shiftDate(date, 1)}`} aria-label="다음 날짜">
        다음 →
      </Link>
    </div>
  )
}

function OwnRecord({ date }) {
  const toast = useToast()
  const [entry, setEntry] = useState(null)
  const [draft, setDraft] = useState({ planText: '', recordText: '', isPublic: false })
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [goalTitle, setGoalTitle] = useState('')

  const load = useCallback(async () => {
    try {
      const e = await get(`/daily-entries/${date}`)
      setEntry(e)
      setDraft({ planText: e.planText, recordText: e.recordText, isPublic: e.isPublic })
      setDirty(false)
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }, [date])

  useEffect(() => {
    load()
  }, [load])

  const set = (key) => (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    setDraft((d) => ({ ...d, [key]: value }))
    setDirty(true)
  }

  async function save(e) {
    e?.preventDefault()
    setSaving(true)
    try {
      const saved = await put(`/daily-entries/${date}`, draft)
      setEntry(saved)
      setDirty(false)
      toast(saved.isPublic ? '저장했어요 · 스터디 멤버에게 공개 중' : '저장했어요 · 나만 보기')
    } catch (err) {
      toast(err.message)
    } finally {
      setSaving(false)
    }
  }

  async function addGoal(e) {
    e.preventDefault()
    if (!goalTitle.trim()) return
    try {
      const g = await post('/goals', { date, title: goalTitle.trim() })
      setEntry((en) => ({ ...en, goals: [...en.goals, g] }))
      setGoalTitle('')
    } catch (err) {
      toast(err.message)
    }
  }

  async function toggleGoal(goal) {
    try {
      const g = await patch(`/goals/${goal.id}`, { done: !goal.done })
      setEntry((en) => ({ ...en, goals: en.goals.map((x) => (x.id === g.id ? g : x)) }))
    } catch (err) {
      toast(err.message)
    }
  }

  async function removeGoal(goal) {
    try {
      await del(`/goals/${goal.id}`)
      setEntry((en) => ({ ...en, goals: en.goals.filter((x) => x.id !== goal.id) }))
    } catch (err) {
      toast(err.message)
    }
  }

  if (error && !entry)
    return (
      <section className="page">
        <p className="form-error" role="alert">
          {error}
        </p>
      </section>
    )
  if (!entry) return <section className="page" aria-busy="true" />

  return (
    <section id="records" className="page">
      <div className="heading">
        <div>
          <p className="eyebrow">DAILY RECORD</p>
          <h1>{prettyDate(date)}의 기록</h1>
          <p>계획과 실제 기록을 남겨요. 기록 작성일이 아니라 대상 날짜 기준으로 저장돼요.</p>
        </div>
        <DateNav date={date} base="/records" />
      </div>
      <div className="record-layout">
        <article className="card">
          <form onSubmit={save}>
            <label>
              오늘 계획
              <textarea rows={3} maxLength={5000} value={draft.planText} onChange={set('planText')} />
            </label>
            <div className="goals">
              <h3>체크 목표</h3>
              <ul className="goal-list">
                {entry.goals.map((g) => (
                  <li key={g.id}>
                    <label className="check">
                      <input type="checkbox" checked={g.done} onChange={() => toggleGoal(g)} />
                      <span className={g.done ? 'done' : ''}>{g.title}</span>
                      {g.carriedFromId && <small className="badge">보충</small>}
                    </label>
                    <button type="button" className="link-button" onClick={() => removeGoal(g)} aria-label={`${g.title} 삭제`}>
                      삭제
                    </button>
                  </li>
                ))}
                {!entry.goals.length && <li className="hint">아직 목표가 없어요.</li>}
              </ul>
            </div>
            <label>
              실제 공부 기록
              <textarea rows={5} maxLength={5000} value={draft.recordText} onChange={set('recordText')} />
            </label>
            <label className="check public-toggle">
              <input type="checkbox" checked={draft.isPublic} onChange={set('isPublic')} />
              스터디 멤버에게 이 날짜 기록 공개
            </label>
            <p className="hint">
              공개하면 이 날짜의 계획·목표·실제 기록·시간표를 같은 스터디 멤버에게 함께 공유해요(인터넷 공개 아님). 비밀
              메모가 있다면 비공개로 두세요.
            </p>
            <button type="submit" className="primary" disabled={saving || !dirty}>
              {saving ? '저장 중…' : dirty ? '저장' : '저장됨'}
            </button>
          </form>
          <form className="inline goal-add" onSubmit={addGoal}>
            <label>
              목표 추가
              <input value={goalTitle} maxLength={120} onChange={(e) => setGoalTitle(e.target.value)} placeholder="예: VPC 오답 정리" />
            </label>
            <button type="submit" disabled={!goalTitle.trim()}>
              추가
            </button>
          </form>
        </article>
        <RecordsExtras.Timetable date={date} entry={entry} onChange={load} />
      </div>
      <RecordsExtras.Weekly date={date} goals={entry.goals} onChange={load} />
    </section>
  )
}

function MemberRecord({ memberId, date }) {
  const [entry, setEntry] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    setEntry(null)
    get(`/members/${memberId}/daily-entries/${date}`)
      .then(setEntry)
      .catch((err) => setError(err.message))
  }, [memberId, date])
  if (error)
    return (
      <section className="page">
        <p className="form-error">{error}</p>
      </section>
    )
  if (!entry) return <section className="page" aria-busy="true" />
  return (
    <section id="records" className="page">
      <div className="heading">
        <div>
          <p className="eyebrow">MEMBER RECORD · 읽기 전용</p>
          <h1>
            {entry.public ? (
              <>
                <span className="emoji-glyph">{entry.member.avatarEmoji}</span> {entry.member.displayName}의 {prettyDate(date)}
              </>
            ) : (
              `${prettyDate(date)}의 기록`
            )}
          </h1>
        </div>
        <DateNav date={date} base={`/members/${memberId}/records`} />
      </div>
      {!entry.public ? (
        <article className="card">
          <p>공개된 기록이 없어요.</p>
        </article>
      ) : (
        <div className="record-layout">
          <article className="card">
            <h2>오늘 계획</h2>
            <p className="pre">{entry.planText || '—'}</p>
            <h3>체크 목표</h3>
            <ul className="goal-list">
              {entry.goals.map((g) => (
                <li key={g.id}>
                  <span className={g.done ? 'done' : ''}>
                    {g.done ? '✔ ' : '○ '}
                    {g.title}
                  </span>
                </li>
              ))}
              {!entry.goals.length && <li className="hint">목표 없음</li>}
            </ul>
            <h2>실제 공부 기록</h2>
            <p className="pre">{entry.recordText || '—'}</p>
          </article>
          <RecordsExtras.Timetable date={date} entry={entry} readOnly />
        </div>
      )}
    </section>
  )
}
