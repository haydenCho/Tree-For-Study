// 기록 화면 보조 영역. 드래그 시간표·주간 회고·주말 보충은 3단계에서 구현한다.
function Timetable() {
  return (
    <article className="card">
      <h2>시간표</h2>
      <p className="hint">드래그 시간표는 3단계에서 열려요.</p>
    </article>
  )
}

function Weekly() {
  return null
}

export const RecordsExtras = { Timetable, Weekly }
