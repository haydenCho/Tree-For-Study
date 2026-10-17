// 앱 라우트. React Router의 data router(createBrowserRouter)를 써야 집중 화면의
// 공식 navigation blocker(useBlocker)를 사용할 수 있다.
import { Navigate, createBrowserRouter } from 'react-router-dom'
import { Root } from './Root.jsx'
import { RequireMember } from './RequireMember.jsx'
import { AppLayout } from './AppLayout.jsx'
import LoginPage from '../features/auth/LoginPage.jsx'
import RegisterPage from '../features/auth/RegisterPage.jsx'
import DashboardPage from '../features/dashboard/DashboardPage.jsx'
import FocusPage from '../features/focus/FocusPage.jsx'
import RecordsPage from '../features/records/RecordsPage.jsx'
import MyPage from '../features/profile/MyPage.jsx'
import AdminPage from '../features/admin/AdminPage.jsx'
import PlazaPage from '../features/plaza/PlazaPage.jsx'
import CalendarPage from '../features/calendar/CalendarPage.jsx'
import { kstDate } from '../lib/time.js'

function TodayRecords() {
  return <Navigate to={`/records/${kstDate()}`} replace />
}

export const router = createBrowserRouter([
  {
    element: <Root />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
      {
        element: <RequireMember />,
        children: [
          // 집중 전용 화면: 사이드바·메뉴·footer 없이 단독 렌더링
          { path: '/focus/:sessionId', element: <FocusPage /> },
          {
            element: <AppLayout />,
            children: [
              { path: '/', element: <DashboardPage /> },
              { path: '/plaza', element: <PlazaPage /> },
              { path: '/calendar', element: <CalendarPage /> },
              { path: '/records', element: <TodayRecords /> },
              { path: '/records/:date', element: <RecordsPage /> },
              { path: '/members/:memberId/records/:date', element: <RecordsPage readOnly /> },
              { path: '/me', element: <MyPage /> },
              { path: '/admin', element: <AdminPage /> },
              { path: '*', element: <Navigate to="/" replace /> },
            ],
          },
        ],
      },
    ],
  },
])
