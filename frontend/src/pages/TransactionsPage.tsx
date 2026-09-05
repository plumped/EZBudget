import { ArrowsLeftRight, PencilSimple, Plus, Trash } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../api/client'
import { extractErrorMessage } from '../api/errors'
import type { Account, Category, Transaction } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { MonthSwitcher } from '../components/MonthSwitcher'
import { Skeleton } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'
import { useMonthParam } from '../utils/useMonthParam'
import { formatMoney } from '../utils/format'

type EditableField = 'account' | 'category' | 'amount'

export function TransactionsPage() {
  const { year, month, label, prevYear, prevMonth, nextYear, nextMonth, setMonth } = useMonthParam()
  const [searchParams] = useSearchParams()
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [categoryFilter, setCategoryFilter] = useState(() => searchParams.get('category') ?? '')
  const [searchInput, setSearchInput] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState<{ id: number; field: EditableField } | null>(null)
  const [savingId, setSavingId] = useState<number | null>(null)
  const [amountDraft, setAmountDraft] = useState('')
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
    api.get<Account[]>('/accounts/', { params: { active_only: 1 } }).then((res) => setAccounts(res.data))
  }, [])

  function resetDateRange() {
    setDateFrom('')
    setDateTo('')
  }

  async function saveField(t: Transaction, field: EditableField, value: string) {
    let patch: Record<string, string | number | null>
    if (field === 'account') {
      if (Number(value) === t.account) {
        setEditing(null)
        return
      }
      patch = { account: Number(value) }
    } else if (field === 'category') {
      const nextCategory = value ? Number(value) : null
      if (nextCategory === t.category) {
        setEditing(null)
        return
      }
      patch = { category: nextCategory }
    } else {
      const trimmed = value.trim().replace(/'/g, '').replace(',', '.')
      const explicitSign = trimmed.startsWith('+') || trimmed.startsWith('-')
      const parsed = Math.abs(parseFloat(trimmed) || 0)
      const wasNegative = parseFloat(t.amount) < 0
      const signed = explicitSign ? parseFloat(trimmed) : wasNegative ? -parsed : parsed
      if (signed.toFixed(2) === parseFloat(t.amount).toFixed(2)) {
        setEditing(null)
        return
      }
      patch = { amount: signed.toFixed(2) }
    }

    setSavingId(t.id)
    try {
      const res = await api.patch<Transaction>(`/transactions/${t.id}/`, patch)
      setTransactions((prev) => prev.map((row) => (row.id === t.id ? res.data : row)))
      setEditing(null)
    } catch (err) {
      push('error', extractErrorMessage(err))
    } finally {
      setSavingId(null)
    }
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
          <option value="none">Ohne Umschlag</option>
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
                  <td>
                    {editing?.id === t.id && editing.field === 'account' ? (
                      <select
                        autoFocus
                        className="cell-edit-select"
                        defaultValue={t.account}
                        disabled={savingId === t.id}
                        onChange={(e) => void saveField(t, 'account', e.target.value)}
                        onBlur={() => setEditing(null)}
                        onKeyDown={(e) => e.key === 'Escape' && setEditing(null)}
                      >
                        {accounts.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <button
                        type="button"
                        className="cell-edit-trigger"
                        onClick={() => setEditing({ id: t.id, field: 'account' })}
                        aria-label={`Konto ändern (aktuell ${t.account_name})`}
                      >
                        {t.account_name}
                      </button>
                    )}
                  </td>
                  <td>
                    {t.is_transfer ? (
                      <span className="badge">Transfer</span>
                    ) : editing?.id === t.id && editing.field === 'category' ? (
                      <select
                        autoFocus
                        className="cell-edit-select"
                        defaultValue={t.category ?? ''}
                        disabled={savingId === t.id}
                        onChange={(e) => void saveField(t, 'category', e.target.value)}
                        onBlur={() => setEditing(null)}
                        onKeyDown={(e) => e.key === 'Escape' && setEditing(null)}
                      >
                        <option value="">— ohne —</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <button
                        type="button"
                        className="cell-edit-trigger"
                        onClick={() => setEditing({ id: t.id, field: 'category' })}
                        aria-label={`Umschlag ändern (aktuell ${t.category_name ?? 'ohne Umschlag'})`}
                      >
                        {t.category_name ?? '—'}
                      </button>
                    )}
                  </td>
                  <td className={`amount-cell ${t.is_expense ? 'negative' : 'positive'}`}>
                    {editing?.id === t.id && editing.field === 'amount' ? (
                      <input
                        autoFocus
                        className="cell-edit-input"
                        value={amountDraft}
                        disabled={savingId === t.id}
                        onChange={(e) => setAmountDraft(e.target.value)}
                        onFocus={(e) => e.target.select()}
                        onBlur={() => void saveField(t, 'amount', amountDraft)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') e.currentTarget.blur()
                          if (e.key === 'Escape') setEditing(null)
                        }}
                      />
                    ) : (
                      <button
                        type="button"
                        className="cell-edit-trigger"
                        onClick={() => {
                          setAmountDraft(Math.abs(parseFloat(t.amount)).toFixed(2))
                          setEditing({ id: t.id, field: 'amount' })
                        }}
                        aria-label={`Betrag ändern (aktuell ${formatMoney(t.amount)})`}
                      >
                        {formatMoney(t.amount)}
                      </button>
                    )}
                  </td>
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
