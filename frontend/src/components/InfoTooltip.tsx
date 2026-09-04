import { Info } from '@phosphor-icons/react'
import { useId } from 'react'

export function InfoTooltip({ text, label = 'Mehr Informationen' }: { text: string; label?: string }) {
  const id = useId()
  return (
    <span className="tooltip">
      <button type="button" className="tooltip-trigger" aria-describedby={id} aria-label={label}>
        <Info size={14} weight="bold" />
      </button>
      <span className="tooltip-bubble" id={id} role="tooltip">
        {text}
      </span>
    </span>
  )
}
