import { ArrowsClockwise, PencilSimple, Plus, Trash } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { extractErrorMessage } from '../api/errors'
import type { RecurringTransaction } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { SkeletonRows } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'
import { formatDate, formatMoney } from '../utils/format'

const WEEKDAY_NAMES = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
const MONTH_NAMES = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
]

function describeFrequency(rt: RecurringTransaction): string {
  switch (rt.frequency) {
    case 'weekly':
      return `Wöchentlich, ${WEEKDAY_NAMES[rt.weekday]}`
    case 'biweekly':
      return `Alle 2 Wochen, ${WEEKDAY_NAMES[rt.weekday]} (ab ${formatDate(rt.start_date)})`
    case 'yearly':
      return `Jährlich, ${rt.day_of_month}. ${MONTH_NAMES[rt.month_of_year - 1]}`
    default:
      return `Monatlich, Tag ${rt.day_of_month}`
  }
}

export function RecurringPage() {
  const [recurring, setRecurring] = useState<RecurringTransaction[]>([])
  const [loading, setLoading] = useState(true)
  const push = useToast()

  const load = useCallback(() => {
    setLoading(true)
    return api
      .get<RecurringTransaction[]>('/recurring/')
      .then((res) => setRecurring(res.data))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function handleGenerate() {
    try {
      const res = await api.post<{ created_count: number }>('/recurring/generate/')
      push(res.data.created_count > 0 ? 'success' : 'info', res.data.created_count > 0 ? `${res.data.created_count} Buchung(en) generiert.` : 'Keine fälligen wiederkehrenden Buchungen.')
    } catch (err) {
      push('error', extractErrorMessage(err))
    }
  }

  async function handleDelete(id: number, description: string) {
    if (!confirm(`Dauerauftrag „${description}“ wirklich löschen?`)) return
    try {
      await api.delete(`/recurring/${id}/`)
      push('success', `Dauerauftrag „${description}“ gelöscht.`)
      void load()
    } catch (err) {
      push('error', extractErrorMessage(err))
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Wiederkehrende Buchungen</h1>
          <p>Fixkosten, Abos und Lohn, die automatisch in der gewählten Frequenz gebucht werden.</p>
        </div>
        <div className="page-header-actions">
          <button type="button" className="btn secondary" onClick={() => void handleGenerate()}>
            <ArrowsClockwise size={16} weight="bold" aria-hidden="true" />
            Jetzt generieren
          </button>
          <Link to="/recurring/new" className="btn secondary">
            <Plus size={16} weight="bold" aria-hidden="true" />
            Neu
          </Link>
        </div>
      </div>

      {loading ? (
        <SkeletonRows count={4} />
      ) : recurring.length === 0 ? (
        <EmptyState>
          Noch keine Daueraufträge. <Link to="/recurring/new">Ersten anlegen</Link>
        </EmptyState>
      ) : (
        <div className="row-list">
          {recurring.map((rt) => (
            <div className="row-item" key={rt.id}>
              <div className="row-dot" style={{ background: rt.category_color ?? 'var(--color-faint-fg)' }} />
              <div className="row-main">
                <span className="row-title">{rt.description}</span>
                <div className="row-sub">
                  {describeFrequency(rt)} · {rt.account_name}
                  {rt.category_name ? ` · ${rt.category_name}` : ''}
                  {!rt.is_active && <span className="badge">pausiert</span>}
                  <Link to={`/recurring/${rt.id}/edit`} className="link-action">
                    <PencilSimple size={12} weight="bold" aria-hidden="true" />
                    bearbeiten
                  </Link>
                  <button type="button" className="link-action danger" onClick={() => void handleDelete(rt.id, rt.description)}>
                    <Trash size={12} weight="bold" aria-hidden="true" />
                    löschen
                  </button>
                </div>
              </div>
              <div className={`row-amount num ${parseFloat(rt.amount) < 0 ? 'negative' : 'positive'}`}>{formatMoney(rt.amount)}</div>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
