import { ChartLineDown, Plus } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/client'
import type { Debt, PayoffResult, PayoffStrategy } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { InfoTooltip } from '../components/InfoTooltip'
import { PayoffChart } from '../components/PayoffChart'
import { ProgressBar } from '../components/ProgressBar'
import { Skeleton, SkeletonRows } from '../components/Skeleton'
import { formatDate, formatMoney } from '../utils/format'

export function DebtsPage() {
  const [debts, setDebts] = useState<Debt[]>([])
  const [strategy, setStrategy] = useState<PayoffStrategy>('avalanche')
  const [extra, setExtra] = useState('0')
  const [result, setResult] = useState<PayoffResult | null>(null)
  const [loading, setLoading] = useState(true)

  const loadDebts = useCallback(() => {
    return api.get<Debt[]>('/debts/', { params: { open_only: 1 } }).then((res) => setDebts(res.data))
  }, [])

  useEffect(() => {
    setLoading(true)
    Promise.all([loadDebts(), loadPayoff(strategy, extra)]).finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function loadPayoff(s: PayoffStrategy, e: string) {
    return api.get<PayoffResult>('/debts/payoff/', { params: { strategy: s, extra: e } }).then((res) => setResult(res.data))
  }

  function handleStrategyChange(s: PayoffStrategy) {
    setStrategy(s)
    void loadPayoff(s, extra)
  }

  function handleExtraBlur() {
    void loadPayoff(strategy, extra)
  }

  if (loading) {
    return (
      <div aria-busy="true">
        <div className="card">
          <Skeleton lines={4} />
        </div>
        <SkeletonRows count={2} />
      </div>
    )
  }

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Schulden</h1>
          <p>Tilgungsplan nach Avalanche- oder Snowball-Strategie.</p>
        </div>
        <Link to="/debts/new" className="btn secondary">
          <Plus size={16} weight="bold" aria-hidden="true" />
          Schuld erfassen
        </Link>
      </div>

      {debts.length === 0 ? (
        <EmptyState>
          Keine offenen Schulden erfasst. <Link to="/debts/new">Jetzt erfassen</Link>
        </EmptyState>
      ) : (
        <>
          <div className="card">
            <div className="stat-grid">
              <div>
                <div className="hero-label">Restschuld gesamt</div>
                <div className="stat-value negative num">{formatMoney(result?.total_balance ?? '0')}</div>
              </div>
              <div>
                <div className="hero-label">Mindestraten / Monat</div>
                <div className="stat-value num">{formatMoney(result?.total_minimum ?? '0')}</div>
              </div>
              <div>
                <div className="hero-label">Schuldenfrei am</div>
                <div className="stat-value num">{formatDate(result?.debt_free_date)}</div>
              </div>
              <div>
                <div className="hero-label">Zinskosten gesamt</div>
                <div className="stat-value negative num">{formatMoney(result?.total_interest ?? '0')}</div>
              </div>
            </div>

            <div className="form-row" style={{ marginTop: 24, alignItems: 'flex-end' }}>
              <div className="field" style={{ minWidth: 220 }}>
                <label id="strategy-label">Strategie</label>
                <div className="toggle-group" style={{ width: '100%' }} role="group" aria-labelledby="strategy-label">
                  <button
                    type="button"
                    className={strategy === 'avalanche' ? 'active' : ''}
                    style={{ flex: 1 }}
                    aria-pressed={strategy === 'avalanche'}
                    onClick={() => handleStrategyChange('avalanche')}
                  >
                    Avalanche
                  </button>
                  <button
                    type="button"
                    className={strategy === 'snowball' ? 'active' : ''}
                    style={{ flex: 1 }}
                    aria-pressed={strategy === 'snowball'}
                    onClick={() => handleStrategyChange('snowball')}
                  >
                    Snowball
                  </button>
                </div>
                <div className="strategy-legend">
                  <span className="strategy-legend-item">
                    Höchster Zins zuerst
                    <InfoTooltip text="Avalanche: Das Extra-Budget fliesst zuerst in die Schuld mit dem höchsten Zinssatz. Das minimiert die gesamten Zinskosten." />
                  </span>
                  <span className="strategy-legend-item">
                    Kleinste Restschuld zuerst
                    <InfoTooltip text="Snowball: Das Extra-Budget fliesst zuerst in die Schuld mit der kleinsten Restschuld. Schnelle Erfolgserlebnisse motivieren zum Durchhalten." />
                  </span>
                </div>
              </div>
              <div className="field">
                <label htmlFor="extra">Extra-Budget / Monat</label>
                <input
                  id="extra"
                  value={extra}
                  onChange={(e) => setExtra(e.target.value)}
                  onBlur={handleExtraBlur}
                  aria-describedby="extra-help"
                />
                <p className="helptext" id="extra-help">
                  Nur mit Extra-Budget wirkt sich die Strategie auf Tilgungsreihenfolge, Laufzeit und Zinskosten aus — ohne
                  Extra-Budget zahlt jede Schuld nur ihre Mindestrate.
                </p>
              </div>
            </div>
          </div>

          {result && result.schedule.length > 0 && (
            <div className="card chart-card">
              <div className="hero-label">Tilgungsverlauf</div>
              <PayoffChart data={result.schedule} />
            </div>
          )}

          {result && result.payoff_order.length > 0 && (
            <>
              <div className="section-title">Tilgungsreihenfolge</div>
              <div className="card">
                <ol className="payoff-order">
                  {result.payoff_order.map((name) => (
                    <li key={name}>{name}</li>
                  ))}
                </ol>
              </div>
            </>
          )}

          <div className="section-title">Offene Schulden</div>
          <div className="row-list">
            {debts.map((d) => (
              <div className="row-item" key={d.id}>
                <div className="row-icon">
                  <ChartLineDown size={18} weight="regular" aria-hidden="true" />
                </div>
                <div className="row-main">
                  <Link to={`/debts/${d.id}`} className="row-title">
                    {d.name}
                  </Link>
                  <div className="row-sub">
                    {d.creditor && `${d.creditor} · `}
                    {d.interest_rate}% Zins · Mindestrate {formatMoney(d.minimum_payment)}
                  </div>
                  <ProgressBar percent={d.progress_percent} />
                </div>
                <div className="row-amount num negative">{formatMoney(d.current_balance)}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}
