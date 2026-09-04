import { ArrowsLeftRight, PencilSimple, Plus, Trash } from '@phosphor-icons/react'
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
  const [searchInput, setSearchInput] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [loading, setLoading] = useState(true)
  const push = useToast()

  useEffect(() => {
    const timer = setTimeout(() => setSearchTerm(searchInput), 350)
    return () => clearTimeout(timer)
  }, [searchInput])

  const hasDateRange = Boolean(dateFrom || dateTo)

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (hasDateRange) {
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
    } else {
      params.year = String(year)
      params.month = String(month)
    }
    if (categoryFilter) params.category = categoryFilter
    if (searchTerm.trim()) params.search = searchTerm.trim()
    return api
      .get<Transaction[]>('/transactions/', { params })
      .then((res) => setTransactions(res.data))
      .finally(() => setLoading(false))
  }, [year, month, categoryFilter, searchTerm, dateFrom, dateTo, hasDateRange])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    api.get<Category[]>('/categories/', { params: { active_only: 1 } }).then((res) => setCategories(res.data))
  }, [])

  function resetDateRange() {
    setDateFrom('')
    setDateTo('')
  }

  async function handleDelete(t: Transaction) {
    if (t.is_transfer && !confirm('Diese Buchung ist Teil eines Transfers — beide verknüpften Buchungen werden gelöscht. Fortfahren?')) {
      return
    }
    try {
      await api.delete(`/transactions/${t.id}/`)
      push('success', t.is_transfer ? 'Transfer gelöscht.' : 'Buchung gelöscht.')
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
          <Link to="/transactions/transfer" className="btn secondary">
            <ArrowsLeftRight size={16} weight="bold" aria-hidden="true" />
            Transfer erfassen
          </Link>
          <Link to="/transactions/add" className="btn secondary">
            <Plus size={16} weight="bold" aria-hidden="true" />
            Buchung erfassen
          </Link>
        </div>
      </div>

      <div className="filter-bar">
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Suche nach Beschreibung/Gegenpartei …"
          aria-label="Buchungen durchsuchen"
          className="search-input"
        />
        <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="filter-select">
          <option value="">Alle Umschläge</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <label className="helptext" htmlFor="date_from">
          von
        </label>
        <input id="date_from" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="date-input" />
        <label className="helptext" htmlFor="date_to">
          bis
        </label>
        <input id="date_to" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="date-input" />
        {hasDateRange && (
          <button type="button" className="link-action" onClick={resetDateRange}>
            Zeitraum zurücksetzen
          </button>
        )}
      </div>
      {hasDateRange && <p className="helptext">Zeitraum-Filter aktiv — überschreibt die Monatsauswahl oben.</p>}

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
                  <td>{t.is_transfer ? <span className="badge">Transfer</span> : (t.category_name ?? '—')}</td>
                  <td className={`amount-cell ${t.is_expense ? 'negative' : 'positive'}`}>{formatMoney(t.amount)}</td>
                  <td className="nowrap">
                    <Link to={`/transactions/${t.id}/edit`} className="link-action">
                      <PencilSimple size={14} weight="bold" aria-hidden="true" />
                      bearbeiten
                    </Link>
                    <button
                      type="button"
                      className="link-action danger"
                      onClick={() => void handleDelete(t)}
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
