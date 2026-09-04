import { useEffect, useState, type FormEvent } from 'react'
import { extractErrorMessage } from '../api/errors'
import { useSettings } from '../context/SettingsContext'
import { useToast } from '../context/ToastContext'

export function SettingsPage() {
  const { monthStartDay, loading, updateMonthStartDay } = useSettings()
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
    </>
  )
}
