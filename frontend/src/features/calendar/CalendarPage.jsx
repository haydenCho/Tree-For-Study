// 캘린더 /calendar (본인) 와 /calendar?member=id (팀원 공개 WBS, 읽기 전용).
// 날짜 클릭은 해당 날짜 기록으로 이동한다: 본인 → /records/:date, 팀원 → /members/:id/records/:date.
import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { get } from '../../lib/api.js'
import { kstDate } from '../../lib/time.js'
import MonthGrid from './MonthGrid.jsx'
import WbsList from './WbsList.jsx'
import { OwnWbsPanel } from './OwnWbsPanel.jsx'

const STUDY_MONTHS = ['2026-10', '2026-11']

function MonthNav({ month, setMonth }) {
  const i = STUDY_MONTHS.indexOf(month)
  const [y, m] = month.split('-').map(Number)
  return (
    <div className="inline month-nav">
      <button type="button" disabled={i <= 0} onClick={() => setMonth(STUDY_MONTHS[i - 1])} aria-label="이전 달">
        ←
      </button>
      <strong>
        {y}년 {m}월
      </strong>
      <button
        type="button"
        disabled={i === -1 || i >= STUDY_MONTHS.length - 1}
        onClick={() => setMonth(STUDY_MONTHS[i + 1])}
        aria-label="다음 달"
      >
        →
      </button>
    </div>
  )
}

export default function CalendarPage() {
  const [params] = useSearchParams()
  const member = params.get('member')
  const today = kstDate()
  const initial = STUDY_MONTHS.includes(today.slice(0, 7)) ? today.slice(0, 7) : STUDY_MONTHS[0]
  const [month, setMonth] = useState(initial)
  const [cal, setCal] = useState(null)
  const [memberWbs, setMemberWbs] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const q = member ? `&member=${member}` : ''
      setCal(await get(`/calendar?month=${month}${q}`))
      if (member) setMemberWbs(await get(`/members/${member}/wbs`))
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }, [month, member])

  useEffect(() => {
    load()
  }, [load])

  if (error && !cal)
    return (
      <section className="page">
        <p className="form-error" role="alert">
          {error}
        </p>
      </section>
    )
  if (!cal) return <section className="page" aria-busy="true" />

  const who = member ? cal.member : null
  return (
    <section id="calendar" className="page">
      <div className="heading">
        <div>
          <p className="eyebrow">{member ? 'MEMBER CALENDAR · 읽기 전용' : 'CALENDAR'}</p>
          <h1>
            {member ? (
              who ? (
                <>
                  <span className="emoji-glyph">{who.avatarEmoji}</span> {who.displayName}의 공개 일정
                </>
              ) : (
                '공개된 일정이 없어요'
              )
            ) : (
              '스터디 캘린더'
            )}
          </h1>
          <p>날짜를 누르면 그날의 기록으로 이동해요. 10.20 — 11.19 · 화–금 대면, 월·주말 자율.</p>
        </div>
        {member && (
          <Link className="button-like" to="/calendar">
            내 캘린더
          </Link>
        )}
      </div>
      <div className="calendar-layout">
        <article className="card">
          <div className="section-top">
            <MonthNav month={month} setMonth={setMonth} />
          </div>
          <MonthGrid
            month={month}
            days={cal.days}
            today={today}
            linkFor={(date) => (member ? `/members/${member}/records/${date}` : `/records/${date}`)}
            renderMeta={(d) =>
              member ? (
                d.hasPublicEntry && <small className="dot-public">공개</small>
              ) : (
                <small>
                  {d.goalCount ? `목표 ${d.goalCount}` : ''}
                  {d.isPublic ? ' · 공개' : ''}
                </small>
              )
            }
          />
        </article>
        <article className="card">
          {member ? (
            <>
              <h2>공개 WBS</h2>
              <WbsList items={memberWbs?.items || []} month={month} emptyText="공개된 WBS가 없어요." />
            </>
          ) : (
            <OwnWbsPanel month={month} />
          )}
        </article>
      </div>
    </section>
  )
}
