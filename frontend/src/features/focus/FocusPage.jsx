// 집중 전용 화면 /focus/:sessionId (docs/10-focus-and-jwt.md).
//
// - 사이드바·메뉴·footer 없이 남은 시간, 성장하는 나무, 진행률, 일시정지/재개, 중도 포기만 제공.
// - 상태는 URL이 아니라 서버 세션 조회로 판단한다. 브라우저 interval은 표시 용도뿐이며
//   완료/보상 근거로 쓰지 않는다(완료는 서버 워커/조회가 확정).
// - 활성 세션 중 다른 내부 route로 이동하면 React Router의 useBlocker로 보류하고 포기
//   확인을 띄운다. 확인 시 서버 abandon이 성공해야 이동하며, 실패하면 머문다.
// - 외부 탭 전환·화면 잠금·visibilitychange만으로는 포기 처리하지 않는다.
// - beforeunload는 브라우저 기본 경고만 보조한다(문구/차단 보장 없음).
import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useBlocker, useLocation, useNavigate, useParams } from 'react-router-dom'
import ConfirmDialog from '../../components/ConfirmDialog.jsx'
import PomodoroView from '../../components/PomodoroView.jsx'
import { useToast } from '../../components/Toast.jsx'
import { get, post } from '../../lib/api.js'
import { formatClock, formatDuration, serverOffsetMs } from '../../lib/time.js'
import { SEEDLING, sizeLabel, speciesName, treeAsset } from '../../lib/trees.js'

const ACTIVE = ['focusing', 'paused']

function remainingOf(session, offsetMs) {
  if (!session) return 0
  if (session.status === 'focusing' && session.targetEndAt) {
    return Math.max(0, (new Date(session.targetEndAt).getTime() - (Date.now() + offsetMs)) / 1000)
  }
  return session.remainingSeconds
}

export default function FocusPage() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const location = useLocation()
  // 시작 직후에는 대시보드가 넘겨준 시작 응답으로 바로 그린다(이후 서버 조회로 갱신).
  const initial = location.state?.session?.id === sessionId ? location.state.session : null
  const [session, setSession] = useState(initial)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(null) // { via: 'button' | 'navigation' }
  const [confirmError, setConfirmError] = useState('')
  const [, setTick] = useState(0)
  const offset = useRef(initial ? serverOffsetMs(initial.serverNow) : 0)
  const wasHidden = useRef(false)

  const active = Boolean(session && ACTIVE.includes(session.status))

  const apply = useCallback((s) => {
    offset.current = serverOffsetMs(s.serverNow)
    setSession(s)
  }, [])

  const refresh = useCallback(async () => {
    try {
      apply(await get(`/sessions/${sessionId}`))
      setError('')
    } catch (err) {
      setError(err.status === 404 ? '집중 세션을 찾을 수 없어요.' : err.message)
    }
  }, [sessionId, apply])

  useEffect(() => {
    refresh()
  }, [refresh])

  // 화면 표시용 초 단위 갱신
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 250)
    return () => clearInterval(id)
  }, [])

  const remaining = remainingOf(session, offset.current)

  // 서버 상태 동기화: 평소 15초, 목표 시각 이후에는 완료 확정을 2초 간격으로 확인
  useEffect(() => {
    if (!active) return undefined
    const due = session.status === 'focusing' && remaining <= 0
    const id = setTimeout(refresh, due ? 2000 : 15000)
    return () => clearTimeout(id)
  }, [active, session, remaining <= 0, refresh]) // eslint-disable-line react-hooks/exhaustive-deps

  // 휴식 중에는 휴식 종료 시각을 확인한다.
  useEffect(() => {
    if (session?.rest?.state !== 'resting') return undefined
    const end = new Date(session.rest.endsAt).getTime() - offset.current
    const id = setTimeout(refresh, Math.max(1000, end - Date.now() + 500))
    return () => clearTimeout(id)
  }, [session, refresh])

  // 탭 제목으로 진행 상황 표시, 숨겨진 사이 완료되면 돌아올 때 토스트
  useEffect(() => {
    if (!session) return undefined
    if (active) document.title = `${formatClock(remaining)} · ${session.status === 'paused' ? '일시정지' : '집중 중'}`
    else document.title = session.status === 'completed' ? '집중 완료 · Tree for Study' : 'Tree for Study'
    return undefined
  })
  useEffect(() => {
    const onVis = () => {
      if (document.hidden) wasHidden.current = true
      else if (wasHidden.current) {
        wasHidden.current = false
        refresh()
      }
    }
    document.addEventListener('visibilitychange', onVis)
    return () => {
      document.removeEventListener('visibilitychange', onVis)
      document.title = 'Tree for Study'
    }
  }, [refresh])
  const prevStatus = useRef(null)
  useEffect(() => {
    if (prevStatus.current && ACTIVE.includes(prevStatus.current) && session?.status === 'completed') {
      toast(`집중 완료! ${session.treeCount}그루가 숲에 자리 잡았어요.`)
    }
    prevStatus.current = session?.status ?? null
  }, [session, toast])

  // 새로고침/닫기 시 브라우저 기본 경고(보조 수단)
  useEffect(() => {
    if (!active) return undefined
    const handler = (e) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [active])

  const blocker = useBlocker(
    useCallback(
      // 세션을 아직 불러오는 중에도 막는다(로딩 중 이탈로 guard를 우회하지 않도록).
      ({ currentLocation, nextLocation }) =>
        (active || (!session && !error)) && currentLocation.pathname !== nextLocation.pathname,
      [active, session, error],
    ),
  )
  useEffect(() => {
    if (blocker.state === 'blocked') {
      setConfirmError('')
      setConfirm({ via: 'navigation' })
    }
  }, [blocker.state])

  async function togglePause() {
    setBusy(true)
    try {
      apply(await post(`/sessions/${sessionId}/${session.status === 'paused' ? 'resume' : 'pause'}`))
    } catch (err) {
      toast(err.message)
      refresh()
    } finally {
      setBusy(false)
    }
  }

  async function confirmAbandon() {
    setBusy(true)
    setConfirmError('')
    try {
      const s = await post(`/sessions/${sessionId}/abandon`)
      apply(s)
      setConfirm(null)
      if (s.status === 'completed') toast('목표 시간에 이미 도달해 정상 완료로 처리되었어요.')
      if (blocker.state === 'blocked') blocker.proceed()
    } catch (err) {
      // 서버 실패 시 이동하지 않고 재시도를 안내한다.
      setConfirmError(`${err.message} 다시 시도해 주세요.`)
    } finally {
      setBusy(false)
    }
  }

  function cancelAbandon() {
    setConfirm(null)
    if (blocker.state === 'blocked') blocker.reset()
  }

  async function restAction(action) {
    setBusy(true)
    try {
      apply(await post(`/sessions/${sessionId}/rest`, { action }))
    } catch (err) {
      toast(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (error && !session) {
    return (
      <main className="focus-page">
        <div className="focus-result">
          <h2>{error}</h2>
          <button type="button" onClick={refresh}>
            다시 시도
          </button>{' '}
          <Link className="button-like" to="/">
            대시보드로
          </Link>
        </div>
      </main>
    )
  }
  if (!session) return <main className="focus-page" aria-busy="true" />

  const finished = !active
  const wilted = session.status === 'abandoned'
  const state = wilted ? 'wilted' : session.libraryAtStart ? 'library' : 'normal'
  const restRemaining =
    session.rest.state === 'resting' ? Math.max(0, (new Date(session.rest.endsAt).getTime() - (Date.now() + offset.current)) / 1000) : 0

  return (
    <main className="focus-page">
      <div className="focus-top">
        <span>
          {speciesName(session.species)} · {sizeLabel(session.size)} 나무 {session.treeCount}그루
          {session.libraryAtStart && ' · 도서관 장식'}
        </span>
        {finished && (
          <Link className="button-like" to="/">
            대시보드로 돌아가기
          </Link>
        )}
      </div>
      <PomodoroView
        remainingSeconds={remaining}
        totalSeconds={session.targetSeconds}
        paused={session.status === 'paused'}
        finished={finished}
        wilted={wilted}
        treeUrl={treeAsset(session.species, session.size, state)}
        seedUrl={SEEDLING}
        busy={busy}
        caption={
          active
            ? '다른 탭에서 교재를 보는 건 괜찮아요. 서비스 안의 다른 화면으로 이동하면 포기 여부를 물어봐요.'
            : ''
        }
        onTogglePause={togglePause}
        onRequestLeave={() => {
          setConfirmError('')
          setConfirm({ via: 'button' })
        }}
      />
      {error && (
        <p className="form-error focus-error" role="alert">
          서버와 동기화하지 못했어요: {error}
        </p>
      )}
      {finished && (
        <section className="focus-result" role="status">
          {wilted ? (
            <>
              <h2>이번 집중을 마쳤어요.</h2>
              <p>이번 세션 인정 시간 0 · 예약한 칸의 나무는 회색으로 시들어 자리에 남아요. 이전 완료 기록은 유지돼요.</p>
            </>
          ) : (
            <>
              <h2>한 번의 집중이 숲에 남았어요.</h2>
              <p>
                {formatDuration(session.targetSeconds)} 완료 · {session.treeCount}그루가 시작할 때 지정한 자리에 남아요.
              </p>
              {session.rest.state === 'none' && (
                <button type="button" className="primary" disabled={busy} onClick={() => restAction('start')}>
                  휴식 시작 ({formatDuration(session.rest.seconds)})
                </button>
              )}
              {session.rest.state === 'resting' && (
                <p>
                  휴식 중 · {formatClock(restRemaining)} 남음{' '}
                  <button type="button" disabled={busy} onClick={() => restAction('end')}>
                    휴식 끝내기
                  </button>
                </p>
              )}
              {session.rest.state === 'rest_completed' && <p>휴식 시간이 끝났어요. 다음 집중을 준비해 볼까요?</p>}
              {session.rest.state === 'rest_ended' && <p>휴식을 마쳤어요.</p>}
            </>
          )}
          <button type="button" onClick={() => navigate('/')}>
            대시보드로 돌아가기
          </button>
        </section>
      )}
      <ConfirmDialog
        open={Boolean(confirm)}
        title="정말 이번 집중을 포기할까요?"
        confirmLabel={confirm?.via === 'navigation' ? '포기하고 이동' : '포기하기'}
        cancelLabel="계속 공부하기"
        danger
        busy={busy}
        error={confirmError}
        onConfirm={confirmAbandon}
        onCancel={cancelAbandon}
      >
        <p>이번 세션 시간은 초기화되고 예약한 나무가 시듭니다. 이전에 완료한 기록은 그대로 남아요.</p>
      </ConfirmDialog>
    </main>
  )
}
