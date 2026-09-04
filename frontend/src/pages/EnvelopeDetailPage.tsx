import { ArrowLeft } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api from '../api/client'
import type { Category, Transaction } from '../api/types'
import { KindBadge } from '../components/KindBadge'
import { KindIcon } from '../components/KindIcon'
import { ProgressBar } from '../components/ProgressBar'
import { Skeleton } from '../components/Skeleton'
import { useMonthParam } from '../utils/useMonthParam'
import { formatDate, formatMoney, formatMonthLabel, moneyClass } from '../utils/format'

export function EnvelopeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { year, month, label } = useMonthParam()
  const [category, setCategory] = useState<Category | null>(null)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      api.get<Category>(`/categories/${id}/`, { params: { year, month } }),
      api.get<Transaction[]>('/transactions/', { params: { category: id, year, month } }),
    ])
      .then(([catRes, txnRes]) => {
        if (cancelled) return
        setCategory(catRes.data)
        setTransactions(txnRes.data)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [id, year, month])

  if (loading || !category) {
    return (
      <div className="card" aria-busy="true">
        <Skeleton lines={4} />
      </div>
    )
  }

  return (
    <>
      <div className="page-header">
        <div className="detail-header">
          <KindIcon kind={category.kind} color={category.color} icon={category.icon} />
          <div>
            <h1>{category.name}</h1>
            <p>
              <KindBadge kind={category.kind} /> · {label}
            </p>
          </div>
        </div>
        <Link to="/envelopes" className="btn secondary">
          <ArrowLeft size={16} weight="bold" aria-hidden="true" />
          Zurück
        </Link>
      </div>

      <div className="card">
        <ProgressBar percent={category.progress} over={category.progress >= 100} />
        <div className="stat-grid">
          <div>
            <div className="hero-label">Budget</div>
            <div className="stat-value num">{formatMoney(category.monthly_budget)}</div>
          </div>
          <div>
            <div className="hero-label">Ausgegeben</div>
            <div className="stat-value negative num">{formatMoney(category.spent)}</div>
          </div>
          <div>
            <div className="hero-label">Verfügbar (nur dieser Monat)</div>
            <div className={`stat-value ${moneyClass(category.available)} num`}>{formatMoney(category.available)}</div>
          </div>
          <div>
            <div className="hero-label">Verfügbar mit Übertrag</div>
            <div className={`stat-value ${moneyClass(category.rollover)} num`}>{formatMoney(category.rollover)}</div>
          </div>
        </div>
      </div>

      {category.target_amount && (
        <div className="card">
          <div className="hero-label">
            Sparziel{category.target_date && ` — bis ${formatDate(category.target_date)}`}
          </div>
          <ProgressBar percent={category.target_progress_percent ?? 0} />
          <p className="helptext">
            {formatMoney(category.rollover)} / {formatMoney(category.target_amount)} CHF gespart (
            {category.target_progress_percent ?? 0}%)
          </p>
        </div>
      )}

      {category.budget_history.length > 1 && (
        <>
          <div className="section-title">Budget-Verlauf</div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Ab</th>
                  <th className="text-right">Monatsbudget</th>
                </tr>
              </thead>
              <tbody>
                {category.budget_history.map((h) => (
                  <tr key={`${h.year}-${h.month}`}>
                    <td>{formatMonthLabel(`${h.year}-${String(h.month).padStart(2, '0')}-01`, h.month)}</td>
                    <td className="amount-cell">{formatMoney(h.monthly_budget)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <div className="section-title">Buchungen in diesem Umschlag</div>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Datum</th>
              <th>Beschreibung</th>
              <th>Konto</th>
              <th className="text-right">Betrag</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr>
                <td colSpan={4} className="table-empty-cell">
                  <div className="empty-state">Keine Buchungen in diesem Monat.</div>
                </td>
              </tr>
            ) : (
              transactions.map((t) => (
                <tr key={t.id}>
                  <td>{t.date}</td>
                  <td>{t.description || '—'}</td>
                  <td>{t.account_name}</td>
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
