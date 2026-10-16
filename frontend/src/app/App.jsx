import { useEffect, useState } from 'react'
import { apiFetch } from '../lib/api.js'

// 0단계 점검 화면: 개발 프록시를 통해 /api/health를 호출해
// 전체 연결(브라우저 -> Vite/Caddy -> FastAPI)이 되는지 확인한다.
// 1단계에서 실제 인증 게이트 + 대시보드로 교체된다.
export function App() {
  const [state, setState] = useState({ phase: 'checking' })

  useEffect(() => {
    apiFetch('/health')
      .then((body) => setState({ phase: 'ok', body }))
      .catch((err) => setState({ phase: 'fail', err: err.message }))
  }, [])

  return (
    <main className="stage0">
      <h1>Tree for Study</h1>
      <p className="muted">0단계 · 스캐폴딩</p>
      <p>
        백엔드 상태:{' '}
        {state.phase === 'checking' && <span className="status">확인 중…</span>}
        {state.phase === 'ok' && <span className="status ok">{state.body.status}</span>}
        {state.phase === 'fail' && <span className="status fail">연결 불가 ({state.err})</span>}
      </p>
      <p className="muted">
        다음: 초대 기반 인증, 운영자 승인 게이트, 대시보드 집중 세션.
      </p>
    </main>
  )
}
