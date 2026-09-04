import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import { extractFieldErrors, type FieldErrors } from '../api/errors'
import type { Category, Rule, RuleField, RuleMatchType } from '../api/types'
import { FieldError } from '../components/FieldError'
import { Skeleton } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'

const FIELD_OPTIONS: { value: RuleField; label: string }[] = [
  { value: 'either', label: 'Beschreibung oder Gegenpartei' },
  { value: 'description', label: 'Beschreibung' },
  { value: 'counterparty', label: 'Gegenpartei' },
]

const MATCH_OPTIONS: { value: RuleMatchType; label: string }[] = [
  { value: 'contains', label: 'enthält' },
  { value: 'startswith', label: 'beginnt mit' },
  { value: 'exact', label: 'ist genau' },
]

export function RuleFormPage() {
  const { id } = useParams<{ id: string }>()
  const isNew = !id
  const navigate = useNavigate()
  const push = useToast()
  const [categories, setCategories] = useState<Category[]>([])
  const [name, setName] = useState('')
  const [field, setField] = useState<RuleField>('either')
  const [matchType, setMatchType] = useState<RuleMatchType>('contains')
  const [value, setValue] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [priority, setPriority] = useState('0')
  const [isActive, setIsActive] = useState(true)
  const [loading, setLoading] = useState(!isNew)
  const [errors, setErrors] = useState<FieldErrors>({ fields: {} })
  const [submitting, setSubmitting] = useState(false)
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
      setField(r.field)
      setMatchType(r.match_type)
      setValue(r.value)
      setCategoryId(String(r.category))
      setPriority(String(r.priority))
      setIsActive(r.is_active)
      setLoading(false)
    })
  }, [id, isNew])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors({ fields: {} })
    setSubmitting(true)
    try {
      const payload = {
        name,
        field,
        match_type: matchType,
        value,
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
          <h1>{isNew ? 'Neue Regel' : 'Regel bearbeiten'}</h1>
          <p>Legt fest, welcher Umschlag beim CAMT.053-Import automatisch zugeordnet wird.</p>
        </div>
      </div>
      <div className="card" style={{ maxWidth: 480 }}>
        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="name">Name (optional)</label>
            <input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="z.B. Migros" />
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="field">Feld</label>
              <select id="field" value={field} onChange={(e) => setField(e.target.value as RuleField)}>
                {FIELD_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="match_type">Bedingung</label>
              <select id="match_type" value={matchType} onChange={(e) => setMatchType(e.target.value as RuleMatchType)}>
                {MATCH_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="field">
            <label htmlFor="value">Text</label>
            <input
              id="value"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              required
              placeholder="z.B. Migros"
              aria-invalid={errors.fields.value ? 'true' : undefined}
              aria-describedby={errors.fields.value ? 'value-error' : undefined}
            />
            {errors.fields.value && <FieldError id="value-error" message={errors.fields.value} />}
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
              <input
                id="priority"
                type="number"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                aria-describedby="priority-help"
              />
            </div>
          </div>
          <p className="helptext" id="priority-help">
            Höhere Zahl wird zuerst geprüft — bei mehreren zutreffenden Regeln gewinnt die mit der höchsten Priorität.
          </p>
          <div className="field checkbox-field">
            <input id="is_active" type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
            <label htmlFor="is_active">Aktiv</label>
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
            <Link to="/rules" className="btn secondary">
              Abbrechen
            </Link>
          </div>
        </form>
      </div>
    </>
  )
}
