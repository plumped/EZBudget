import { useRef } from 'react'

const ICON_GROUPS: { label: string; icons: string[] }[] = [
  { label: 'Finanzen', icons: ['💰', '💳', '💵', '🏦', '📈', '💸', '🐷', '🧾'] },
  { label: 'Essen & Haushalt', icons: ['🛒', '🍎', '🍽️', '☕', '🧺', '🧹', '🛋️'] },
  { label: 'Wohnen', icons: ['🏠', '💡', '🔥', '🚿', '📶', '🔧'] },
  { label: 'Verkehr', icons: ['🚗', '⛽', '🚌', '🚲', '✈️', '🅿️'] },
  { label: 'Gesundheit', icons: ['💊', '🏥', '🦷', '🏋️', '🧘'] },
  { label: 'Freizeit & Familie', icons: ['🎮', '🎬', '📚', '🎉', '👶', '🐾', '🎁'] },
  { label: 'Sonstiges', icons: ['📄', '🛍️', '👕', '✂️', '🔖', '⭐'] },
]

interface Props {
  value: string
  onChange: (icon: string) => void
  color?: string
}

export function IconPicker({ value, onChange, color }: Props) {
  const detailsRef = useRef<HTMLDetailsElement>(null)

  function select(icon: string) {
    onChange(icon)
    if (detailsRef.current) detailsRef.current.open = false
  }

  return (
    <details className="icon-picker" ref={detailsRef}>
      <summary>
        <span className="row-icon" style={color ? { background: `${color}1a`, color } : undefined}>
          <span className="emoji-glyph" aria-hidden="true">
            {value || '❓'}
          </span>
        </span>
        Icon ändern
      </summary>
      <div className="icon-picker-panel">
        {ICON_GROUPS.map((group) => (
          <div className="icon-picker-group" key={group.label}>
            <div className="icon-picker-group-label">{group.label}</div>
            <div className="icon-picker-grid" role="group" aria-label={group.label}>
              {group.icons.map((icon) => (
                <button
                  key={icon}
                  type="button"
                  className={icon === value ? 'active' : ''}
                  aria-pressed={icon === value}
                  aria-label={icon}
                  onClick={() => select(icon)}
                >
                  {icon}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </details>
  )
}
