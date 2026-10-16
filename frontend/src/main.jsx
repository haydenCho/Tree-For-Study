import React from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { router } from './app/router.jsx'
import { StageBadge } from './app/StageBadge.jsx'
import './styles/index.css'

// 라우터 화면과 함께, 모든 화면 위에 개발 단계 배지를 고정 표시한다.
createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
    <StageBadge />
  </React.StrictMode>,
)
