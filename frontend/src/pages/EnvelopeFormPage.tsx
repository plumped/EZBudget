import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import { extractFieldErrors, type FieldErrors } from '../api/errors'
import type { Category, CategoryKind } from '../api/types'
import { FieldError } from '../components/FieldError'
import { Skeleton } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'

const KIND_OPTIONS: { value: CategoryKind; label: string }[] = [
  { value: 'fixed', label: 'Fixkosten' },
  { value: 'variable', label: 'Variable Kosten' },
  { value: 'income', label: 'Einnahmen' },
  { value: 'debt', label: 'Schuldentilgung' },
  { value: 'savings', label: 'Sparen' },
]

interface FormState {
  name: string
  kind: CategoryKind
  monthly_budget: string
  keywords: string
  color: string
  icon: string
  is_archived: boolean
}

const EMPTY: FormState = {
  name: '',
  kind: 'variable',
  monthly_budget: '0',
  keywords: '',
  color: '#0f172a',
  icon: '💰',
  is_archived: false,
}

export function EnvelopeFormPage() {
  const { id } = useParams<{ id: string }>()
  const isNew = !id
  const navigate = useNavigate()
  const push = useToast()
  const [form, setForm] = useState<FormState>(EMPTY)
  const [loading, setLoading] = useState(!isNew)
  const [errors, setErrors] = useState<FieldErrors>({ fields: {} })
  const [submitting, setSubmitting] = useState(false)
  const generalErrorRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    if (isNew) return
    api.get<Category>(`/categories/${id}/`).then((res) => {
      const c = res.data
      setForm({
        name: c.name,
        kind: c.kind,
        monthly_budget: c.monthly_budget,
        keywords: c.keywords,
        color: c.color,
        icon: c.icon,
        is_archived: c.is_archived,
      })
      setLoading(false)
    })
  }, [id, isNew])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors({ fields: {} })
    setSubmitting(true)
    try {
      if (isNew) {
        await api.post('/categories/', form)
        push('success', `Umschlag „${form.name}“ angelegt.`)
      } else {
        await api.put(`/categories/${id}/`, form)
        push('success', `Umschlag „${form.name}“ aktualisiert.`)
      }
      navigate('/envelopes')
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
          <h1>{isNew ? 'Neuer Umschlag' : 'Umschlag bearbeiten'}</h1>
          <p>Budget-Topf für Fixkosten, variable Kosten, Sparen oder Schuldentilgung.</p>
        </div>
      </div>
      <div className="card" style={{ maxWidth: 480 }}>
        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="name">Name</label>
            <input
              id="name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              aria-invalid={errors.fields.name ? 'true' : undefined}
              aria-describedby={errors.fields.name ? 'name-error' : undefined}
            />
            {errors.fields.name && <FieldError id="name-error" message={errors.fields.name} />}
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="kind">Art</label>
              <select id="kind" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value as CategoryKind })}>
                {KIND_OPTIONS.map((k) => (
                  <option key={k.value} value={k.value}>
                    {k.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="budget">Monatsbudget</label>
              <input
                id="budget"
                value={form.monthly_budget}
                onChange={(e) => setForm({ ...form, monthly_budget: e.target.value })}
                required
                aria-invalid={errors.fields.monthly_budget ? 'true' : undefined}
                aria-describedby={errors.fields.monthly_budget ? 'budget-error' : undefined}
              />
              {errors.fields.monthly_budget && <FieldError id="budget-error" message={errors.fields.monthly_budget} />}
            </div>
          </div>
          <div className="field">
            <label htmlFor="keywords">Stichworte für Auto-Zuordnung</label>
            <input
              id="keywords"
              value={form.keywords}
              onChange={(e) => setForm({ ...form, keywords: e.target.value })}
              placeholder="migros, coop, denner"
              aria-describedby="keywords-help"
            />
            <p className="helptext" id="keywords-help">
              Komma-getrennt, für den CAMT.053-Import.
            </p>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="color">Farbe</label>
              <input id="color" type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
            </div>
            <div className="field">
              <label htmlFor="icon">Icon (Emoji)</label>
              <input id="icon" value={form.icon} onChange={(e) => setForm({ ...form, icon: e.target.value })} />
            </div>
          </div>
          <div className="field checkbox-field">
            <input
              id="archived"
              type="checkbox"
              checked={form.is_archived}
              onChange={(e) => setForm({ ...form, is_archived: e.target.checked })}
            />
            <label htmlFor="archived">Archiviert</label>
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
            <Link to="/envelopes" className="btn secondary">
              Abbrechen
            </Link>
          </div>
        </form>
      </div>
    </>
  )
}
