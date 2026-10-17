// 대시보드 보조 영역: 출석 체크, 도서관 인식 안내, 멤버 요약, 스터디 일정.
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useToast } from '../../components/Toast.jsx'
import { post } from '../../lib/api.js'

const STATUS_TEXT = {
  present: '오늘 출석 완료',
  not_checked: '출석 체크',
  holiday: '오늘은 휴무일',
  self: '자율일 체크인',
}

function Attendance({ attendance, onChange }) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  if (!attendance || !attendance.todayKind) {
    return <span className="badge">스터디 기간 외</span>
  }
  const status = attendance.todayStatus
  const done = status === 'present'
  const disabled = busy || done || status === 'holiday'
  return (
    <div className="attendance-box">
      <button
        type="button"
        className={done ? 'attendance-done' : 'primary'}
        disabled={disabled}
        aria-pressed={done}
        onClick={async () => {
          setBusy(true)
          try {
            await post('/attendance/check-in')
            toast('출석했어요. 오늘도 함께해요!')
            onChange?.()
          } catch (err) {
            toast(err.message)
          } finally {
            setBusy(false)
          }
        }}
      >
        {done ? '✔ ' : ''}
        {STATUS_TEXT[status] || '출석 체크'}
      </button>
      <small>
        출석 {attendance.presentDays}일 · 대면일 {attendance.countedDays}일 기준
      </small>
    </div>
  )
}

function Library({ recognized }) {
  if (!recognized) return null
  return (
    <p className="library-note" role="status">
      📚 도서관 네트워크로 인식돼요 · 지금 시작하면 나무에 도서관 장식이 붙어요(시작 요청에서 다시 확인)
    </p>
  )
}

function Members({ members }) {
  return (
    <article className="card">
      <h2>공동 숲</h2>
      <p>{members ? `멤버 ${members.active}명 · 지금 ${members.focusingNow}명 공부 중` : '팀원 현황을 불러오는 중'}</p>
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

export const DashboardExtras = { Attendance, Library, Members, NextSchedule }
