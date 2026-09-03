import { Bank, PencilSimple, Plus } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { extractErrorMessage } from '../api/errors'
import type { Account } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { SkeletonRows } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'
import { formatMoney, moneyClass } from '../utils/format'

const TYPE_LABELS: Record<string, string> = {
  checking: 'Girokonto',
  savings: 'Sparkonto',
  cash: 'Bargeld',
  credit: 'Kreditkarte',
}

export function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [loading, setLoading] = useState(true)
  const push = useToast()

  const load = useCallback(() => {
    setLoading(true)
    return api
      .get<Account[]>('/accounts/')
      .then((res) => setAccounts(res.data))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function toggleArchive(id: number) {
    try {
      await api.post(`/accounts/${id}/archive_toggle/`)
      void load()
    } catch (err) {
      push('error', extractErrorMessage(err))
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Konten</h1>
          <p>Alle deine Bankkonten und Bargeldkassen.</p>
        </div>
        <Link to="/accounts/new" className="btn secondary">
          <Plus size={16} weight="bold" aria-hidden="true" />
          Neues Konto
        </Link>
      </div>

      {loading ? (
        <SkeletonRows count={3} />
      ) : accounts.length === 0 ? (
        <EmptyState>
          Noch keine Konten. <Link to="/accounts/new">Erstes Konto anlegen</Link>
        </EmptyState>
      ) : (
        <div className="row-list">
          {accounts.map((a) => (
            <div className="row-item" key={a.id}>
              <div className="row-icon">
                <Bank size={18} weight="regular" aria-hidden="true" />
              </div>
              <div className="row-main">
                <Link to={`/accounts/${a.id}`} className="row-title">
                  {a.name}
                </Link>
                <div className="row-sub">
                  {TYPE_LABELS[a.account_type] ?? a.account_type}
                  {a.iban && ` · ${a.iban}`}
                  {a.is_archived && <span className="badge">archiviert</span>}
                  <Link to={`/accounts/${a.id}/edit`} className="link-action">
                    <PencilSimple size={12} weight="bold" aria-hidden="true" />
                    bearbeiten
                  </Link>
                  <button type="button" className="link-action" onClick={() => void toggleArchive(a.id)}>
                    {a.is_archived ? 'reaktivieren' : 'archivieren'}
                  </button>
                </div>
              </div>
              <div className={`row-amount num ${moneyClass(a.balance)}`}>{formatMoney(a.balance)}</div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
