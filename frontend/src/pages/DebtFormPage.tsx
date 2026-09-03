import { useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'
import { extractFieldErrors, type FieldErrors } from '../api/errors'
import { FieldError } from '../components/FieldError'
import { useToast } from '../context/ToastContext'

export function DebtFormPage() {
  const navigate = useNavigate()
  const push = useToast()
  const [name, setName] = useState('')
  const [creditor, setCreditor] = useState('')
  const [principal, setPrincipal] = useState('')
  const [currentBalance, setCurrentBalance] = useState('')
  const [interestRate, setInterestRate] = useState('')
  const [minimumPayment, setMinimumPayment] = useState('')
  const [errors, setErrors] = useState<FieldErrors>({ fields: {} })
  const [submitting, setSubmitting] = useState(false)
  const generalErrorRef = useRef<HTMLParagraphElement>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setErrors({ fields: {} })
    setSubmitting(true)
    try {
      await api.post('/debts/', {
        name,
        creditor,
        principal,
        current_balance: currentBalance,
        interest_rate: interestRate,
        minimum_payment: minimumPayment,
      })
      push('success', 'Schuld hinzugefügt.')
      navigate('/debts')
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
          <h1>Schuld erfassen</h1>
          <p>Kredit, Kreditkarte, Privatdarlehen o.ä.</p>
        </div>
      </div>
      <div className="card" style={{ maxWidth: 480 }}>
        <form onSubmit={handleSubmit} noValidate>
          <div className="field">
            <label htmlFor="name">Bezeichnung</label>
            <input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="z.B. Kreditkarte Viseca"
              aria-invalid={errors.fields.name ? 'true' : undefined}
              aria-describedby={errors.fields.name ? 'name-error' : undefined}
            />
            {errors.fields.name && <FieldError id="name-error" message={errors.fields.name} />}
          </div>
          <div className="field">
            <label htmlFor="creditor">Gläubiger (optional)</label>
            <input id="creditor" value={creditor} onChange={(e) => setCreditor(e.target.value)} placeholder="z.B. Viseca Card Services" />
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="principal">Ursprungsbetrag</label>
              <input
                id="principal"
                value={principal}
                onChange={(e) => setPrincipal(e.target.value)}
                required
                placeholder="5000"
                aria-invalid={errors.fields.principal ? 'true' : undefined}
                aria-describedby={errors.fields.principal ? 'principal-error' : undefined}
              />
              {errors.fields.principal && <FieldError id="principal-error" message={errors.fields.principal} />}
            </div>
            <div className="field">
              <label htmlFor="current_balance">Aktuelle Restschuld</label>
              <input
                id="current_balance"
                value={currentBalance}
                onChange={(e) => setCurrentBalance(e.target.value)}
                required
                placeholder="3200"
                aria-invalid={errors.fields.current_balance ? 'true' : undefined}
                aria-describedby={errors.fields.current_balance ? 'current-balance-error' : undefined}
              />
              {errors.fields.current_balance && (
                <FieldError id="current-balance-error" message={errors.fields.current_balance} />
              )}
            </div>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="interest_rate">Zinssatz % p.a.</label>
              <input
                id="interest_rate"
                value={interestRate}
                onChange={(e) => setInterestRate(e.target.value)}
                required
                placeholder="9.9"
                aria-invalid={errors.fields.interest_rate ? 'true' : undefined}
                aria-describedby={errors.fields.interest_rate ? 'interest-rate-error' : undefined}
              />
              {errors.fields.interest_rate && <FieldError id="interest-rate-error" message={errors.fields.interest_rate} />}
            </div>
            <div className="field">
              <label htmlFor="minimum_payment">Mindestrate / Monat</label>
              <input
                id="minimum_payment"
                value={minimumPayment}
                onChange={(e) => setMinimumPayment(e.target.value)}
                required
                placeholder="150"
                aria-invalid={errors.fields.minimum_payment ? 'true' : undefined}
                aria-describedby={errors.fields.minimum_payment ? 'minimum-payment-error' : undefined}
              />
              {errors.fields.minimum_payment && (
                <FieldError id="minimum-payment-error" message={errors.fields.minimum_payment} />
              )}
            </div>
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
            <Link to="/debts" className="btn secondary">
              Abbrechen
            </Link>
          </div>
        </form>
      </div>
    </>
  )
}
