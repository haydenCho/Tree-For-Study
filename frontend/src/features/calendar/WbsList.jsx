// WBS 목록과 일정 막대(조회용). 막대는 선택한 달 안에서의 기간을 보여 준다.
// 생성·편집은 별도 폼에서 하며 막대를 드래그해 편집하지 않는다.
const STATUS = { planned: '예정', in_progress: '진행', done: '완료' }

function rangeStyle(task, month) {
  const [y, m] = month.split('-').map(Number)
  const first = Date.UTC(y, m - 1, 1)
  const days = new Date(Date.UTC(y, m, 0)).getUTCDate()
  const last = Date.UTC(y, m - 1, days)
  const toUtc = (iso) => {
    const [a, b, c] = iso.split('-').map(Number)
    return Date.UTC(a, b - 1, c)
  }
  const s = Math.max(first, toUtc(task.startDate))
  const e = Math.min(last, toUtc(task.endDate))
  if (e < s) return null
  const day = 86400000
  return { left: `${((s - first) / day / days) * 100}%`, width: `${(((e - s) / day + 1) / days) * 100}%` }
}

export default function WbsList({ items, month, onSelect, selectedId, emptyText = 'WBS가 없어요.' }) {
  if (!items.length) return <p className="hint">{emptyText}</p>
  const roots = items.filter((t) => !t.parentId || !items.some((p) => p.id === t.parentId))
  const childrenOf = (id) => items.filter((t) => t.parentId === id)
  const row = (t, child) => {
    const style = rangeStyle(t, month)
    const body = (
      <>
        <strong>
          {child ? '└ ' : ''}
          {t.title}
        </strong>
        <span>
          {t.startDate.slice(5).replace('-', '.')} – {t.endDate.slice(5).replace('-', '.')} · {STATUS[t.status]} · {t.progress}%
          {t.isPublic === false ? ' · 비공개' : ''}
        </span>
        <div className="track" aria-hidden="true">
          <i style={{ width: `${t.progress}%` }} />
        </div>
        <div className="schedule-track" aria-hidden="true">
          {style && <span className="schedule-range" style={style} />}
        </div>
      </>
    )
    return onSelect ? (
      <button
        type="button"
        key={t.id}
        className={`wbs-row${child ? ' child' : ''}`}
        aria-pressed={selectedId === t.id}
        onClick={() => onSelect(t)}
      >
        {body}
      </button>
    ) : (
      <div key={t.id} className={`wbs-row${child ? ' child' : ''}`}>
        {body}
      </div>
    )
  }
  return (
    <div className="wbs-list">
      {roots.map((t) => [row(t, false), ...childrenOf(t.id).map((c) => row(c, true))])}
    </div>
  )
}
