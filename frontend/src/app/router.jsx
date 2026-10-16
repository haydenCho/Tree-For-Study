import { createBrowserRouter } from 'react-router-dom'
import { App } from './App.jsx'

// Stage 0: a single landing route proving the frontend<->backend wiring.
// Real routes (auth gate, dashboard, /focus/:sessionId with navigation blocker,
// plaza, calendar, records, mypage) are added from stage 1.
export const router = createBrowserRouter([
  { path: '/', element: <App /> },
])
