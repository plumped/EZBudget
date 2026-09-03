import { Tray } from '@phosphor-icons/react'
import type { ReactNode } from 'react'

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Tray size={28} weight="light" aria-hidden="true" />
      </div>
      {children}
    </div>
  )
}
