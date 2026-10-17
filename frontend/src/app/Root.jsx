// 최상위 레이아웃: 인증 컨텍스트와 토스트.
import { Outlet } from 'react-router-dom'
import { AuthProvider } from '../lib/auth.jsx'
import { ToastProvider } from '../components/Toast.jsx'

export function Root() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Outlet />
      </ToastProvider>
    </AuthProvider>
  )
}
