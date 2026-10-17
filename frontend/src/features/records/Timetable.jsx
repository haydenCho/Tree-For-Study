// 드래그 시간표(한국 시간 00:00~24:00, 15분 단위). 왼쪽 열은 계획, 오른쪽 열은 실제 기록.
//
// - 빈 곳을 위아래로 드래그하면 범위를 선택하고 폼을 연다(역방향 드래그도 정규화).
//   드래그 threshold(6px) 미만이면 클릭으로 보고 15분 한 칸을 선택한다.
// - 기존 블록 본문을 드래그하면 이동, 아래 손잡이를 드래그하면 끝 시각 조절. 클릭하면 폼으로 수정.
// - pointer capture를 쓰고 pointercancel(스크롤 전환 등) 시 원래 상태로 복구한다.
// - 키보드·터치 대안: '블록 추가' 버튼 → 시작/종료 시각 선택 폼.
// - 시간표는 자기 기록이며 집중 보상과 무관하다(나무 지급 없음). 같은 레이어 겹침은 서버도 거부.
import { useEffect, useRef, useState } from 'react'
import { useToast } from '../../components/Toast.jsx'
import { del, patch, post } from '../../lib/api.js'

const SLOT = 15
const SLOT_PX = 20
const SLOTS = 1440 / SLOT
const THRESHOLD = 6
const LAYER = { plan: '계획', actual: '실제' }

export const fmt = (min) => `${String(Math.floor(min / 60)).padStart(2, '0')}:${String(min % 60).padStart(2, '0')}`
const TIMES = Array.from({ length: SLOTS + 1 }, (_, i) => i * SLOT)

function overlaps(blocks, cand, ignoreId) {
  return blocks.some(
    (b) => b.id !== ignoreId && b.layer === cand.layer && b.startMin < cand.endMin && b.endMin > cand.startMin,
  )
}

export default function Timetable({ date, blocks, readOnly, onChange }) {
  const toast = useToast()
  const scroller = useRef(null)
  const timeline = useRef(null)
  const drag = useRef(null)
  const [range, setRange] = useState(null) // 새 블록 드래그 중 {layer, a, b}
  const [preview, setPreview] = useState(null) // 이동/조절 미리보기 {id, startMin, endMin}
  const [form, setForm] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    // 초기 스크롤은 09:00 근처
    if (scroller.current) scroller.current.scrollTop = (9 * 60 / SLOT) * SLOT_PX - 10
  }, [date])

  const slotAt = (clientY) => {
    const rect = timeline.current.getBoundingClientRect()
    return Math.max(0, Math.min(SLOTS - 1, Math.floor((clientY - rect.top) / SLOT_PX)))
  }
  const layerAt = (clientX) => {
    const rect = timeline.current.getBoundingClientRect()
    return clientX - rect.left < 48 + (rect.width - 48) / 2 ? 'plan' : 'actual'
  }

  // ── 새 블록: 빈 곳 드래그 ───────────────────────────────────────
  function onTimelineDown(e) {
    if (readOnly || e.button > 0 || e.target.closest('.time-block')) return
    const slot = slotAt(e.clientY)
    drag.current = { kind: 'create', y0: e.clientY, a: slot, layer: layerAt(e.clientX), pointerId: e.pointerId }
    timeline.current.setPointerCapture(e.pointerId)
    setRange({ layer: drag.current.layer, a: slot, b: slot })
  }

  // ── 기존 블록: 이동 / 끝 조절 ──────────────────────────────────
  function onBlockDown(e, block, kind) {
    if (readOnly || e.button > 0) return
    e.stopPropagation()
    drag.current = { kind, y0: e.clientY, block, pointerId: e.pointerId, moved: false }
    timeline.current.setPointerCapture(e.pointerId)
  }

  function onMove(e) {
    const d = drag.current
    if (!d) return
    if (d.kind === 'create') {
      setRange({ layer: d.layer, a: d.a, b: slotAt(e.clientY) })
      return
    }
    const dy = e.clientY - d.y0
    if (Math.abs(dy) < THRESHOLD && !d.moved) return
    d.moved = true
    const delta = Math.round(dy / SLOT_PX) * SLOT
    const b = d.block
    if (d.kind === 'move') {
      const len = b.endMin - b.startMin
      const start = Math.max(0, Math.min(1440 - len, b.startMin + delta))
      d.preview = { id: b.id, startMin: start, endMin: start + len }
    } else {
      const end = Math.max(b.startMin + SLOT, Math.min(1440, b.endMin + delta))
      d.preview = { id: b.id, startMin: b.startMin, endMin: end }
    }
    // 렌더링용 상태와 별도로 ref에도 보관한다(빠른 놓기에서 오래된 상태를 읽지 않도록).
    setPreview(d.preview)
  }

  async function onUp(e) {
    const d = drag.current
    drag.current = null
    if (!d) return
    if (timeline.current?.hasPointerCapture(d.pointerId)) timeline.current.releasePointerCapture(d.pointerId)
    if (d.kind === 'create') {
      const isClick = Math.abs(e.clientY - d.y0) < THRESHOLD
      const end = isClick ? d.a : slotAt(e.clientY)
      const lo = Math.min(d.a, end)
      const hi = Math.max(d.a, end)
      setRange(null)
      setError('')
      setForm({ mode: 'create', layer: d.layer, startMin: lo * SLOT, endMin: (hi + 1) * SLOT, title: '', memo: '' })
      return
    }
    const p = d.preview
    setPreview(null)
    if (!d.moved || !p) {
      setError('')
      setForm({ mode: 'edit', id: d.block.id, ...d.block })
      return
    }
    if (overlaps(blocks, { ...d.block, ...p }, d.block.id)) {
      toast('같은 종류의 다른 블록과 겹쳐요. 원래 자리로 돌아갔어요.')
      return
    }
    try {
      await patch(`/timetable-blocks/${d.block.id}`, { startMin: p.startMin, endMin: p.endMin })
      onChange?.()
    } catch (err) {
      toast(err.message)
      onChange?.()
    }
  }

  function onCancel() {
    // 스크롤 전환 등으로 포인터가 취소되면 미리보기를 버리고 원상 복구
    drag.current = null
    setRange(null)
    setPreview(null)
  }

  async function submit(e) {
    e.preventDefault()
    setError('')
    const f = form
    if (f.endMin <= f.startMin) return setError('종료 시각은 시작 시각보다 늦어야 해요.')
    if (overlaps(blocks, f, f.id)) return setError('같은 종류의 다른 블록과 시간이 겹쳐요.')
    try {
      if (f.mode === 'create') {
        await post('/timetable-blocks', { date, layer: f.layer, startMin: f.startMin, endMin: f.endMin, title: f.title, memo: f.memo })
      } else {
        await patch(`/timetable-blocks/${f.id}`, { layer: f.layer, startMin: f.startMin, endMin: f.endMin, title: f.title, memo: f.memo })
      }
      setForm(null)
      onChange?.()
    } catch (err) {
      setError(err.message)
    }
  }

  async function remove() {
    try {
      await del(`/timetable-blocks/${form.id}`)
      setForm(null)
      onChange?.()
    } catch (err) {
      setError(err.message)
    }
  }

  const shown = blocks.map((b) => (preview?.id === b.id ? { ...b, ...preview } : b))
  const lo = range ? Math.min(range.a, range.b) : -1
  const hi = range ? Math.max(range.a, range.b) : -1

  return (
    <article className="card timetable-card">
      <div className="section-top">
        <h2>시간표</h2>
        {!readOnly && (
          <button
            type="button"
            onClick={() => {
              setError('')
              setForm({ mode: 'create', layer: 'actual', startMin: 540, endMin: 600, title: '', memo: '' })
            }}
          >
            블록 추가
          </button>
        )}
      </div>
      <p className="hint" id={`tt-help-${date}`}>
        {readOnly
          ? '왼쪽은 계획, 오른쪽은 실제 기록이에요.'
          : '왼쪽(계획)·오른쪽(실제) 열의 빈 곳을 위아래로 드래그해 시간을 고르고, 블록을 끌어 옮기거나 아래 손잡이로 길이를 바꿔요. 키보드는 블록 추가 버튼을 쓰세요.'}
      </p>
      <div className="timeline-head" aria-hidden="true">
        <span />
        <span>계획</span>
        <span>실제</span>
      </div>
      <div className="timeline-scroll" ref={scroller}>
        <div
          className="timeline"
          ref={timeline}
          onPointerDown={onTimelineDown}
          onPointerMove={onMove}
          onPointerUp={onUp}
          onPointerCancel={onCancel}
          aria-describedby={`tt-help-${date}`}
        >
          {Array.from({ length: SLOTS }, (_, i) => (
            <div key={i} className={`time-slot${i % 4 === 0 ? ' hour' : ''}${i >= lo && i <= hi ? ` range ${range.layer}` : ''}`}>
              {i % 4 === 0 ? fmt(i * SLOT) : ''}
            </div>
          ))}
          {shown.map((b) => (
            <div
              key={b.id}
              className={`time-block ${b.layer}${preview?.id === b.id ? ' dragging' : ''}`}
              style={{ top: (b.startMin / SLOT) * SLOT_PX, height: ((b.endMin - b.startMin) / SLOT) * SLOT_PX }}
            >
              {readOnly ? (
                <span className="block-body">
                  <strong>{b.title}</strong> {fmt(b.startMin)}–{fmt(b.endMin)}
                </span>
              ) : (
                <>
                  <button
                    type="button"
                    className="block-body"
                    onPointerDown={(e) => onBlockDown(e, b, 'move')}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        setError('')
                        setForm({ mode: 'edit', id: b.id, ...b })
                      }
                    }}
                    aria-label={`${LAYER[b.layer]} ${b.title} ${fmt(b.startMin)}부터 ${fmt(b.endMin)}까지, Enter로 수정`}
                  >
                    <strong>{b.title}</strong> {fmt(b.startMin)}–{fmt(b.endMin)}
                  </button>
                  <span className="block-resize" aria-hidden="true" onPointerDown={(e) => onBlockDown(e, b, 'resize')} />
                </>
              )}
            </div>
          ))}
        </div>
      </div>
      {form && !readOnly && (
        <form className="block-form" onSubmit={submit} aria-label={form.mode === 'create' ? '새 시간표 블록' : '시간표 블록 수정'}>
          <div className="inline">
            <label>
              종류
              <select value={form.layer} onChange={(e) => setForm((f) => ({ ...f, layer: e.target.value }))}>
                <option value="plan">계획</option>
                <option value="actual">실제 기록</option>
              </select>
            </label>
            <label>
              시작
              <select value={form.startMin} onChange={(e) => setForm((f) => ({ ...f, startMin: Number(e.target.value) }))}>
                {TIMES.slice(0, -1).map((t) => (
                  <option key={t} value={t}>
                    {fmt(t)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              종료
              <select value={form.endMin} onChange={(e) => setForm((f) => ({ ...f, endMin: Number(e.target.value) }))}>
                {TIMES.slice(1).map((t) => (
                  <option key={t} value={t}>
                    {fmt(t)}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            공부 제목
            <input required maxLength={80} value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} autoFocus />
          </label>
          <label>
            메모
            <input maxLength={500} value={form.memo} onChange={(e) => setForm((f) => ({ ...f, memo: e.target.value }))} />
          </label>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="inline">
            <button type="submit" className="primary">
              {form.mode === 'create' ? '블록 저장' : '수정 저장'}
            </button>
            <button type="button" onClick={() => setForm(null)}>
              취소
            </button>
            {form.mode === 'edit' && (
              <button type="button" className="danger" onClick={remove}>
                삭제
              </button>
            )}
          </div>
        </form>
      )}
    </article>
  )
}
