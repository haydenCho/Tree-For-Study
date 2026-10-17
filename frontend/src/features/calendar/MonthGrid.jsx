// 월간 달력. 날짜 셀은 링크(해당 날짜 기록으로 이동)이며, WBS 막대 선택과는 분리된 동작이다.
import { Link } from 'react-router-dom'

const KIND = { in_person: '대면', self: '자율', holiday: '휴무' }
const WEEK = ['일', '월', '화', '수', '목', '금', '토']

export default function MonthGrid({ month, days, today, linkFor, renderMeta }) {
  const [y, m] = month.split('-').map(Number)
  const lead = new Date(Date.UTC(y, m - 1, 1)).getUTCDay()
  return (
    <div className="month">
      <div className="weekdays" aria-hidden="true">
        {WEEK.map((w) => (
          <span key={w}>{w}</span>
        ))}
      </div>
      <div className="month-grid">
        {Array.from({ length: lead }, (_, i) => (
          <span key={`lead-${i}`} className="day outside" aria-hidden="true" />
        ))}
        {days.map((d) => {
          const n = Number(d.date.slice(8))
          const cls = `day${d.date === today ? ' today' : ''}${d.kind ? '' : ' outside'}${d.kind === 'holiday' ? ' holiday' : ''}`
          const label = `${m}월 ${n}일${d.kind ? ` ${KIND[d.kind]}` : ''}`
          return (
            <Link key={d.date} className={cls} to={linkFor(d.date)} aria-label={label}>
              <span>{n}</span>
              <small className={d.kind === 'in_person' ? 'meeting' : ''}>{d.kind ? KIND[d.kind] : ''}</small>
              {renderMeta?.(d)}
            </Link>
          )
        })}
      </div>
    </div>
  )
}
