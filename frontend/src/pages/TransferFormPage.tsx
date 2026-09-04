import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'
import { extractFieldErrors, type FieldErrors } from '../api/errors'
import type { Account } from '../api/types'
import { FieldError } from '../components/FieldError'
import { useToast } from '../context/ToastContext'

export function TransferFormPage() {
  const navigate = useNavigate()
  const push = useToast()
  const [accounts, setAccounts] = useState<Account[]>([])
  const [fromAccount, setFromAccount] = useState('')
  const [toAccount, setToAccount] = useState('')
  const [amount, setAmount] = useState('')
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [note, setNote] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({ fields: {} })
  const [submitting, setSubmitting] = useState(false)
  const generalErrorRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    api.get<Account[]>('/accounts/', { params: { active_only: 1 } }).then((res) => {
      setAccounts(res.data)
      if (res.data.length > 0) {
        setFromAccount(String(res.data[0].id))
        if (res.data.length > 1) setToAccount(String(res.data[1].id))
      }
    })
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors({ fields: {} })
    setSubmitting(true)
    try {
      await api.post('/transfers/', {
        from_account: Number(fromAccount),
        to_account: Number(toAccount),
        amount,
        date,
        note,
      })
      push('success', 'Transfer erfasst.')
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
          <h1>Transfer erfassen</h1>
          <p>Geld zwischen zwei eigenen Konten verschieben — zählt nicht als Einnahme/Ausgabe.</p>
        </div>
      </div>
      <div className="card card-form">
        <form onSubmit={handleSubmit} noValidate>
          <div className="form-row">
            <div className="field">
              <label htmlFor="from_account">Von Konto</label>
              <select id="from_account" value={fromAccount} onChange={(e) => setFromAccount(e.target.value)} required>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="to_account">Zu Konto</label>
              <select id="to_account" value={toAccount} onChange={(e) => setToAccount(e.target.value)} required>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="amount">Betrag</label>
              <input
                id="amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
                placeholder="200"
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
            <label htmlFor="note">Notiz (optional)</label>
            <input id="note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="z.B. Sparbetrag Monatsende" />
          </div>
          {errors.general && (
            <p className="error-text" role="alert" tabIndex={-1} ref={generalErrorRef}>
              {errors.general}
            </p>
          )}
          <div className="form-actions">
            <button type="submit" className="btn" disabled={submitting}>
              Transfer erfassen
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
