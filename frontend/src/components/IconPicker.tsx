import { useRef } from 'react'
import { ICON_CATALOG, ICON_COMPONENTS } from './iconCatalog'

interface Props {
  value: string
  onChange: (icon: string) => void
  color?: string
}

export function IconPicker({ value, onChange, color }: Props) {
  const detailsRef = useRef<HTMLDetailsElement>(null)
  const SelectedIcon = ICON_COMPONENTS[value]

  function select(icon: string) {
    onChange(icon)
    if (detailsRef.current) detailsRef.current.open = false
  }

  return (
    <details className="icon-picker" ref={detailsRef}>
      <summary>
        <span className="row-icon" style={color ? { background: `${color}1a`, color } : undefined}>
          {SelectedIcon ? <SelectedIcon size={18} weight="regular" aria-hidden="true" /> : null}
        </span>
        Icon ändern
      </summary>
      <div className="icon-picker-panel">
        {ICON_CATALOG.map((group) => (
          <div className="icon-picker-group" key={group.label}>
            <div className="icon-picker-group-label">{group.label}</div>
            <div className="icon-picker-grid" role="group" aria-label={group.label}>
              {group.icons.map((name) => {
                const OptionIcon = ICON_COMPONENTS[name]
                return (
                  <button
                    key={name}
                    type="button"
                    className={name === value ? 'active' : ''}
                    aria-pressed={name === value}
                    aria-label={name}
                    onClick={() => select(name)}
                  >
                    <OptionIcon size={20} weight="regular" aria-hidden="true" />
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </details>
  )
}
