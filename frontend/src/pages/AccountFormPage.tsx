import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import { extractFieldErrors, type FieldErrors } from '../api/errors'
import type { Account, AccountType } from '../api/types'
import { FieldError } from '../components/FieldError'
import { Skeleton } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'

const TYPE_OPTIONS: { value: AccountType; label: string }[] = [
  { value: 'checking', label: 'Girokonto' },
  { value: 'savings', label: 'Sparkonto' },
  { value: 'cash', label: 'Bargeld' },
  { value: 'credit', label: 'Kreditkarte' },
]

interface FormState {
  name: string
  account_type: AccountType
  iban: string
  starting_balance: string
  is_archived: boolean
}

const EMPTY: FormState = {
  name: '',
  account_type: 'checking',
  iban: '',
  starting_balance: '0',
  is_archived: false,
}

export function AccountFormPage() {
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
    api.get<Account>(`/accounts/${id}/`).then((res) => {
      const a = res.data
      setForm({
        name: a.name,
        account_type: a.account_type,
        iban: a.iban,
        starting_balance: a.starting_balance,
        is_archived: a.is_archived,
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
        await api.post('/accounts/', form)
        push('success', `Konto „${form.name}“ angelegt.`)
      } else {
        await api.put(`/accounts/${id}/`, form)
        push('success', `Konto „${form.name}“ aktualisiert.`)
      }
      navigate('/accounts')
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
        <Skeleton lines={5} />
      </div>
    )
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>{isNew ? 'Neues Konto' : 'Konto bearbeiten'}</h1>
          <p>Girokonto, Sparkonto, Bargeld oder Kreditkarte.</p>
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
              <label htmlFor="type">Art</label>
              <select
                id="type"
                value={form.account_type}
                onChange={(e) => setForm({ ...form, account_type: e.target.value as AccountType })}
              >
                {TYPE_OPTIONS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="balance">Startsaldo</label>
              <input
                id="balance"
                value={form.starting_balance}
                onChange={(e) => setForm({ ...form, starting_balance: e.target.value })}
                required
                aria-invalid={errors.fields.starting_balance ? 'true' : undefined}
                aria-describedby={errors.fields.starting_balance ? 'balance-error' : undefined}
              />
              {errors.fields.starting_balance && <FieldError id="balance-error" message={errors.fields.starting_balance} />}
            </div>
          </div>
          <div className="field">
            <label htmlFor="iban">IBAN (optional)</label>
            <input
              id="iban"
              value={form.iban}
              onChange={(e) => setForm({ ...form, iban: e.target.value })}
              aria-invalid={errors.fields.iban ? 'true' : undefined}
              aria-describedby={errors.fields.iban ? 'iban-error' : undefined}
            />
            {errors.fields.iban && <FieldError id="iban-error" message={errors.fields.iban} />}
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
            <Link to="/accounts" className="btn secondary">
              Abbrechen
            </Link>
          </div>
        </form>
      </div>
    </>
  )
}
