import { Archive, Envelope, List, PencilSimple, Plus } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import type { Category } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { KindBadge } from '../components/KindBadge'
import { KindIcon } from '../components/KindIcon'
import { MonthSwitcher } from '../components/MonthSwitcher'
import { ProgressBar } from '../components/ProgressBar'
import { SkeletonRows } from '../components/Skeleton'
import { extractErrorMessage } from '../api/errors'
import { useToast } from '../context/ToastContext'
import { useMonthParam } from '../utils/useMonthParam'
import { formatMoney, moneyClass } from '../utils/format'

type ViewMode = 'list' | 'cards'
const VIEW_STORAGE_KEY = 'ezbudget.envelopes.view'

function loadStoredView(): ViewMode {
  try {
    const stored = localStorage.getItem(VIEW_STORAGE_KEY)
    return stored === 'cards' ? 'cards' : 'list'
  } catch {
    return 'list'
  }
}

export function EnvelopesPage() {
  const { year, month, label, prevYear, prevMonth, nextYear, nextMonth, setMonth } = useMonthParam()
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState<ViewMode>(loadStoredView)
  const [showArchived, setShowArchived] = useState(false)
  const push = useToast()

  function changeView(next: ViewMode) {
    setView(next)
    try {
      localStorage.setItem(VIEW_STORAGE_KEY, next)
    } catch {
      // localStorage kann in privaten Modi/eingeschränkten Browsern fehlschlagen — Ansicht bleibt trotzdem für die Session gesetzt.
    }
  }

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, number | string> = { year, month }
    if (!showArchived) params.active_only = 1
    return api
      .get<Category[]>('/categories/', { params })
      .then((res) => setCategories(res.data))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, month, showArchived])

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

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Umschläge</h1>
          <p>Jeder Franken hat einen Job.</p>
        </div>
        <div className="page-header-actions">
          <MonthSwitcher label={label} onPrev={() => setMonth(prevYear, prevMonth)} onNext={() => setMonth(nextYear, nextMonth)} />
          <label className="archived-toggle">
            <input type="checkbox" checked={showArchived} onChange={(e) => setShowArchived(e.target.checked)} />
            Archivierte anzeigen
          </label>
          <div className="toggle-group" role="group" aria-label="Ansicht">
            <button type="button" className={view === 'list' ? 'active' : ''} aria-pressed={view === 'list'} onClick={() => changeView('list')}>
              <List size={14} weight="bold" aria-hidden="true" />
              Liste
            </button>
            <button type="button" className={view === 'cards' ? 'active' : ''} aria-pressed={view === 'cards'} onClick={() => changeView('cards')}>
              <Envelope size={14} weight="bold" aria-hidden="true" />
              Umschläge
            </button>
          </div>
          <Link to="/envelopes/new" className="btn secondary">
            <Plus size={16} weight="bold" aria-hidden="true" />
            Neuer Umschlag
          </Link>
        </div>
      </div>

      {loading ? (
        <SkeletonRows count={5} />
      ) : categories.length === 0 ? (
        <EmptyState>
          Noch keine Umschläge angelegt. <Link to="/envelopes/new">Ersten Umschlag anlegen</Link>
        </EmptyState>
      ) : view === 'list' ? (
        <div className="row-list">
          {categories.map((c) => (
            <div className={`row-item${c.is_archived ? ' archived' : ''}`} key={c.id}>
              <KindIcon kind={c.kind} color={c.color} icon={c.icon} />
              <div className="row-main">
                <Link to={`/envelopes/${c.id}?year=${year}&month=${month}`} className="row-title">
                  {c.name}
                </Link>
                <div className="row-sub">
                  <KindBadge kind={c.kind} />
                  {c.is_archived && <span className="badge">archiviert</span>}
                  {c.keywords && <span className="mono">auto: {c.keywords}</span>}
                  <Link to={`/envelopes/${c.id}/edit`} className="link-action">
                    <PencilSimple size={12} weight="bold" aria-hidden="true" />
                    bearbeiten
                  </Link>
                  <button type="button" className="link-action" onClick={() => void toggleArchive(c.id)}>
                    <Archive size={12} weight="bold" aria-hidden="true" />
                    {c.is_archived ? 'reaktivieren' : 'archivieren'}
                  </button>
                </div>
                <ProgressBar percent={c.progress} over={c.progress >= 100} />
              </div>
              <div className={`row-amount num ${moneyClass(c.rollover)}`}>
                {formatMoney(c.rollover)}
                <div className="row-amount-sub">verfügbar mit Übertrag ({formatMoney(c.available)} diesen Monat)</div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="envelope-grid">
          {categories.map((c) => (
            <div className={`envelope-card${c.is_archived ? ' archived' : ''}`} key={c.id}>
              <div className="envelope-flap" style={{ background: `${c.color}33` }} />
              <div className="envelope-seal">
                <KindIcon kind={c.kind} color={c.color} icon={c.icon} size={32} />
              </div>
              <div className="envelope-body">
                <Link to={`/envelopes/${c.id}?year=${year}&month=${month}`} className="envelope-name">
                  {c.name}
                </Link>
                <div className="envelope-kind">
                  <KindBadge kind={c.kind} />
                </div>
                <div className="envelope-progress">
                  <ProgressBar percent={c.progress} over={c.progress >= 100} />
                </div>
                <div className={`envelope-amount num ${moneyClass(c.rollover)}`}>{formatMoney(c.rollover)}</div>
                <div className="envelope-amount-sub">verfügbar mit Übertrag ({formatMoney(c.available)} diesen Monat)</div>
                <div className="envelope-actions">
                  <Link to={`/envelopes/${c.id}/edit`} className="link-action">
                    <PencilSimple size={12} weight="bold" aria-hidden="true" />
                    bearbeiten
                  </Link>
                  <button type="button" className="link-action" onClick={() => void toggleArchive(c.id)}>
                    <Archive size={12} weight="bold" aria-hidden="true" />
                    {c.is_archived ? 'reaktivieren' : 'archivieren'}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
