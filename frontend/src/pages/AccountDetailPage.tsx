import { ArrowLeft } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api from '../api/client'
import type { Account, Transaction } from '../api/types'
import { Skeleton } from '../components/Skeleton'
import { formatMoney, moneyClass } from '../utils/format'

export function AccountDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [account, setAccount] = useState<Account | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      api.get<Account>(`/accounts/${id}/`),
      api.get<Transaction[]>('/transactions/', { params: { account: id } }),
    ])
      .then(([accRes, txnRes]) => {
        if (cancelled) return
        setAccount(accRes.data)
        setTransactions(txnRes.data.slice(0, 50))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id])

  if (loading || !account) {
    return (
      <div className="card" aria-busy="true">
        <Skeleton lines={3} />
      </div>
    )
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>{account.name}</h1>
          <p>{account.iban || 'Keine IBAN hinterlegt'}</p>
        </div>
        <Link to="/accounts" className="btn secondary">
          <ArrowLeft size={16} weight="bold" aria-hidden="true" />
          Zurück
        </Link>
      </div>

      <div className="card">
        <div className="hero-label">Aktueller Saldo</div>
        <div className={`hero-figure num ${moneyClass(account.balance)}`}>CHF {formatMoney(account.balance)}</div>
      </div>

      <div className="section-title">Letzte Buchungen</div>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Datum</th>
              <th>Beschreibung</th>
              <th>Umschlag</th>
              <th style={{ textAlign: 'right' }}>Betrag</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ padding: 0 }}>
                  <div className="empty-state">Keine Buchungen auf diesem Konto.</div>
                </td>
              </tr>
            ) : (
              transactions.map((t) => (
                <tr key={t.id}>
                  <td>{t.date}</td>
                  <td>{t.description || '—'}</td>
                  <td>{t.category_name ?? '—'}</td>
                  <td className={`amount-cell ${t.is_expense ? 'negative' : 'positive'}`}>{formatMoney(t.amount)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  )
}
