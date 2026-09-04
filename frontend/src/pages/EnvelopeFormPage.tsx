import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import { extractFieldErrors, type FieldErrors } from '../api/errors'
import type { Category, CategoryKind } from '../api/types'
import { FieldError } from '../components/FieldError'
import { KindIcon } from '../components/KindIcon'
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
  target_amount: string
  target_date: string
  is_archived: boolean
}

const EMPTY: FormState = {
  name: '',
  kind: 'variable',
  monthly_budget: '0',
  keywords: '',
  color: '#0f172a',
  target_amount: '',
  target_date: '',
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
        target_amount: c.target_amount ?? '',
        target_date: c.target_date ?? '',
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
      const payload = {
        ...form,
        target_amount: form.target_amount.trim() || null,
        target_date: form.target_date || null,
      }
      if (isNew) {
        await api.post('/categories/', payload)
        push('success', `Umschlag „${form.name}“ angelegt.`)
      } else {
        await api.put(`/categories/${id}/`, payload)
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
      <div className="card card-form" aria-busy="true">
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
      <div className="card card-form">
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
              <label htmlFor="target_amount">Sparziel (optional)</label>
              <input
                id="target_amount"
                value={form.target_amount}
                onChange={(e) => setForm({ ...form, target_amount: e.target.value })}
                placeholder="z.B. 5000"
                aria-describedby="target-help"
              />
            </div>
            <div className="field">
              <label htmlFor="target_date">Zieldatum (optional)</label>
              <input
                id="target_date"
                type="date"
                value={form.target_date}
                onChange={(e) => setForm({ ...form, target_date: e.target.value })}
              />
            </div>
          </div>
          <p className="helptext" id="target-help">
            Zielbetrag, bis zu dem dieser Umschlag inkl. Übertrag angespart werden soll — z.B. für Sparziele.
          </p>
          <div className="form-row align-end">
            <div className="field">
              <label htmlFor="color">Farbe</label>
              <input id="color" type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
            </div>
            <div className="field field-auto">
              <label id="preview-label">Vorschau</label>
              <div aria-labelledby="preview-label" className="color-preview">
                <KindIcon kind={form.kind} color={form.color} />
              </div>
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
