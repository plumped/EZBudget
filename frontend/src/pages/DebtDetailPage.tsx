import { ArrowLeft, Trash } from '@phosphor-icons/react'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import api from '../api/client'
import { extractErrorMessage, extractFieldErrors, type FieldErrors } from '../api/errors'
import type { Debt, DebtPayment } from '../api/types'
import { FieldError } from '../components/FieldError'
import { ProgressBar } from '../components/ProgressBar'
import { Skeleton } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'
import { formatMoney } from '../utils/format'

export function DebtDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const push = useToast()
  const [debt, setDebt] = useState<Debt | null>(null)
  const [payments, setPayments] = useState<DebtPayment[]>([])
  const [loading, setLoading] = useState(true)
  const [amount, setAmount] = useState('')
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [note, setNote] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({ fields: {} })
  const [submitting, setSubmitting] = useState(false)
  const generalErrorRef = useRef<HTMLParagraphElement>(null)

  function load() {
    setLoading(true)
    return Promise.all([api.get<Debt>(`/debts/${id}/`), api.get<DebtPayment[]>(`/debts/${id}/payments/`)])
      .then(([debtRes, paymentsRes]) => {
        setDebt(debtRes.data)
        setPayments(paymentsRes.data)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors({ fields: {} })
    setSubmitting(true)
    try {
      await api.post(`/debts/${id}/payments/`, { date, amount, note })
      push('success', 'Zahlung erfasst.')
      setAmount('')
      setNote('')
      void load()
    } catch (err) {
      const fieldErrors = extractFieldErrors(err)
      setErrors(fieldErrors)
      queueMicrotask(() => generalErrorRef.current?.focus())
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete() {
    if (!debt || !confirm(`Schuld „${debt.name}“ wirklich löschen?`)) return
    try {
      await api.delete(`/debts/${id}/`)
      push('success', 'Schuld gelöscht.')
      navigate('/debts')
    } catch (err) {
      push('error', extractErrorMessage(err))
    }
  }

  if (loading || !debt) {
    return (
      <div className="card" aria-busy="true">
        <Skeleton lines={4} />
      </div>
    )
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>{debt.name}</h1>
          <p>{debt.creditor || 'Kein Gläubiger hinterlegt'}</p>
        </div>
        <div className="page-header-actions">
          <Link to="/debts" className="btn secondary">
            <ArrowLeft size={16} weight="bold" aria-hidden="true" />
            Zurück
          </Link>
          <button type="button" className="btn danger" onClick={() => void handleDelete()}>
            <Trash size={16} weight="bold" aria-hidden="true" />
            Löschen
          </button>
        </div>
      </div>

      <div className="card">
        <ProgressBar percent={debt.progress_percent} />
        <div className="stat-grid">
          <div>
            <div className="hero-label">Restschuld</div>
            <div className="stat-value negative num">{formatMoney(debt.current_balance)}</div>
          </div>
          <div>
            <div className="hero-label">Bereits getilgt</div>
            <div className="stat-value positive num">{formatMoney(debt.paid_so_far)}</div>
          </div>
          <div>
            <div className="hero-label">Zinssatz</div>
            <div className="stat-value num">{debt.interest_rate}%</div>
          </div>
          <div>
            <div className="hero-label">Mindestrate</div>
            <div className="stat-value num">{formatMoney(debt.minimum_payment)}</div>
          </div>
        </div>
      </div>

      <div className="section-title">Zahlung erfassen</div>
      <div className="card" style={{ maxWidth: 480 }}>
        <form onSubmit={handleSubmit} noValidate>
          <div className="form-row">
            <div className="field">
              <label htmlFor="amount">Betrag</label>
              <input
                id="amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
                placeholder="100"
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
            <input id="note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="z.B. Monatsrate" />
          </div>
          {errors.general && (
            <p className="error-text" role="alert" tabIndex={-1} ref={generalErrorRef}>
              {errors.general}
            </p>
          )}
          <button type="submit" className="btn" disabled={submitting}>
            Zahlung erfassen
          </button>
        </form>
      </div>

      <div className="section-title">Zahlungshistorie</div>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Datum</th>
              <th>Notiz</th>
              <th style={{ textAlign: 'right' }}>Betrag</th>
            </tr>
          </thead>
          <tbody>
            {payments.length === 0 ? (
              <tr>
                <td colSpan={3} style={{ padding: 0 }}>
                  <div className="empty-state">Noch keine Zahlungen erfasst.</div>
                </td>
              </tr>
            ) : (
              payments.map((p) => (
                <tr key={p.id}>
                  <td>{p.date}</td>
                  <td>{p.note || '—'}</td>
                  <td className="amount-cell positive">{formatMoney(p.amount)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}
