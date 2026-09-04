import { Desktop, Moon, Sun, type Icon } from '@phosphor-icons/react'
import { useEffect, useState, type FormEvent } from 'react'
import { extractErrorMessage } from '../api/errors'
import { useSettings } from '../context/SettingsContext'
import { useTheme, type Theme } from '../context/ThemeContext'
import { useToast } from '../context/ToastContext'

const THEME_OPTIONS: { value: Theme; label: string; icon: Icon }[] = [
  { value: 'system', label: 'System', icon: Desktop },
  { value: 'light', label: 'Hell', icon: Sun },
  { value: 'dark', label: 'Dunkel', icon: Moon },
]

export function SettingsPage() {
  const { monthStartDay, loading, updateMonthStartDay } = useSettings()
  const { theme, setTheme } = useTheme()
  const push = useToast()
  const [value, setValue] = useState(String(monthStartDay))
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    setValue(String(monthStartDay))
  }, [monthStartDay])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const parsed = Number(value)
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > 28) {
      push('error', 'Bitte einen Tag zwischen 1 und 28 angeben.')
      return
    }
    setSubmitting(true)
    try {
      await updateMonthStartDay(parsed)
      push('success', 'Einstellung gespeichert.')
    } catch (err) {
      push('error', extractErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Einstellungen</h1>
          <p>Globale Einstellungen fürs Haushaltsbudget.</p>
        </div>
      </div>
      <div className="card card-form">
        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="month_start_day">Budget-Monat beginnt am</label>
            <input
              id="month_start_day"
              type="number"
              min={1}
              max={28}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              disabled={loading}
              required
              aria-describedby="month-start-help"
            />
            <p className="helptext" id="month-start-help">
              Tag im Monat, an dem Umschläge/Buchungen/Dashboard neu zu rechnen beginnen — z.B. 25, wenn dort
              Lohn und Daueraufträge ausgeführt werden. 1 = normaler Kalendermonat.
            </p>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn" disabled={submitting || loading}>
              Speichern
            </button>
          </div>
        </form>
      </div>

      <div className="card card-form">
        <div className="field">
          <label id="theme-label">Darstellung</label>
          <div className="toggle-group toggle-group-full" role="group" aria-labelledby="theme-label">
            {THEME_OPTIONS.map((opt) => {
              const IconComponent = opt.icon
              return (
                <button
                  key={opt.value}
                  type="button"
                  className={theme === opt.value ? 'active' : ''}
                  aria-pressed={theme === opt.value}
                  onClick={() => setTheme(opt.value)}
                >
                  <IconComponent size={14} weight="bold" aria-hidden="true" />
                  {opt.label}
                </button>
              )
            })}
          </div>
          <p className="helptext">„System" folgt automatisch der Geräteeinstellung, „Hell"/„Dunkel" überschreiben sie fest.</p>
        </div>
      </div>
    </>
  )
}
