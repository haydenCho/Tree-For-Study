// 승인 게이트. 로그인하지 않았으면 /login, 승인 대기/거부 상태면 안내 화면만 보여 준다.
// pending 회원은 인증되었더라도 스터디 데이터 화면에 들어갈 수 없다(서버도 403).
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../lib/auth.jsx'
import PendingPage from '../features/auth/PendingPage.jsx'

export function RequireMember() {
  const auth = useAuth()
  const location = useLocation()
  if (auth.phase === 'loading') {
    return (
      <main className="splash" aria-busy="true">
        <p>숲을 불러오는 중…</p>
      </main>
    )
  }
  if (!auth.user) {
    return <Navigate to="/login" replace state={{ from: location.pathname, expired: auth.expired }} />
  }
  if (auth.user.status !== 'active') return <PendingPage />
  return <Outlet />
}
