import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'
import { extractFieldErrors, type FieldErrors } from '../api/errors'
import type { Account, Category } from '../api/types'
import { FieldError } from '../components/FieldError'
import { useToast } from '../context/ToastContext'

export function TransactionFormPage() {
  const navigate = useNavigate()
  const push = useToast()
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [direction, setDirection] = useState<'expense' | 'income'>('expense')
  const [amount, setAmount] = useState('')
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [description, setDescription] = useState('')
  const [counterparty, setCounterparty] = useState('')
  const [accountId, setAccountId] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({ fields: {} })
  const [submitting, setSubmitting] = useState(false)
  const generalErrorRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    api.get<Account[]>('/accounts/', { params: { active_only: 1 } }).then((res) => {
      setAccounts(res.data)
      if (res.data.length > 0) setAccountId(String(res.data[0].id))
    })
    api.get<Category[]>('/categories/', { params: { active_only: 1 } }).then((res) => setCategories(res.data))
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors({ fields: {} })
    setSubmitting(true)
    try {
      const numeric = Math.abs(parseFloat(amount.replace(',', '.')) || 0)
      const signedAmount = direction === 'expense' ? -numeric : numeric
      await api.post('/transactions/', {
        account: Number(accountId),
        category: categoryId ? Number(categoryId) : null,
        date,
        amount: signedAmount.toFixed(2),
        description,
        counterparty,
      })
      push('success', 'Buchung gespeichert.')
      navigate('/transactions')
    } catch (err) {
      const fieldErrors = extractFieldErrors(err)
      setErrors(fieldErrors)
      queueMicrotask(() => generalErrorRef.current?.focus())
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Buchung erfassen</h1>
          <p>Manuelle Buchung hinzufügen (z.B. Bargeld).</p>
        </div>
      </div>
      <div className="card" style={{ maxWidth: 480 }}>
        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label id="direction-label">Richtung</label>
            <div className="toggle-group" style={{ width: '100%' }} role="group" aria-labelledby="direction-label">
              <button
                type="button"
                className={direction === 'expense' ? 'active' : ''}
                style={{ flex: 1 }}
                aria-pressed={direction === 'expense'}
                onClick={() => setDirection('expense')}
              >
                Ausgabe
              </button>
              <button
                type="button"
                className={direction === 'income' ? 'active' : ''}
                style={{ flex: 1 }}
                aria-pressed={direction === 'income'}
                onClick={() => setDirection('income')}
              >
                Einnahme
              </button>
            </div>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="amount">Betrag (CHF)</label>
              <input
                id="amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
                placeholder="42.50"
                aria-invalid={errors.fields.amount ? 'true' : undefined}
                aria-describedby={errors.fields.amount ? 'amount-error' : undefined}
              />
              {errors.fields.amount && <FieldError id="amount-error" message={errors.fields.amount} />}
            </div>
            <div className="field">
              <label htmlFor="date">Datum</label>
              <input
                id="date"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
                aria-invalid={errors.fields.date ? 'true' : undefined}
                aria-describedby={errors.fields.date ? 'date-error' : undefined}
              />
              {errors.fields.date && <FieldError id="date-error" message={errors.fields.date} />}
            </div>
          </div>
          <div className="field">
            <label htmlFor="description">Beschreibung</label>
            <input
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="z.B. Migros Einkauf"
            />
          </div>
          <div className="field">
            <label htmlFor="counterparty">Gegenpartei (optional)</label>
            <input
              id="counterparty"
              value={counterparty}
              onChange={(e) => setCounterparty(e.target.value)}
              placeholder="z.B. Migros AG"
            />
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="account">Konto</label>
              <select id="account" value={accountId} onChange={(e) => setAccountId(e.target.value)} required>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="category">Umschlag</label>
              <select id="category" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
                <option value="">— ohne —</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {errors.general && (
            <p className="error-text" role="alert" tabIndex={-1} ref={generalErrorRef}>
              {errors.general}
            </p>
          )}
          <div className="form-actions">
            <button type="submit" className="btn" disabled={submitting}>
              Buchung speichern
            </button>
            <Link to="/transactions" className="btn secondary">
              Abbrechen
            </Link>
          </div>
        </form>
      </div>
    </>
  )
}
