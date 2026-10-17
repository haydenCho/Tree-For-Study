// 대시보드: 왼쪽 타이머 설정, 오른쪽 수종 선택·크기/개수 미리보기·고정 개인 숲.
// 시작 API가 성공한 뒤에만 /focus/:sessionId로 이동한다. 실제 보상은 서버가 확정한다.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import ForestGrid from '../../components/ForestGrid.jsx'
import { useToast } from '../../components/Toast.jsx'
import { get, newRequestId, post } from '../../lib/api.js'
import { FOCUS_MAX, FOCUS_MIN, REST_MAX, REST_MIN, treeCount, treeSize, validFocusMinutes, validRestMinutes } from '../../lib/policy.js'
import { formatDuration, prettyDate } from '../../lib/time.js'
import { SPECIES, sizeLabel, speciesName, treeAsset } from '../../lib/trees.js'
import { DashboardExtras } from './DashboardExtras.jsx'

const ZONE_CELLS = 36

export default function DashboardPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const [data, setData] = useState(null)
  const [loadError, setLoadError] = useState('')
  const [minutes, setMinutes] = useState('60')
  const [rest, setRest] = useState('10')
  const [species, setSpecies] = useState('oak')
  const [zoneIndex, setZoneIndex] = useState(0)
  const [selected, setSelected] = useState([])
  const [starting, setStarting] = useState(false)
  const [startError, setStartError] = useState('')
  const requestId = useRef(newRequestId())
  const initialised = useRef(false)

  const load = useCallback(async () => {
    try {
      const d = await get('/dashboard')
      if (d.activeSession) {
        navigate(`/focus/${d.activeSession.id}`, { replace: true })
        return
      }
      setData(d)
      setLoadError('')
      if (!initialised.current) {
        initialised.current = true
        setMinutes(String(d.defaults.focusMinutes))
        setRest(String(d.defaults.restMinutes))
        // 가장 최근 구역부터 보여 준다.
        setZoneIndex(Math.max(0, d.zones.length - 1))
      }
    } catch (err) {
      setLoadError(err.message)
    }
  }, [navigate])

  useEffect(() => {
    load()
  }, [load])

  const m = Number(minutes)
  const r = Number(rest)
  const minutesOk = validFocusMinutes(m)
  const restOk = validRestMinutes(r)
  const need = minutesOk ? treeCount(m) : 0
  const size = minutesOk ? treeSize(m) : 'small'

  const zones = data?.zones || []
  const zoneFree = zones.map((z) => ZONE_CELLS - z.cells.length)
  const canAddZone = need > 0 && zoneFree.every((free) => free < need)
  const isNewZone = zoneIndex === zones.length
  const zoneCells = isNewZone ? [] : zones[zoneIndex]?.cells || []
  const currentFree = isNewZone ? ZONE_CELLS : zoneFree[zoneIndex] ?? 0

  // 시간이 줄면 넘치는 선택을 잘라 낸다.
  useEffect(() => {
    setSelected((s) => (s.length > need ? s.slice(0, need) : s))
  }, [need])

  const toggle = (cell) => {
    setStartError('')
    setSelected((s) => {
      const exists = s.some((c) => c.row === cell.row && c.col === cell.col)
      if (exists) return s.filter((c) => !(c.row === cell.row && c.col === cell.col))
      if (s.length >= need) return s
      return [...s, cell]
    })
  }

  async function start() {
    if (!minutesOk || !restOk || selected.length !== need) return
    setStarting(true)
    setStartError('')
    try {
      const s = await post('/sessions', {
        species,
        targetMinutes: m,
        restMinutes: r,
        zoneIndex,
        plots: selected,
        requestId: requestId.current,
      })
      requestId.current = newRequestId()
      navigate(`/focus/${s.id}`, { state: { session: s } })
    } catch (err) {
      setStartError(err.message)
      if (err.status === 409) {
        requestId.current = newRequestId()
        setSelected([])
        await load()
      }
    } finally {
      setStarting(false)
    }
  }

  const startLabel = useMemo(() => {
    if (!minutesOk) return `공부 시간은 ${FOCUS_MIN}~${FOCUS_MAX}분이에요`
    if (!restOk) return `휴식 시간은 ${REST_MIN}~${REST_MAX}분이에요`
    if (currentFree < need) return '이 구역에 빈 칸이 부족해요'
    if (selected.length < need) return `${need - selected.length}칸을 더 선택해 주세요`
    return starting ? '시작하는 중…' : '집중 시작'
  }, [minutesOk, restOk, need, selected.length, starting, currentFree])

  if (loadError && !data) {
    return (
      <section className="page">
        <p className="form-error" role="alert">
          {loadError}
        </p>
        <button type="button" onClick={load}>
          다시 시도
        </button>
      </section>
    )
  }
  if (!data) return <section className="page" aria-busy="true" />

  return (
    <section id="dashboard" className="page">
      <div className="heading">
        <div>
          <p className="eyebrow">{prettyDate(data.study.today)}</p>
          <h1>오늘의 집중이, 숲의 한 자리가 되도록.</h1>
          <p>나무를 고르고 자리를 정한 뒤, 나만의 공부를 시작해요.</p>
        </div>
        <DashboardExtras.Attendance attendance={data.attendance} onChange={load} />
      </div>

      <div className="hero">
        <article className="card timer">
          <p className="eyebrow">MY FOCUS</p>
          <h2>한 번의 집중, 하나의 약속</h2>
          <div className="clock">
            <span>시작 전</span>
            <strong>{minutesOk ? `${String(m).padStart(2, '0')}:00` : '--:--'}</strong>
            <small>서버 시간 기준으로 진행돼요</small>
          </div>
          <div className="inline">
            <label>
              공부(분)
              <input
                type="number"
                inputMode="numeric"
                min={FOCUS_MIN}
                max={FOCUS_MAX}
                value={minutes}
                onChange={(e) => setMinutes(e.target.value)}
                aria-invalid={!minutesOk}
              />
            </label>
            <label>
              휴식(분)
              <input
                type="number"
                inputMode="numeric"
                min={REST_MIN}
                max={REST_MAX}
                value={rest}
                onChange={(e) => setRest(e.target.value)}
                aria-invalid={!restOk}
              />
            </label>
          </div>
          <p className="reward" role="status">
            {minutesOk
              ? `${speciesName(species)} · ${sizeLabel(size)} 나무 ${need}그루 · ${need}칸 필요`
              : `${FOCUS_MIN}~${FOCUS_MAX}분 사이 정수로 입력해 주세요`}
          </p>
          <DashboardExtras.Library recognized={data.libraryRecognized} />
          {startError && (
            <p className="form-error" role="alert">
              {startError}
            </p>
          )}
          <button
            type="button"
            className="primary full"
            disabled={starting || !minutesOk || !restOk || selected.length !== need || currentFree < need}
            onClick={start}
          >
            {startLabel}
          </button>
          <p className="hint">
            완료해야 나무가 확정돼요. 중도 포기하면 이번 세션 시간은 0이 되고 나무가 회색으로 시들어요. 이전 기록은 유지돼요.
          </p>
        </article>

        <article className="card forest-card">
          <div className="section-top">
            <div>
              <p className="eyebrow">MY GROWING SPACE</p>
              <h2>시작 전에, 나무의 자리를 골라요.</h2>
            </div>
          </div>
          <div className="species" role="group" aria-label="수종 선택">
            {SPECIES.map((s) => (
              <button
                type="button"
                key={s.id}
                aria-pressed={species === s.id}
                onClick={() => setSpecies(s.id)}
                title={s.name}
              >
                <img src={treeAsset(s.id, size, 'normal')} alt="" />
                {s.name}
              </button>
            ))}
          </div>
          <div className="section-top compact">
            <span role="status">
              {selected.length} / {need}칸 선택 · 이 구역 빈 칸 {currentFree}
            </span>
            <div className="inline zone-tabs">
              {zones.length > 1 &&
                zones.map((z) => (
                  <button
                    type="button"
                    key={z.index}
                    aria-pressed={zoneIndex === z.index}
                    onClick={() => {
                      setZoneIndex(z.index)
                      setSelected([])
                    }}
                  >
                    구역 {z.index + 1}
                  </button>
                ))}
              {(canAddZone || isNewZone) && (
                <button
                  type="button"
                  aria-pressed={isNewZone}
                  onClick={() => {
                    setZoneIndex(zones.length)
                    setSelected([])
                  }}
                >
                  새 구역
                </button>
              )}
              <button type="button" onClick={() => setSelected([])} disabled={!selected.length}>
                선택 해제
              </button>
            </div>
          </div>
          <ForestGrid
            cells={zoneCells}
            selectedCells={selected}
            requiredCount={need}
            onCellToggle={toggle}
            label={`개인 숲 구역 ${zoneIndex + 1}: 빈 칸을 눌러 나무 자리를 선택`}
          />
          <div className="stats">
            <div>
              <span>오늘 성공 집중</span>
              <strong className="small">{formatDuration(data.today.successSeconds)}</strong>
            </div>
            <div>
              <span>오늘 성공 나무</span>
              <strong>{data.today.successTrees}</strong>
            </div>
            <div>
              <span>시든 나무</span>
              <strong>{data.today.wiltedTrees}</strong>
            </div>
          </div>
        </article>
      </div>

      <div className="bottom-grid">
        <article className="card">
          <h2>오늘 목표</h2>
          <p>
            {data.goals.length
              ? `${data.goals.filter((g) => g.done).length} / ${data.goals.length}개 완료 · ${data.goals[0].title}`
              : '아직 오늘 목표가 없어요.'}
          </p>
          <Link className="button-like" to={`/records/${data.study.today}`}>
            기록 열기
          </Link>
        </article>
        <DashboardExtras.Members members={data.members} />
        <DashboardExtras.NextSchedule study={data.study} />
      </div>
    </section>
  )
}
