import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'
import { extractErrorMessage } from '../api/errors'
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
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
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
      setError(extractErrorMessage(err))
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
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="name">Bezeichnung</label>
            <input id="name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="z.B. Kreditkarte Viseca" />
          </div>
          <div className="field">
            <label htmlFor="creditor">Gläubiger (optional)</label>
            <input id="creditor" value={creditor} onChange={(e) => setCreditor(e.target.value)} placeholder="z.B. Viseca Card Services" />
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="principal">Ursprungsbetrag</label>
              <input id="principal" value={principal} onChange={(e) => setPrincipal(e.target.value)} required placeholder="5000" />
            </div>
            <div className="field">
              <label htmlFor="current_balance">Aktuelle Restschuld</label>
              <input
                id="current_balance"
                value={currentBalance}
                onChange={(e) => setCurrentBalance(e.target.value)}
                required
                placeholder="3200"
              />
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
              />
            </div>
            <div className="field">
              <label htmlFor="minimum_payment">Mindestrate / Monat</label>
              <input
                id="minimum_payment"
                value={minimumPayment}
                onChange={(e) => setMinimumPayment(e.target.value)}
                required
                placeholder="150"
              />
            </div>
          </div>
          {error && <p className="error-text">{error}</p>}
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
