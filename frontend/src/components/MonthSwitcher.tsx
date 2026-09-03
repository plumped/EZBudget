interface Props {
  label: string
  onPrev: () => void
  onNext: () => void
}

export function MonthSwitcher({ label, onPrev, onNext }: Props) {
  return (
    <div className="month-switcher">
      <button type="button" onClick={onPrev} aria-label="Vorheriger Monat">
        ←
      </button>
      <span>{label}</span>
      <button type="button" onClick={onNext} aria-label="Nächster Monat">
        →
      </button>
    </div>
  )
}
