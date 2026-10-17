// 일반 화면 레이아웃: PC 좌측 208px 사이드바 / 모바일 하단 5개 메뉴. 공통 헤더 없음.
// 활성 집중 세션이 있으면 어떤 내부 주소로 들어와도 집중 화면으로 유도한다.
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { get, post } from '../lib/api.js'
import { useAuth } from '../lib/auth.jsx'

const MENU = [
  { to: '/', label: '대시보드', end: true },
  { to: '/plaza', label: '공동 숲' },
  { to: '/calendar', label: '캘린더' },
  { to: '/records', label: '기록' },
  { to: '/me', label: '마이페이지' },
]

function DDay({ study }) {
  if (!study) return <div className="sidebar-deadline" aria-hidden="true" />
  const ended = study.daysToExam < 0
  const label = study.daysToExam === 0 ? 'D-DAY' : `D-${study.daysToExam}`
  return (
    <div className="sidebar-deadline">
      <span>{ended ? '시험 종료' : '시험까지'}</span>
      {!ended && <strong>{label}</strong>}
      <small>{study.examDate.replaceAll('-', '.')}</small>
    </div>
  )
}

export function AppLayout() {
  const auth = useAuth()
  const navigate = useNavigate()
  const [study, setStudy] = useState(null)

  useEffect(() => {
    let alive = true
    get('/study').then((s) => alive && setStudy(s)).catch(() => {})
    // 새 탭/직접 주소 접근 시에도 활성 세션이 있으면 집중 화면으로 보낸다.
    get('/sessions/active')
      .then((r) => {
        if (alive && r.session) navigate(`/focus/${r.session.id}`, { replace: true })
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [navigate])

  useEffect(() => {
    // 30초 heartbeat(온라인 표시 전용). 실패해도 공부 상태에는 영향이 없다.
    const beat = () => post('/presence').catch(() => {})
    beat()
    const id = setInterval(beat, 30000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink to="/" className="brand" aria-label="tree for study 대시보드">
          ♧<b>tree for study</b>
          <small>같은 공간, 각자의 속도로.</small>
        </NavLink>
        <DDay study={study} />
        <nav aria-label="주 메뉴">
          {MENU.map((m) => (
            <NavLink key={m.to} to={m.to} end={m.end} className={({ isActive }) => (isActive ? 'active' : '')}>
              {m.label}
            </NavLink>
          ))}
        </nav>
        {auth.user?.role === 'operator' && (
          <NavLink to="/admin" className="account-link admin-link">
            운영자 설정
          </NavLink>
        )}
        <div className="side-bottom">
          <span className="emoji-glyph">{auth.user?.avatarEmoji}</span> {auth.user?.displayName}
          <br />
          <small>
            SAA 도서관 스터디
            <br />
            10.20 — 11.19 · 최대 10명
          </small>
        </div>
      </aside>
      <main>
        <Outlet />
        <footer>
          <span>Tree for Study · 시각 효과만 사용하는 공부 공간</span>
          <span>소리·진동·푸시 알림 없음</span>
        </footer>
      </main>
    </div>
  )
}
