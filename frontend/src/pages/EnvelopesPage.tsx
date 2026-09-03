import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import type { Category } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { KindBadge } from '../components/KindBadge'
import { MonthSwitcher } from '../components/MonthSwitcher'
import { ProgressBar } from '../components/ProgressBar'
import { extractErrorMessage } from '../api/errors'
import { useToast } from '../context/ToastContext'
import { useMonthParam } from '../utils/useMonthParam'
import { formatMoney, moneyClass } from '../utils/format'

export function EnvelopesPage() {
  const { year, month, label, prevYear, prevMonth, nextYear, nextMonth, setMonth } = useMonthParam()
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const push = useToast()

  const load = useCallback(() => {
    setLoading(true)
    return api
      .get<Category[]>('/categories/', { params: { year, month, active_only: 1 } })
      .then((res) => setCategories(res.data))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, month])

  useEffect(() => {
    void load()
  }, [load])

  async function toggleArchive(id: number) {
    try {
      await api.post(`/categories/${id}/archive_toggle/`)
      void load()
    } catch (err) {
      push('error', extractErrorMessage(err))
    }
  }

  if (loading) {
    return <div className="loading-shell">Lädt …</div>
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Umschläge</h1>
          <p>Jeder Franken hat einen Job.</p>
        </div>
        <div className="page-header-actions">
          <MonthSwitcher label={label} onPrev={() => setMonth(prevYear, prevMonth)} onNext={() => setMonth(nextYear, nextMonth)} />
          <Link to="/envelopes/new" className="btn secondary">
            + Neuer Umschlag
          </Link>
        </div>
      </div>

      <div className="row-list">
        {categories.length === 0 ? (
          <div style={{ padding: '20px' }}>
            <EmptyState>
              Noch keine Umschläge angelegt. <Link to="/envelopes/new">Ersten Umschlag anlegen</Link>
            </EmptyState>
          </div>
        ) : (
          categories.map((c) => (
            <div className="row-item" key={c.id}>
              <div className="row-dot" style={{ background: c.color }} />
              <div className="row-main">
                <Link to={`/envelopes/${c.id}`} className="row-title">
                  {c.icon} {c.name}
                </Link>
                <div className="row-sub">
                  <KindBadge kind={c.kind} />
                  {c.keywords && <span className="mono">auto: {c.keywords}</span>}
                  <Link to={`/envelopes/${c.id}/edit`} className="link-action">
                    bearbeiten
                  </Link>
                  <button type="button" className="link-action" onClick={() => void toggleArchive(c.id)}>
                    archivieren
                  </button>
                </div>
                <ProgressBar percent={c.progress} over={c.progress >= 100} />
              </div>
              <div className={`row-amount num ${moneyClass(c.rollover)}`}>
                {formatMoney(c.rollover)}
                <div className="row-amount-sub">verfügbar mit Übertrag ({formatMoney(c.available)} diesen Monat)</div>
              </div>
            </div>
          ))
        )}
      </div>
    </>
  )
}
