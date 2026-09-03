import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import { extractFieldErrors, type FieldErrors } from '../api/errors'
import type { Account, Category, RecurringTransaction } from '../api/types'
import { FieldError } from '../components/FieldError'
import { Skeleton } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'

interface FormState {
  account: string
  category: string
  description: string
  counterparty: string
  amount: string
  day_of_month: string
  is_active: boolean
}

const EMPTY: FormState = {
  account: '',
  category: '',
  description: '',
  counterparty: '',
  amount: '',
  day_of_month: '1',
  is_active: true,
}

export function RecurringFormPage() {
  const { id } = useParams<{ id: string }>()
  const isNew = !id
  const navigate = useNavigate()
  const push = useToast()
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [form, setForm] = useState<FormState>(EMPTY)
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
        day_of_month: String(rt.day_of_month),
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
        day_of_month: Number(form.day_of_month),
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
      <div className="card" style={{ maxWidth: 480 }} aria-busy="true">
        <Skeleton lines={6} />
      </div>
    )
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>{isNew ? 'Neuer Dauerauftrag' : 'Dauerauftrag bearbeiten'}</h1>
          <p>Wird jeden Monat am angegebenen Tag automatisch als Buchung erzeugt.</p>
        </div>
      </div>
      <div className="card" style={{ maxWidth: 480 }}>
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
          </div>
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
