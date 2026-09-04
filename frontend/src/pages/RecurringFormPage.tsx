import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import { extractFieldErrors, type FieldErrors } from '../api/errors'
import type { Account, Category, RecurringFrequency, RecurringTransaction } from '../api/types'
import { FieldError } from '../components/FieldError'
import { Skeleton } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'

const FREQUENCY_OPTIONS: { value: RecurringFrequency; label: string }[] = [
  { value: 'weekly', label: 'Wöchentlich' },
  { value: 'biweekly', label: 'Alle 2 Wochen' },
  { value: 'monthly', label: 'Monatlich' },
  { value: 'yearly', label: 'Jährlich' },
]

const WEEKDAY_OPTIONS = [
  { value: '0', label: 'Montag' },
  { value: '1', label: 'Dienstag' },
  { value: '2', label: 'Mittwoch' },
  { value: '3', label: 'Donnerstag' },
  { value: '4', label: 'Freitag' },
  { value: '5', label: 'Samstag' },
  { value: '6', label: 'Sonntag' },
]

const MONTH_OPTIONS = [
  { value: '1', label: 'Januar' },
  { value: '2', label: 'Februar' },
  { value: '3', label: 'März' },
  { value: '4', label: 'April' },
  { value: '5', label: 'Mai' },
  { value: '6', label: 'Juni' },
  { value: '7', label: 'Juli' },
  { value: '8', label: 'August' },
  { value: '9', label: 'September' },
  { value: '10', label: 'Oktober' },
  { value: '11', label: 'November' },
  { value: '12', label: 'Dezember' },
]

interface FormState {
  account: string
  category: string
  description: string
  counterparty: string
  amount: string
  frequency: RecurringFrequency
  day_of_month: string
  month_of_year: string
  weekday: string
  start_date: string
  is_active: boolean
}

const EMPTY: FormState = {
  account: '',
  category: '',
  description: '',
  counterparty: '',
  amount: '',
  frequency: 'monthly',
  day_of_month: '1',
  month_of_year: '1',
  weekday: '0',
  start_date: '',
  is_active: true,
}

export function RecurringFormPage() {
  const { id } = useParams<{ id: string }>()
  const isNew = !id
  const navigate = useNavigate()
  const push = useToast()
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [form, setForm] = useState<FormState>(() => ({ ...EMPTY, start_date: new Date().toISOString().slice(0, 10) }))
  const [loading, setLoading] = useState(!isNew)
  const [errors, setErrors] = useState<FieldErrors>({ fields: {} })
  const [submitting, setSubmitting] = useState(false)
  const generalErrorRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    api.get<Account[]>('/accounts/', { params: { active_only: 1 } }).then((res) => {
      setAccounts(res.data)
      setForm((f) => (f.account ? f : { ...f, account: res.data[0] ? String(res.data[0].id) : '' }))
    })
    api.get<Category[]>('/categories/', { params: { active_only: 1 } }).then((res) => setCategories(res.data))
  }, [])

  useEffect(() => {
    if (isNew) return
    api.get<RecurringTransaction>(`/recurring/${id}/`).then((res) => {
      const rt = res.data
      setForm({
        account: String(rt.account),
        category: rt.category ? String(rt.category) : '',
        description: rt.description,
        counterparty: rt.counterparty,
        amount: rt.amount,
        frequency: rt.frequency,
        day_of_month: String(rt.day_of_month),
        month_of_year: String(rt.month_of_year),
        weekday: String(rt.weekday),
        start_date: rt.start_date,
        is_active: rt.is_active,
      })
      setLoading(false)
    })
  }, [id, isNew])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors({ fields: {} })
    setSubmitting(true)
    try {
      const payload = {
        account: Number(form.account),
        category: form.category ? Number(form.category) : null,
        description: form.description,
        counterparty: form.counterparty,
        amount: form.amount,
        frequency: form.frequency,
        day_of_month: Number(form.day_of_month),
        month_of_year: Number(form.month_of_year),
        weekday: Number(form.weekday),
        start_date: form.start_date,
        is_active: form.is_active,
      }
      if (isNew) {
        await api.post('/recurring/', payload)
        push('success', `Dauerauftrag „${form.description}“ angelegt.`)
      } else {
        await api.put(`/recurring/${id}/`, payload)
        push('success', `Dauerauftrag „${form.description}“ aktualisiert.`)
      }
      navigate('/recurring')
    } catch (err) {
      const fieldErrors = extractFieldErrors(err)
      setErrors(fieldErrors)
      queueMicrotask(() => generalErrorRef.current?.focus())
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="card card-form" aria-busy="true">
        <Skeleton lines={6} />
      </div>
    )
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>{isNew ? 'Neuer Dauerauftrag' : 'Dauerauftrag bearbeiten'}</h1>
          <p>Wird automatisch in der gewählten Frequenz als Buchung erzeugt.</p>
        </div>
      </div>
      <div className="card card-form">
        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="description">Beschreibung</label>
            <input
              id="description"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              required
              aria-invalid={errors.fields.description ? 'true' : undefined}
              aria-describedby={errors.fields.description ? 'description-error' : undefined}
            />
            {errors.fields.description && <FieldError id="description-error" message={errors.fields.description} />}
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="amount">Betrag (negativ = Ausgabe)</label>
              <input
                id="amount"
                value={form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                required
                aria-invalid={errors.fields.amount ? 'true' : undefined}
                aria-describedby={errors.fields.amount ? 'amount-error' : undefined}
              />
              {errors.fields.amount && <FieldError id="amount-error" message={errors.fields.amount} />}
            </div>
            <div className="field">
              <label htmlFor="frequency">Frequenz</label>
              <select
                id="frequency"
                value={form.frequency}
                onChange={(e) => setForm({ ...form, frequency: e.target.value as RecurringFrequency })}
              >
                {FREQUENCY_OPTIONS.map((f) => (
                  <option key={f.value} value={f.value}>
                    {f.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="form-row">
            {(form.frequency === 'monthly' || form.frequency === 'yearly') && (
              <div className="field">
                <label htmlFor="day">Tag im Monat</label>
                <input
                  id="day"
                  type="number"
                  min={1}
                  max={28}
                  value={form.day_of_month}
                  onChange={(e) => setForm({ ...form, day_of_month: e.target.value })}
                  required
                  aria-invalid={errors.fields.day_of_month ? 'true' : undefined}
                  aria-describedby={errors.fields.day_of_month ? 'day-error' : undefined}
                />
                {errors.fields.day_of_month && <FieldError id="day-error" message={errors.fields.day_of_month} />}
              </div>
            )}
            {form.frequency === 'yearly' && (
              <div className="field">
                <label htmlFor="month_of_year">Monat</label>
                <select id="month_of_year" value={form.month_of_year} onChange={(e) => setForm({ ...form, month_of_year: e.target.value })}>
                  {MONTH_OPTIONS.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {(form.frequency === 'weekly' || form.frequency === 'biweekly') && (
              <div className="field">
                <label htmlFor="weekday">Wochentag</label>
                <select id="weekday" value={form.weekday} onChange={(e) => setForm({ ...form, weekday: e.target.value })}>
                  {WEEKDAY_OPTIONS.map((w) => (
                    <option key={w.value} value={w.value}>
                      {w.label}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {form.frequency === 'biweekly' && (
              <div className="field">
                <label htmlFor="start_date">Ankerdatum</label>
                <input
                  id="start_date"
                  type="date"
                  value={form.start_date}
                  onChange={(e) => setForm({ ...form, start_date: e.target.value })}
                  required
                  aria-describedby="start-date-help"
                />
              </div>
            )}
          </div>
          {form.frequency === 'biweekly' && (
            <p className="helptext" id="start-date-help">
              Ab diesem Datum wird jede 2. Woche am gewählten Wochentag gebucht.
            </p>
          )}
          <div className="field">
            <label htmlFor="counterparty">Gegenpartei (optional)</label>
            <input id="counterparty" value={form.counterparty} onChange={(e) => setForm({ ...form, counterparty: e.target.value })} />
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="account">Konto</label>
              <select id="account" value={form.account} onChange={(e) => setForm({ ...form, account: e.target.value })} required>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="category">Umschlag</label>
              <select id="category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                <option value="">— ohne —</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="field checkbox-field">
            <input
              id="active"
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            <label htmlFor="active">Aktiv</label>
          </div>
          {errors.general && (
            <p className="error-text" role="alert" tabIndex={-1} ref={generalErrorRef}>
              {errors.general}
            </p>
          )}
          <div className="form-actions">
            <button type="submit" className="btn" disabled={submitting}>
              Speichern
            </button>
            <Link to="/recurring" className="btn secondary">
              Abbrechen
            </Link>
          </div>
        </form>
      </div>
    </>
  )
}
