import { ArrowRight } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import type { DashboardData } from '../api/types'
import { KindIcon } from '../components/KindIcon'
import { MonthSwitcher } from '../components/MonthSwitcher'
import { ProgressBar } from '../components/ProgressBar'
import { EmptyState } from '../components/EmptyState'
import { Skeleton, SkeletonRows } from '../components/Skeleton'
import { useToast } from '../context/ToastContext'
import { useMonthParam } from '../utils/useMonthParam'
import { formatMoney, moneyClass } from '../utils/format'

export function DashboardPage() {
  const { year, month, label, prevYear, prevMonth, nextYear, nextMonth, setMonth } = useMonthParam()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const push = useToast()

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    api
      .get<DashboardData>('/dashboard/', { params: { year, month } })
      .then((res) => {
        if (cancelled) return
        setData(res.data)
        for (const txn of res.data.generated_recurring) {
          push('info', `Wiederkehrende Buchung generiert: ${txn.description} (${formatMoney(txn.amount)}).`)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [year, month])

  if (loading || !data) {
    return (
      <div aria-busy="true">
        <div className="page-header">
          <div>
            <h1>Übersicht</h1>
            <p>Dein Geld auf einen Blick.</p>
          </div>
        </div>
        <div className="card">
          <Skeleton lines={3} />
        </div>
        <div className="section-title">Fixkosten</div>
        <SkeletonRows count={3} />
      </div>
    )
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Übersicht</h1>
          <p>{label} — dein Geld auf einen Blick.</p>
        </div>
        <MonthSwitcher label={label} onPrev={() => setMonth(prevYear, prevMonth)} onNext={() => setMonth(nextYear, nextMonth)} />
      </div>

      <div className="card">
        <div className="hero-label">Gesamtguthaben, alle Konten</div>
        <div className="hero-figure num">CHF {formatMoney(data.total_balance)}</div>
        <div className="stat-grid">
          <div>
            <div className="hero-label">Einnahmen diesen Monat</div>
            <div className="stat-value positive num">+{formatMoney(data.income_total)}</div>
          </div>
          <div>
            <div className="hero-label">Ausgaben diesen Monat</div>
            <div className="stat-value negative num">-{formatMoney(data.expense_total)}</div>
          </div>
          <div>
            <div className="hero-label">Netto</div>
            <div className={`stat-value ${moneyClass(data.net_total)} num`}>{formatMoney(data.net_total)}</div>
          </div>
          {data.open_debts_count > 0 && (
            <div>
              <div className="hero-label">Restschulden ({data.open_debts_count})</div>
              <div className="stat-value negative num">{formatMoney(data.total_debt)}</div>
            </div>
          )}
        </div>
      </div>

      <div className="section-title">
        Fixkosten <span className="tag num">{formatMoney(data.fixed.spent)} / {formatMoney(data.fixed.budgeted)} CHF</span>
      </div>
      <div className="row-list">
        {data.fixed.categories.length === 0 ? (
          <div className="content-pad">
            <EmptyState>
              Noch keine Fixkosten-Umschläge. <Link to="/envelopes">Jetzt anlegen</Link>
            </EmptyState>
          </div>
        ) : (
          data.fixed.categories.map((c) => (
            <div className="row-item" key={c.id}>
              <KindIcon kind={c.kind} color={c.color} icon={c.icon} />
              <div className="row-main">
                <Link to={`/envelopes/${c.id}?year=${year}&month=${month}`} className="row-title">
                  {c.name}
                </Link>
                <ProgressBar percent={c.progress} over={c.progress >= 100} />
              </div>
              <div className="row-amount num">{formatMoney(c.monthly_budget)}</div>
            </div>
          ))
        )}
      </div>

      <div className="section-title">
        Variable Kosten <span className="tag num">{formatMoney(data.variable.spent)} / {formatMoney(data.variable.budgeted)} CHF</span>
      </div>
      <div className="row-list">
        {data.variable.categories.length === 0 ? (
          <div className="content-pad">
            <EmptyState>Noch keine Umschläge für variable Kosten.</EmptyState>
          </div>
        ) : (
          data.variable.categories.map((c) => (
            <div className="row-item" key={c.id}>
              <KindIcon kind={c.kind} color={c.color} icon={c.icon} />
              <div className="row-main">
                <Link to={`/envelopes/${c.id}?year=${year}&month=${month}`} className="row-title">
                  {c.name}
                </Link>
                <ProgressBar percent={c.progress} over={c.progress >= 100} />
              </div>
              <div className="row-amount num">{formatMoney(c.monthly_budget)}</div>
            </div>
          ))
        )}
      </div>

      {data.open_debts_count > 0 && (
        <>
          <div className="section-title">
            Schulden{' '}
            <span className="tag">
              <Link to="/debts">
                Tilgungsplan ansehen <ArrowRight size={14} weight="bold" aria-hidden="true" />
              </Link>
            </span>
          </div>
          <div className="card">
            <div className="stat-grid">
              <div>
                <div className="hero-label">Restschuld gesamt</div>
                <div className="stat-value negative num">{formatMoney(data.total_debt)}</div>
              </div>
              <div>
                <div className="hero-label">Mindestraten / Monat</div>
                <div className="stat-value num">{formatMoney(data.total_minimum)}</div>
              </div>
            </div>
          </div>
        </>
      )}

      <div className="section-title">
        Letzte Buchungen{' '}
        <span className="tag">
          <Link to="/transactions">
            alle ansehen <ArrowRight size={14} weight="bold" aria-hidden="true" />
          </Link>
        </span>
      </div>
      <div className="row-list">
        {data.recent_transactions.length === 0 ? (
          <div className="content-pad">
            <EmptyState>
              Noch keine Buchungen. <Link to="/import">CAMT.053 importieren</Link> oder{' '}
              <Link to="/transactions/add">manuell erfassen</Link>.
            </EmptyState>
          </div>
        ) : (
          data.recent_transactions.map((t) => (
            <div className="row-item" key={t.id}>
              <div className="row-dot" style={{ background: t.category_color ?? '#98a2b3' }} />
              <div className="row-main">
                <span className="row-title">{t.description || '(keine Beschreibung)'}</span>
                <div className="row-sub">
                  {t.date} · {t.account_name}
                  {t.is_transfer ? <span className="badge">Transfer</span> : t.category_name ? ` · ${t.category_name}` : ''}
                </div>
              </div>
              <div className={`row-amount num ${t.is_expense ? 'negative' : 'positive'}`}>{formatMoney(t.amount)}</div>
            </div>
          ))
        )}
      </div>
    </>
  )
}
