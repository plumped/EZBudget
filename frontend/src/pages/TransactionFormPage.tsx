import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'
import { extractErrorMessage } from '../api/errors'
import type { Account, Category } from '../api/types'
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
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    api.get<Account[]>('/accounts/', { params: { active_only: 1 } }).then((res) => {
      setAccounts(res.data)
      if (res.data.length > 0) setAccountId(String(res.data[0].id))
    })
    api.get<Category[]>('/categories/', { params: { active_only: 1 } }).then((res) => setCategories(res.data))
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
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
      setError(extractErrorMessage(err))
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
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Richtung</label>
            <div className="toggle-group" style={{ width: '100%' }}>
              <button
                type="button"
                className={direction === 'expense' ? 'active' : ''}
                style={{ flex: 1 }}
                onClick={() => setDirection('expense')}
              >
                Ausgabe
              </button>
              <button
                type="button"
                className={direction === 'income' ? 'active' : ''}
                style={{ flex: 1 }}
                onClick={() => setDirection('income')}
              >
                Einnahme
              </button>
            </div>
          </div>
          <div className="form-row">
            <div className="field">
              <label htmlFor="amount">Betrag (CHF)</label>
              <input id="amount" value={amount} onChange={(e) => setAmount(e.target.value)} required placeholder="42.50" />
            </div>
            <div className="field">
              <label htmlFor="date">Datum</label>
              <input id="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
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
                    {c.icon} {c.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {error && <p className="error-text">{error}</p>}
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
