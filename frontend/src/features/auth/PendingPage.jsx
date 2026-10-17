// 승인 대기/거부 안내. 이 상태에서는 스터디 데이터에 접근할 수 없다.
import { useState } from 'react'
import { useAuth } from '../../lib/auth.jsx'

export default function PendingPage() {
  const auth = useAuth()
  const [checking, setChecking] = useState(false)
  const status = auth.user?.status
  return (
    <main className="auth-page">
      <section className="card pending-card" role="status">
        <p className="eyebrow">MEMBERSHIP</p>
        {status === 'pending' && (
          <>
            <h1>운영자 승인을 기다리고 있어요.</h1>
            <p>운영자가 실제 스터디 멤버인지 확인한 뒤 승인하면 숲에 들어갈 수 있어요.</p>
          </>
        )}
        {status === 'rejected' && (
          <>
            <h1>가입 신청이 승인되지 않았어요.</h1>
            <p>잘못된 신청이라고 생각되면 운영자에게 직접 문의해 주세요.</p>
          </>
        )}
        <div className="inline">
          <button
            type="button"
            className="primary"
            disabled={checking}
            onClick={async () => {
              setChecking(true)
              try {
                await auth.reload()
              } finally {
                setChecking(false)
              }
            }}
          >
            {checking ? '확인 중…' : '승인 상태 다시 확인'}
          </button>
          <button type="button" onClick={() => auth.logout()}>
            로그아웃
          </button>
        </div>
      </section>
    </main>
  )
}
