import React from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { router } from './app/router.jsx'
import './styles/index.css'

// 라우터가 Root 레이아웃(인증·토스트·좌하단 단계 배지)을 포함한다.
createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
