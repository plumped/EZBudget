import { CheckCircle, Info, WarningCircle } from '@phosphor-icons/react'
import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react'

type ToastType = 'success' | 'error' | 'info'

interface ToastItem {
  id: number
  type: ToastType
  text: string
}

type PushToast = (type: ToastType, text: string) => void

const ToastContext = createContext<PushToast | undefined>(undefined)

const ICONS: Record<ToastType, typeof CheckCircle> = {
  success: CheckCircle,
  error: WarningCircle,
  info: Info,
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const counter = useRef(0)

  const push = useCallback<PushToast>((type, text) => {
    const id = ++counter.current
    setToasts((current) => [...current, { id, type, text }])
    setTimeout(() => {
      setToasts((current) => current.filter((t) => t.id !== id))
    }, 4500)
  }, [])

  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toast-list">
        {toasts.map((t) => {
          const ToastIcon = ICONS[t.type]
          return (
            <div key={t.id} className={`toast ${t.type}`} role={t.type === 'error' ? 'alert' : 'status'} aria-live="polite">
              <ToastIcon size={18} weight="fill" className="icon" aria-hidden="true" />
              <span>{t.text}</span>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): PushToast {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return ctx
}
