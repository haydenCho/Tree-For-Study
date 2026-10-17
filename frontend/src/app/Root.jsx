// 최상위 레이아웃: 인증 컨텍스트, 토스트, 좌하단 개발 단계 배지.
import { Outlet } from 'react-router-dom'
import { AuthProvider } from '../lib/auth.jsx'
import { ToastProvider } from '../components/Toast.jsx'
import { StageBadge } from './StageBadge.jsx'

export function Root() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Outlet />
        <StageBadge />
      </ToastProvider>
    </AuthProvider>
  )
}
