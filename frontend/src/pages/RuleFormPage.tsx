import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import { extractErrorMessage, extractFieldErrors, type FieldErrors } from '../api/errors'
import type { Category, Rule, RuleConditions, RuleMatchType, RulePreviewResult } from '../api/types'
import { FieldError } from '../components/FieldError'
import { Skeleton } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'
import { formatMoney } from '../utils/format'

const MATCH_OPTIONS: { value: RuleMatchType; label: string }[] = [
  { value: 'contains', label: 'enthält' },
  { value: 'startswith', label: 'beginnt mit' },
  { value: 'exact', label: 'ist genau' },
]

function hasCondition(c: RuleConditions): boolean {
  return Boolean(c.description_value || c.counterparty_value || c.amount_min || c.amount_max)
}

export function RuleFormPage() {
  const { id } = useParams<{ id: string }>()
  const isNew = !id
  const navigate = useNavigate()
  const push = useToast()
  const [categories, setCategories] = useState<Category[]>([])
  const [name, setName] = useState('')
  const [conditions, setConditions] = useState<RuleConditions>({
    description_match_type: 'contains',
    description_value: '',
    counterparty_match_type: 'contains',
    counterparty_value: '',
    amount_min: '',
    amount_max: '',
  })
  const [categoryId, setCategoryId] = useState('')
  const [priority, setPriority] = useState('0')
  const [isActive, setIsActive] = useState(true)
  const [loading, setLoading] = useState(!isNew)
  const [errors, setErrors] = useState<FieldErrors>({ fields: {} })
  const [submitting, setSubmitting] = useState(false)
  const [preview, setPreview] = useState<RulePreviewResult | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const generalErrorRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    api.get<Category[]>('/categories/', { params: { active_only: 1 } }).then((res) => {
      setCategories(res.data)
      setCategoryId((current) => current || (res.data[0] ? String(res.data[0].id) : ''))
    })
  }, [])

  useEffect(() => {
    if (isNew) return
    api.get<Rule>(`/import/rules/${id}/`).then((res) => {
      const r = res.data
      setName(r.name)
      setConditions({
        description_match_type: r.description_match_type,
        description_value: r.description_value,
        counterparty_match_type: r.counterparty_match_type,
        counterparty_value: r.counterparty_value,
        amount_min: r.amount_min,
        amount_max: r.amount_max,
      })
      setCategoryId(String(r.category))
      setPriority(String(r.priority))
      setIsActive(r.is_active)
      setLoading(false)
    })
  }, [id, isNew])

  // Live-Vorschau: welche bestehenden Buchungen passen gerade zu den eingegebenen
  // Bedingungen — bevor überhaupt gespeichert oder angewendet wird.
  useEffect(() => {
    if (!hasCondition(conditions)) {
      setPreview(null)
      return
    }
    setPreviewLoading(true)
    const timer = setTimeout(() => {
      api
        .post<RulePreviewResult>('/import/rules/preview/', conditions)
        .then((res) => setPreview(res.data))
        .catch(() => setPreview(null))
        .finally(() => setPreviewLoading(false))
    }, 350)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    conditions.description_match_type,
    conditions.description_value,
    conditions.counterparty_match_type,
    conditions.counterparty_value,
    conditions.amount_min,
    conditions.amount_max,
  ])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors({ fields: {} })
    setSubmitting(true)
    try {
      const payload = {
        name,
        ...conditions,
        category: Number(categoryId),
        priority: Number(priority) || 0,
        is_active: isActive,
      }
      if (isNew) {
        await api.post('/import/rules/', payload)
        push('success', 'Regel angelegt.')
      } else {
        await api.put(`/import/rules/${id}/`, payload)
        push('success', 'Regel aktualisiert.')
      }
      navigate('/rules')
    } catch (err) {
      const fieldErrors = extractFieldErrors(err)
      setErrors(fieldErrors)
      queueMicrotask(() => generalErrorRef.current?.focus())
    } finally {
      setSubmitting(false)
    }
  }

  async function handleApply() {
    if (!preview || preview.count === 0) return
    const categoryName = categories.find((c) => String(c.id) === categoryId)?.name ?? 'diesen Umschlag'
    if (!confirm(`${preview.count} bestehende Buchung(en) wirklich „${categoryName}“ zuordnen?`)) return
    setApplying(true)
    try {
      const res = await api.post<{ updated: number }>('/import/rules/apply/', {
        ...conditions,
        category: Number(categoryId),
      })
      push('success', `${res.data.updated} Buchung(en) aktualisiert.`)
      setPreview(null)
    } catch (err) {
      push('error', extractErrorMessage(err))
    } finally {
      setApplying(false)
    }
  }

  if (loading) {
    return (
      <div className="card" style={{ maxWidth: 560 }} aria-busy="true">
        <Skeleton lines={8} />
      </div>
    )
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>{isNew ? 'Neue Regel' : 'Regel bearbeiten'}</h1>
          <p>Legt fest, welcher Umschlag beim CAMT.053-Import automatisch zugeordnet wird.</p>
        </div>
      </div>
      <div className="card" style={{ maxWidth: 560 }}>
        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="name">Name (optional)</label>
            <input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="z.B. Migros" />
          </div>

          <div className="rule-condition-group">
            <div className="rule-condition-label">Beschreibung</div>
            <div className="form-row">
              <div className="field" style={{ flex: '0 0 160px' }}>
                <select
                  aria-label="Bedingung für Beschreibung"
                  value={conditions.description_match_type}
                  onChange={(e) => setConditions({ ...conditions, description_match_type: e.target.value as RuleMatchType })}
                >
                  {MATCH_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <input
                  aria-label="Text für Beschreibung"
                  value={conditions.description_value}
                  onChange={(e) => setConditions({ ...conditions, description_value: e.target.value })}
                  placeholder="leer = keine Bedingung"
                />
              </div>
            </div>
          </div>

          <div className="rule-condition-group">
            <div className="rule-condition-label">Gegenpartei</div>
            <div className="form-row">
              <div className="field" style={{ flex: '0 0 160px' }}>
                <select
                  aria-label="Bedingung für Gegenpartei"
                  value={conditions.counterparty_match_type}
                  onChange={(e) => setConditions({ ...conditions, counterparty_match_type: e.target.value as RuleMatchType })}
                >
                  {MATCH_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <input
                  aria-label="Text für Gegenpartei"
                  value={conditions.counterparty_value}
                  onChange={(e) => setConditions({ ...conditions, counterparty_value: e.target.value })}
                  placeholder="leer = keine Bedingung"
                />
              </div>
            </div>
          </div>

          <div className="rule-condition-group">
            <div className="rule-condition-label">Betrag (negativ = Ausgabe)</div>
            <div className="form-row">
              <div className="field">
                <input
                  aria-label="Betrag mindestens"
                  value={conditions.amount_min ?? ''}
                  onChange={(e) => setConditions({ ...conditions, amount_min: e.target.value })}
                  placeholder="mindestens, z.B. -50"
                />
              </div>
              <div className="field">
                <input
                  aria-label="Betrag höchstens"
                  value={conditions.amount_max ?? ''}
                  onChange={(e) => setConditions({ ...conditions, amount_max: e.target.value })}
                  placeholder="höchstens, z.B. -10"
                />
              </div>
            </div>
          </div>

          <div className="form-row">
            <div className="field">
              <label htmlFor="category">Umschlag</label>
              <select id="category" value={categoryId} onChange={(e) => setCategoryId(e.target.value)} required>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="priority">Priorität</label>
              <input id="priority" type="number" value={priority} onChange={(e) => setPriority(e.target.value)} aria-describedby="priority-help" />
            </div>
          </div>
          <p className="helptext" id="priority-help">
            Höhere Zahl wird zuerst geprüft — bei mehreren zutreffenden Regeln gewinnt die mit der höchsten Priorität.
          </p>
          <div className="field checkbox-field">
            <input id="is_active" type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            <label htmlFor="is_active">Aktiv</label>
          </div>
          {errors.fields.value && <FieldError id="value-error" message={errors.fields.value} />}
          {errors.general && (
            <p className="error-text" role="alert" tabIndex={-1} ref={generalErrorRef}>
              {errors.general}
            </p>
          )}
          <div className="form-actions">
            <button type="submit" className="btn" disabled={submitting}>
              Speichern
            </button>
            <Link to="/rules" className="btn secondary">
              Abbrechen
            </Link>
          </div>
        </form>
      </div>

      <div className="section-title">Passende bestehende Buchungen</div>
      <div className="card">
        {!hasCondition(conditions) ? (
          <p className="helptext">Noch keine Bedingung eingegeben.</p>
        ) : previewLoading && !preview ? (
          <Skeleton lines={3} />
        ) : preview && preview.count === 0 ? (
          <p className="helptext">Keine bestehenden Buchungen passen zu diesen Bedingungen.</p>
        ) : preview ? (
          <>
            <p className="helptext">
              {preview.count} passende Buchung(en){preview.count > preview.preview_limit ? ` — zeige die ersten ${preview.preview_limit}` : ''}.
            </p>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Datum</th>
                    <th>Beschreibung</th>
                    <th>Gegenpartei</th>
                    <th>Umschlag aktuell</th>
                    <th style={{ textAlign: 'right' }}>Betrag</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.transactions.map((t) => (
                    <tr key={t.id}>
                      <td>{t.date}</td>
                      <td>{t.description || '—'}</td>
                      <td className="cell-truncate" title={t.counterparty || undefined}>
                        {t.counterparty || '—'}
                      </td>
                      <td>{t.category_name ?? '—'}</td>
                      <td className={`amount-cell ${t.is_expense ? 'negative' : 'positive'}`}>{formatMoney(t.amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="form-actions">
              <button type="button" className="btn" disabled={applying} onClick={() => void handleApply()}>
                {applying ? 'Wende an …' : `Jetzt auf ${preview.count} Buchung(en) anwenden`}
              </button>
            </div>
          </>
        ) : null}
      </div>
    </>
  )
}
