import { useEffect, useState } from 'react'
import { apiFetch } from '../lib/api.js'

// Stage 0 smoke screen: calls /api/health through the dev proxy to confirm the
// full chain (browser -> Vite/Caddy -> FastAPI) is wired. Replaced by the real
// auth gate + dashboard in stage 1.
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
      <p className="muted">Stage 0 · scaffolding</p>
      <p>
        Backend health:{' '}
        {state.phase === 'checking' && <span className="status">checking…</span>}
        {state.phase === 'ok' && <span className="status ok">{state.body.status}</span>}
        {state.phase === 'fail' && <span className="status fail">unreachable ({state.err})</span>}
      </p>
      <p className="muted">
        Next: invite-based auth, operator approval gate, dashboard focus session.
      </p>
    </main>
  )
}
