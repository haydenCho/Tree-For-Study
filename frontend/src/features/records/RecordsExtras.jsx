// 기록 화면 보조 영역: 드래그 시간표(본인 편집 / 팀원 읽기 전용)와 주간 회고·주말 보충.
import Timetable from './Timetable.jsx'
import Weekly from './Weekly.jsx'

function TimetableArea({ date, entry, readOnly, onChange }) {
  return <Timetable date={date} blocks={entry.blocks || []} readOnly={readOnly} onChange={onChange} />
}

function WeeklyArea({ date, onChange }) {
  return <Weekly date={date} onChange={onChange} />
}

export const RecordsExtras = { Timetable: TimetableArea, Weekly: WeeklyArea }
