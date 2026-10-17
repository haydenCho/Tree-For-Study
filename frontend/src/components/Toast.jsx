// 시각 전용 토스트(소리·진동·OS 알림 없음). 화면 오른쪽 아래에 잠시 표시한다.
import { createContext, useCallback, useContext, useRef, useState } from 'react'

const ToastContext = createContext(() => {})

export function ToastProvider({ children }) {
  const [message, setMessage] = useState(null)
  const timer = useRef(null)
  const show = useCallback((text, ms = 3600) => {
    setMessage(text)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setMessage(null), ms)
  }, [])
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div className="toast" role="status" aria-live="polite" hidden={!message}>
        {message}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}
