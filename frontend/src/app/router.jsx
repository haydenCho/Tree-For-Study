import { createBrowserRouter } from 'react-router-dom'
import { App } from './App.jsx'

// 0단계: 프론트엔드<->백엔드 연결을 확인하는 단일 랜딩 라우트.
// 실제 라우트(인증 게이트, 대시보드, 이탈 guard가 있는 /focus/:sessionId,
// 광장, 캘린더, 기록, 마이페이지)는 1단계부터 추가한다.
export const router = createBrowserRouter([
  { path: '/', element: <App /> },
])
