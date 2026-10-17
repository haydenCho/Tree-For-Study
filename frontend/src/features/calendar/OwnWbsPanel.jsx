// 본인 WBS: 목록(일정 막대) + 명확한 폼으로 생성·수정·삭제·공개 전환.
// 상위 과제/하위 작업 최대 2단계, 하위 작업은 상위 기간 안, 진행률 0~100(서버도 검증).
// WBS 막대 드래그 편집은 하지 않는다(필수 아님). 작업 추가 폼은 접기/펼치기로 필요할 때만 연다.
import { useCallback, useEffect, useState } from 'react'
import ConfirmDialog from '../../components/ConfirmDialog.jsx'
import { useToast } from '../../components/Toast.jsx'
import { del, get, patch, post } from '../../lib/api.js'
import WbsList from './WbsList.jsx'

const EMPTY = { title: '', startDate: '2026-10-20', endDate: '2026-11-19', parentId: '', status: 'planned', progress: 0, memo: '', isPublic: false }

function WbsForm({ initial, parents, onSubmit, onCancel, submitLabel, lockParent }) {
  const [f, setF] = useState(initial)
  const [error, setError] = useState('')
  const set = (k, number) => (e) =>
    setF((x) => ({ ...x, [k]: e.target.type === 'checkbox' ? e.target.checked : number ? Number(e.target.value) : e.target.value }))
  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault()
        setError('')
        if (f.endDate < f.startDate) return setError('종료일은 시작일과 같거나 늦어야 해요.')
        try {
          await onSubmit({ ...f, parentId: f.parentId || null })
        } catch (err) {
          setError(err.message)
        }
      }}
    >
      <label>
        제목
        <input required maxLength={120} value={f.title} onChange={set('title')} />
      </label>
      {!lockParent && (
        <label>
          상위 과제
          <select value={f.parentId || ''} onChange={set('parentId')}>
            <option value="">(없음 · 상위 과제로 만들기)</option>
            {parents.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
        </label>
      )}
      <div className="inline">
        <label>
          시작일
          <input type="date" required value={f.startDate} onChange={set('startDate')} />
        </label>
        <label>
          종료일
          <input type="date" required value={f.endDate} onChange={set('endDate')} />
        </label>
      </div>
      <div className="inline">
        <label>
          상태
          <select value={f.status} onChange={set('status')}>
            <option value="planned">예정</option>
            <option value="in_progress">진행</option>
            <option value="done">완료</option>
          </select>
        </label>
        <label>
          진행률 {f.progress}%
          <input type="range" min={0} max={100} step={5} value={f.progress} onChange={set('progress', true)} />
        </label>
      </div>
      <label>
        메모
        <textarea rows={2} maxLength={2000} value={f.memo} onChange={set('memo')} />
      </label>
      <label className="check">
        <input type="checkbox" checked={f.isPublic} onChange={set('isPublic')} />
        스터디 멤버에게 이 항목 공개
      </label>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="inline">
        <button type="submit" className="primary">
          {submitLabel}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel}>
            취소
          </button>
        )}
      </div>
    </form>
  )
}

export function OwnWbsPanel({ month }) {
  const toast = useToast()
  const [items, setItems] = useState([])
  const [selected, setSelected] = useState(null)
  const [adding, setAdding] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const load = useCallback(async () => {
    try {
      setItems((await get('/wbs')).items)
    } catch (err) {
      toast(err.message)
    }
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  const parents = items.filter((t) => !t.parentId)

  return (
    <>
      <div className="section-top">
        <h2>나의 WBS</h2>
        <small>막대를 누르면 편집해요</small>
      </div>
      <WbsList
        items={items}
        month={month}
        selectedId={selected?.id}
        onSelect={(t) => {
          setSelected(t)
          setAdding(false)
        }}
        emptyText="아직 WBS가 없어요. 아래에서 상위 과제부터 추가해 보세요."
      />
      {selected && (
        <div className="wbs-editor-panel">
          <h3>편집: {selected.title}</h3>
          <WbsForm
            key={selected.id}
            initial={{ ...selected, parentId: selected.parentId || '' }}
            parents={parents}
            lockParent
            submitLabel="저장"
            onCancel={() => setSelected(null)}
            onSubmit={async (f) => {
              await patch(`/wbs/${selected.id}`, {
                title: f.title,
                startDate: f.startDate,
                endDate: f.endDate,
                status: f.status,
                progress: f.progress,
                memo: f.memo,
                isPublic: f.isPublic,
              })
              toast('WBS를 저장했어요.')
              setSelected(null)
              load()
            }}
          />
          <button type="button" className="danger" onClick={() => setConfirmDelete(true)}>
            삭제
          </button>
        </div>
      )}
      <details className="wbs-editor" open={adding} onToggle={(e) => setAdding(e.currentTarget.open)}>
        <summary>+ 작업 추가</summary>
        {adding && (
          <WbsForm
            initial={EMPTY}
            parents={parents}
            submitLabel="추가"
            onSubmit={async (f) => {
              await post('/wbs', f)
              toast('WBS를 추가했어요.')
              setAdding(false)
              load()
            }}
          />
        )}
      </details>
      <ConfirmDialog
        open={confirmDelete}
        title="이 WBS 항목을 삭제할까요?"
        confirmLabel="삭제"
        danger
        onCancel={() => setConfirmDelete(false)}
        onConfirm={async () => {
          setConfirmDelete(false)
          try {
            await del(`/wbs/${selected.id}`)
            setSelected(null)
            load()
          } catch (err) {
            toast(err.message)
          }
        }}
      >
        <p>상위 과제를 지우면 하위 작업도 함께 삭제돼요.</p>
      </ConfirmDialog>
    </>
  )
}
