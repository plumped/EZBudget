import { PencilSimple, Plus, Trash } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { extractErrorMessage } from '../api/errors'
import type { Category, Transaction } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { MonthSwitcher } from '../components/MonthSwitcher'
import { Skeleton } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'
import { useMonthParam } from '../utils/useMonthParam'
import { formatMoney } from '../utils/format'

export function TransactionsPage() {
  const { year, month, label, prevYear, prevMonth, nextYear, nextMonth, setMonth } = useMonthParam()
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [categoryFilter, setCategoryFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const push = useToast()

  const load = useCallback(() => {
    setLoading(true)
    return api
      .get<Transaction[]>('/transactions/', { params: { year, month, category: categoryFilter || undefined } })
      .then((res) => setTransactions(res.data))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, month, categoryFilter])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    api.get<Category[]>('/categories/', { params: { active_only: 1 } }).then((res) => setCategories(res.data))
  }, [])

  async function handleDelete(id: number) {
    try {
      await api.delete(`/transactions/${id}/`)
      push('success', 'Buchung gelöscht.')
      void load()
    } catch (err) {
      push('error', extractErrorMessage(err))
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Buchungen</h1>
          <p>Alle Buchungen im gewählten Monat.</p>
        </div>
        <div className="page-header-actions">
          <MonthSwitcher label={label} onPrev={() => setMonth(prevYear, prevMonth)} onNext={() => setMonth(nextYear, nextMonth)} />
          <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="filter-select">
            <option value="">Alle Umschläge</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          <Link to="/transactions/add" className="btn secondary">
            <Plus size={16} weight="bold" aria-hidden="true" />
            Buchung erfassen
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="table-wrap" aria-busy="true">
          <div className="content-pad">
            <Skeleton lines={6} />
          </div>
        </div>
      ) : transactions.length === 0 ? (
        <EmptyState>
          Noch keine Buchungen. <Link to="/import">CAMT.053 importieren</Link> oder{' '}
          <Link to="/transactions/add">manuell erfassen</Link>.
        </EmptyState>
      ) : (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Datum</th>
                <th>Beschreibung</th>
                <th>Gegenpartei</th>
                <th>Konto</th>
                <th>Umschlag</th>
                <th className="text-right">Betrag</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {transactions.map((t) => (
                <tr key={t.id}>
                  <td>{t.date}</td>
                  <td>{t.description || '—'}</td>
                  <td className="cell-truncate" title={t.counterparty || undefined}>
                    {t.counterparty || '—'}
                  </td>
                  <td>{t.account_name}</td>
                  <td>{t.category_name ?? '—'}</td>
                  <td className={`amount-cell ${t.is_expense ? 'negative' : 'positive'}`}>{formatMoney(t.amount)}</td>
                  <td className="nowrap">
                    <Link to={`/transactions/${t.id}/edit`} className="link-action">
                      <PencilSimple size={14} weight="bold" aria-hidden="true" />
                      bearbeiten
                    </Link>
                    <button
                      type="button"
                      className="link-action danger"
                      onClick={() => void handleDelete(t.id)}
                      aria-label={`Buchung „${t.description || t.date}“ löschen`}
                    >
                      <Trash size={14} weight="bold" aria-hidden="true" />
                      löschen
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}
