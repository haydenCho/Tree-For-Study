// 주간 회고(잘한 점/어려웠던 점/다음 주 계획, 기본 비공개)와 주말 보충.
// 주간 합계는 성공한 집중 세션만 한국 날짜별로 나눠 보여 준다(서버 계산).
// 주말 보충: 이번 주 미완료 목표를 토/일로 이월하며 원본은 그대로 남는다(같은 대상일 중복 불가).
import { useCallback, useEffect, useState } from 'react'
import { useToast } from '../../components/Toast.jsx'
import { get, post, put } from '../../lib/api.js'
import { formatDuration, prettyDate, shiftDate, weekdayOf } from '../../lib/time.js'

const DAY = ['월', '화', '수', '목', '금', '토', '일']

function weekStartOf(iso) {
  const wd = weekdayOf(iso) // 0=일
  return shiftDate(iso, wd === 0 ? -6 : 1 - wd)
}

export default function Weekly({ date, onChange }) {
  const toast = useToast()
  const weekStart = weekStartOf(date)
  const [review, setReview] = useState(null)
  const [dirty, setDirty] = useState(false)
  const [undone, setUndone] = useState([])
  const [carry, setCarry] = useState({ goalId: '', target: shiftDate(weekStart, 5) })

  const load = useCallback(async () => {
    try {
      const [r, g] = await Promise.all([
        get(`/weekly-reviews/${weekStart}`),
        get(`/goals?from=${weekStart}&to=${shiftDate(weekStart, 4)}&done=false`),
      ])
      setReview(r)
      setDirty(false)
      setUndone(g.items)
    } catch (err) {
      toast(err.message)
    }
  }, [weekStart, toast])

  useEffect(() => {
    load()
  }, [load])

  if (!review) return null
  const set = (k) => (e) => {
    const v = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    setReview((r) => ({ ...r, [k]: v }))
    setDirty(true)
  }
  const max = Math.max(1, ...review.totals.days.map((d) => d.successSeconds))

  return (
    <article className="card review">
      <div className="section-top">
        <div>
          <h2>주간 회고 · {prettyDate(weekStart)} 주</h2>
          <small>
            이번 주 성공 집중 {formatDuration(review.totals.totalSeconds)} · 성공 나무 {review.totals.successTrees}그루
          </small>
        </div>
      </div>
      <div className="week-bars" aria-label="요일별 성공 집중 시간">
        {review.totals.days.map((d, i) => (
          <div key={d.date} className="week-bar" title={`${DAY[i]} ${formatDuration(d.successSeconds)}`}>
            <i style={{ height: `${(d.successSeconds / max) * 100}%` }} />
            <span>{DAY[i]}</span>
            <small>{d.successSeconds ? formatDuration(d.successSeconds) : '–'}</small>
          </div>
        ))}
      </div>
      <form
        onSubmit={async (e) => {
          e.preventDefault()
          try {
            const r = await put(`/weekly-reviews/${weekStart}`, {
              good: review.good,
              hard: review.hard,
              nextPlan: review.nextPlan,
              isPublic: review.isPublic,
            })
            setReview(r)
            setDirty(false)
            toast(r.isPublic ? '회고를 저장했어요 · 스터디에 공개 중' : '회고를 저장했어요 · 나만 보기')
          } catch (err) {
            toast(err.message)
          }
        }}
      >
        <div className="three">
          <label>
            잘한 점
            <textarea maxLength={3000} value={review.good} onChange={set('good')} />
          </label>
          <label>
            어려웠던 점
            <textarea maxLength={3000} value={review.hard} onChange={set('hard')} />
          </label>
          <label>
            다음 주 계획
            <textarea maxLength={3000} value={review.nextPlan} onChange={set('nextPlan')} />
          </label>
        </div>
        <div className="inline">
          <label className="check">
            <input type="checkbox" checked={review.isPublic} onChange={set('isPublic')} />
            주간 회고 공개
          </label>
          <button type="submit" className="primary" disabled={!dirty}>
            {dirty ? '회고 저장' : '저장됨'}
          </button>
        </div>
      </form>
      <form
        className="weekend"
        onSubmit={async (e) => {
          e.preventDefault()
          try {
            await post(`/goals/${carry.goalId}/carry`, { targetDate: carry.target })
            toast(`${prettyDate(carry.target)}로 보충 목표를 옮겼어요.`)
            setCarry((c) => ({ ...c, goalId: '' }))
            load()
            onChange?.()
          } catch (err) {
            toast(err.message)
          }
        }}
      >
        <h3>주말 보충</h3>
        <label>
          미완료 목표
          <select required value={carry.goalId} onChange={(e) => setCarry((c) => ({ ...c, goalId: e.target.value }))}>
            <option value="">{undone.length ? '선택' : '이번 주 미완료 목표 없음'}</option>
            {undone.map((g) => (
              <option key={g.id} value={g.id}>
                {prettyDate(g.date)} · {g.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          보충할 날
          <select value={carry.target} onChange={(e) => setCarry((c) => ({ ...c, target: e.target.value }))}>
            <option value={shiftDate(weekStart, 5)}>{prettyDate(shiftDate(weekStart, 5))}</option>
            <option value={shiftDate(weekStart, 6)}>{prettyDate(shiftDate(weekStart, 6))}</option>
          </select>
        </label>
        <button type="submit" disabled={!carry.goalId}>
          보충으로 옮기기
        </button>
      </form>
    </article>
  )
}
