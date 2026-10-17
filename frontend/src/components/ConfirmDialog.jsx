// 확인 다이얼로그(네이티브 <dialog>). Escape/취소 버튼으로 닫힌다.
import { useEffect, useRef } from 'react'

export default function ConfirmDialog({ open, title, children, confirmLabel, cancelLabel = '취소', danger, busy, error, onConfirm, onCancel }) {
  const ref = useRef(null)
  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) d.showModal()
    if (!open && d.open) d.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault()
        if (!busy) onCancel?.()
      }}
    >
      <h2>{title}</h2>
      <div className="dialog-body">{children}</div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="inline dialog-actions">
        <button type="button" onClick={onCancel} disabled={busy} autoFocus>
          {cancelLabel}
        </button>
        <button type="button" className={danger ? 'danger' : 'primary'} onClick={onConfirm} disabled={busy}>
          {busy ? '처리 중…' : confirmLabel}
        </button>
      </div>
    </dialog>
  )
}
