import { PencilSimple, Plus, Trash } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import { extractErrorMessage } from '../api/errors'
import type { Rule, RuleField, RuleMatchType } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { SkeletonRows } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'

const FIELD_LABELS: Record<RuleField, string> = {
  description: 'Beschreibung',
  counterparty: 'Gegenpartei',
  either: 'Beschreibung/Gegenpartei',
}

const MATCH_LABELS: Record<RuleMatchType, string> = {
  contains: 'enthält',
  startswith: 'beginnt mit',
  exact: 'ist genau',
}

export function RulesPage() {
  const [rules, setRules] = useState<Rule[]>([])
  const [loading, setLoading] = useState(true)
  const push = useToast()

  const load = useCallback(() => {
    setLoading(true)
    return api
      .get<Rule[]>('/import/rules/')
      .then((res) => setRules(res.data))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function handleDelete(id: number, label: string) {
    if (!confirm(`Regel „${label}“ wirklich löschen?`)) return
    try {
      await api.delete(`/import/rules/${id}/`)
      push('success', `Regel „${label}“ gelöscht.`)
      void load()
    } catch (err) {
      push('error', extractErrorMessage(err))
    }
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Regeln</h1>
          <p>Legt fest, welcher Umschlag beim CAMT.053-Import automatisch zugeordnet wird.</p>
        </div>
        <Link to="/rules/new" className="btn secondary">
          <Plus size={16} weight="bold" aria-hidden="true" />
          Neue Regel
        </Link>
      </div>

      {loading ? (
        <SkeletonRows count={4} />
      ) : rules.length === 0 ? (
        <EmptyState>
          Noch keine Regeln. <Link to="/rules/new">Erste Regel anlegen</Link>
        </EmptyState>
      ) : (
        <div className="row-list">
          {rules.map((r) => {
            const label = r.name || r.value
            return (
              <div className="row-item" key={r.id}>
                <div className="row-dot" style={{ background: r.category_color || 'var(--color-faint-fg)' }} />
                <div className="row-main">
                  <span className="row-title">{label}</span>
                  <div className="row-sub">
                    {FIELD_LABELS[r.field]} {MATCH_LABELS[r.match_type]} „{r.value}“ → {r.category_name}
                    {' · '}Priorität {r.priority}
                    {!r.is_active && <span className="badge">inaktiv</span>}
                    <Link to={`/rules/${r.id}/edit`} className="link-action">
                      <PencilSimple size={12} weight="bold" aria-hidden="true" />
                      bearbeiten
                    </Link>
                    <button type="button" className="link-action danger" onClick={() => void handleDelete(r.id, label)}>
                      <Trash size={12} weight="bold" aria-hidden="true" />
                      löschen
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}
