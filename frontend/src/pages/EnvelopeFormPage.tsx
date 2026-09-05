import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import { extractFieldErrors, type FieldErrors } from '../api/errors'
import type { Category, CategoryKind } from '../api/types'
import { FieldError } from '../components/FieldError'
import { IconPicker } from '../components/IconPicker'
import { Skeleton } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'

const KIND_OPTIONS: { value: CategoryKind; label: string }[] = [
  { value: 'fixed', label: 'Fixkosten' },
  { value: 'variable', label: 'Variable Kosten' },
  { value: 'income', label: 'Einnahmen' },
  { value: 'debt', label: 'Schuldentilgung' },
  { value: 'savings', label: 'Sparen' },
]

// Muss zu Category.KIND_ICON_DEFAULTS (core/models.py) passen — nur als sinnvoller
// Startwert für neue Umschläge; das Backend würde bei leerem Icon ohnehin dasselbe setzen.
const KIND_ICON_DEFAULTS: Record<CategoryKind, string> = {
  fixed: 'FileText',
  variable: 'ShoppingCart',
  income: 'TrendUp',
  debt: 'CreditCard',
  savings: 'PiggyBank',
}

interface FormState {
  name: string
  kind: CategoryKind
  monthly_budget: string
  keywords: string
  color: string
  icon: string
  target_amount: string
  target_date: string
  is_emergency_fund: boolean
  is_archived: boolean
}

const EMPTY: FormState = {
  name: '',
  kind: 'variable',
  monthly_budget: '0',
  keywords: '',
  color: '#0f172a',
  icon: KIND_ICON_DEFAULTS.variable,
  target_amount: '',
  target_date: '',
  is_emergency_fund: false,
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
        target_amount: c.target_amount ?? '',
        target_date: c.target_date ?? '',
        is_emergency_fund: c.is_emergency_fund,
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
          <div className="field checkbox-field">
            <input
              id="is_emergency_fund"
              type="checkbox"
              checked={form.is_emergency_fund}
              onChange={(e) => setForm({ ...form, is_emergency_fund: e.target.checked })}
              aria-describedby="emergency-fund-help"
            />
            <label htmlFor="is_emergency_fund">Das ist mein Notfallfonds</label>
          </div>
          <p className="helptext" id="emergency-fund-help">
            Bevor der Tilgungsplan-Rechner und der Sweep-Vorschlag Extra-Budget auf Schulden verteilen, füllen sie
            zuerst die Lücke zu diesem Sparziel — bewährtes Prinzip aus der Schuldenberatung, damit die nächste
            unerwartete Rechnung nicht wieder auf der Kreditkarte landet. Braucht ein gesetztes Sparziel oben, und
            es kann immer nur ein Umschlag Notfallfonds sein — ein zuvor markierter wird automatisch abgewählt.
          </p>
          {errors.fields.is_emergency_fund && <FieldError id="emergency-fund-error" message={errors.fields.is_emergency_fund} />}
          <div className="form-row align-end">
            <div className="field">
              <label htmlFor="color">Farbe</label>
              <input id="color" type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
            </div>
            <div className="field field-auto">
              <label>Icon</label>
              <IconPicker value={form.icon} onChange={(icon) => setForm({ ...form, icon })} color={form.color} />
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
