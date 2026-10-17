// 대시보드 보조 카드. 출석·멤버 요약은 2단계에서 서버와 연결한다.
import { Link } from 'react-router-dom'

function Attendance() {
  return (
    <span className="badge" title="2단계에서 연결 예정">
      출석 체크 준비 중
    </span>
  )
}

function Members() {
  return (
    <article className="card">
      <h2>공동 숲</h2>
      <p>팀원 현황과 공동 숲은 다음 단계에서 열려요.</p>
      <Link className="button-like" to="/plaza">
        둘러보기
      </Link>
    </article>
  )
}

function NextSchedule({ study }) {
  return (
    <article className="card">
      <h2>스터디 일정</h2>
      <p>
        {study.studyStart.slice(5).replace('-', '.')} — {study.studyEnd.slice(5).replace('-', '.')} · 화–금 대면
      </p>
      <Link className="button-like" to="/calendar">
        캘린더
      </Link>
    </article>
  )
}

export const DashboardExtras = { Attendance, Members, NextSchedule }
