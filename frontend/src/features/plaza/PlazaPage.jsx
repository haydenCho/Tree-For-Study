// 공동 숲 = 스터디 광장. 요약·무작위 배치 숲·팀원 카드·공개 기록 피드.
// 나무에 hover/focus/tap 하면 소유자 카드(표시 이름·아바타·소개·공개 WBS 링크)를 연다.
// 이메일·실명·IP·비공개 제목은 서버가 보내지 않으며 화면에도 없다. 순위 경쟁 없음.
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ForestGrid from '../../components/ForestGrid.jsx'
import { get } from '../../lib/api.js'
import { formatDuration, prettyDate } from '../../lib/time.js'
import { speciesName } from '../../lib/trees.js'

const STATE = { focusing: '공부 중', paused: '일시정지', resting: '휴식', idle: '대기' }
const ATTEND = { present: '출석', not_checked: '미체크인', absent: '결석', holiday: '휴무', self: '자율일', none: '' }

export default function PlazaPage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [zone, setZone] = useState(null)
  const [owner, setOwner] = useState(null)

  const load = useCallback(async () => {
    try {
      const d = await get('/plaza')
      setData(d)
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }, [])

  useEffect(() => {
    load()
    // 10명 규모라 15초 polling으로 충분하다.
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [load])

  useEffect(() => {
    if (!owner) return undefined
    const onKey = (e) => e.key === 'Escape' && setOwner(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [owner])

  if (error && !data)
    return (
      <section className="page">
        <p className="form-error" role="alert">
          {error}
        </p>
      </section>
    )
  if (!data) return <section className="page" aria-busy="true" />

  const zoneIndex = zone ?? data.zones[data.zones.length - 1].index
  const cells = (data.zones.find((z) => z.index === zoneIndex)?.cells || []).map((c) => ({
    ...c,
    ownerName: c.owner?.displayName,
  }))
  const s = data.summary

  return (
    <section id="plaza" className="page">
      <div className="heading">
        <div>
          <p className="eyebrow">PLAZA</p>
          <h1>함께 자라는 공동 숲</h1>
          <p>
            전체 성공 집중 {formatDuration(s.totalSuccessSeconds)} · 성공 나무 {s.totalTrees}그루 · 오늘 출석 {s.todayPresent}/
            {s.members}명
          </p>
        </div>
        <span className="badge">지금 {s.focusingNow}명 공부 중</span>
      </div>
      <div className="plaza-layout">
        <article className="card">
          <div className="section-top">
            <h2>공동 숲</h2>
            {data.zones.length > 1 && (
              <div className="inline zone-tabs">
                {data.zones.map((z) => (
                  <button type="button" key={z.index} aria-pressed={z.index === zoneIndex} onClick={() => setZone(z.index)}>
                    구역 {z.index + 1}
                  </button>
                ))}
              </div>
            )}
          </div>
          <ForestGrid
            cells={cells}
            onTreeFocus={(item) => setOwner(item)}
            label="공동 숲: 나무를 선택하면 심은 멤버를 볼 수 있어요"
            className="community-forest"
          />
          <p className="hint">정상 완료한 나무만 서버가 빈 칸을 무작위로 골라 심어요. 위치는 바뀌지 않아요.</p>
          <p className="hint">오늘 함께한 집중 {formatDuration(s.todaySuccessSeconds)}</p>
        </article>
        <article className="card">
          <h2>팀원</h2>
          <div className="member-cards">
            {data.members.map((m) => (
              <Link key={m.id} className="member-card" to={`/calendar?member=${m.id}`} aria-label={`${m.displayName}의 공개 WBS 보기`}>
                <span className="avatar emoji-glyph">{m.avatarEmoji}</span>
                <span>
                  <strong>{m.displayName}</strong>
                  <small>
                    {STATE[m.state]}
                    {m.online ? ' · 접속 중' : ''} · 오늘 {formatDuration(m.todaySuccessSeconds)} · {m.todayTrees}그루
                  </small>
                </span>
                <em>{ATTEND[m.attendance]}</em>
              </Link>
            ))}
          </div>
          <div className="feed">
            <div className="section-top">
              <h2>공개 기록</h2>
            </div>
            {!data.feed.length && <p className="hint">아직 공개된 기록이 없어요.</p>}
            {data.feed.map((f) => (
              <div className="feed-item" key={`${f.kind}-${f.member.id}-${f.date}`}>
                <div>
                  <small>
                    <span className="emoji-glyph">{f.member.avatarEmoji}</span> {f.member.displayName} · {prettyDate(f.date)}
                    {f.kind === 'weekly' ? ' 주간 회고' : ''}
                  </small>
                  <p>{f.excerpt || '(내용 없음)'}</p>
                  {f.kind === 'daily' && f.goalsTotal > 0 && (
                    <small>
                      목표 {f.goalsDone}/{f.goalsTotal}
                    </small>
                  )}
                </div>
                {f.kind === 'daily' && (
                  <Link className="button-like" to={`/members/${f.member.id}/records/${f.date}`}>
                    열기
                  </Link>
                )}
              </div>
            ))}
          </div>
        </article>
      </div>
      {owner && (
        <aside className="owner-card" role="dialog" aria-label="나무 주인">
          <button type="button" onClick={() => setOwner(null)}>
            닫기
          </button>
          {owner.owner ? (
            <>
              <h3>
                <span className="avatar emoji-glyph">{owner.owner.avatarEmoji}</span> {owner.owner.displayName}
              </h3>
              <p className="pre">{owner.owner.bio || '소개가 없어요.'}</p>
              <p className="hint">
                {speciesName(owner.species)} · {owner.size === 'large' ? '큰' : '작은'} 나무
                {owner.state === 'library' ? ' · 도서관 장식' : ''}
              </p>
              <Link className="button-like" to={`/calendar?member=${owner.owner.id}`}>
                공개 WBS 보기
              </Link>
            </>
          ) : (
            <p>지금은 함께하지 않는 멤버의 나무예요.</p>
          )}
        </aside>
      )}
    </section>
  )
}
