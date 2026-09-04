import { useEffect, useState } from 'react'
import api from '../api/client'
import type { TrendsData } from '../api/types'
import { EmptyState } from '../components/EmptyState'
import { Skeleton } from '../components/Skeleton'
import { TrendChart } from '../components/TrendChart'
import { formatMoney, formatMonthLabel } from '../utils/format'

export function TrendsPage() {
  const [data, setData] = useState<TrendsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [categoryId, setCategoryId] = useState('')

  useEffect(() => {
    api.get<TrendsData>('/trends/', { params: { months: 12 } }).then((res) => {
      setData(res.data)
      if (res.data.categories.length > 0) setCategoryId(String(res.data.categories[0].id))
      setLoading(false)
    })
  }, [])

  if (loading || !data) {
    return (
      <div aria-busy="true">
        <div className="page-header">
          <div>
            <h1>Trends &amp; Insights</h1>
            <p>Verlauf der letzten Monate.</p>
          </div>
        </div>
        <div className="card">
          <Skeleton lines={4} />
        </div>
      </div>
    )
  }

  const monthLabels = data.months.map((m) => formatMonthLabel(`${m.year}-${String(m.month).padStart(2, '0')}-01`, m.month))
  const selectedCategory = data.categories.find((c) => String(c.id) === categoryId)

  const yoy = data.year_over_year
  const expenseDelta = Number(yoy.current_expense) - Number(yoy.previous_expense)
  const incomeDelta = Number(yoy.current_income) - Number(yoy.previous_income)
  const previousLabel = formatMonthLabel(
    `${yoy.previous_year}-${String(yoy.current_month).padStart(2, '0')}-01`,
    yoy.current_month,
  )

  return (
    <>
      <div className="page-header">
        <div>
          <h1>Trends &amp; Insights</h1>
          <p>Verlauf der letzten {data.months.length} Monate.</p>
        </div>
      </div>

      <div className="card chart-card">
        <div className="hero-label">Einnahmen vs. Ausgaben</div>
        <TrendChart
          labels={monthLabels}
          series={[
            { label: 'Einnahmen', color: 'var(--color-positive)', values: data.income_by_month.map(Number) },
            { label: 'Ausgaben', color: 'var(--color-destructive)', values: data.expense_by_month.map(Number) },
          ]}
          formatValue={(v) => `CHF ${formatMoney(v)}`}
          caption={`Einnahmen und Ausgaben der letzten ${data.months.length} Monate.`}
        />
      </div>

      <div className="section-title">Jahresvergleich</div>
      <div className="card">
        <div className="stat-grid">
          <div>
            <div className="hero-label">Ausgaben diesen Monat</div>
            <div className="stat-value negative num">{formatMoney(yoy.current_expense)}</div>
            <p className={`helptext ${expenseDelta > 0 ? 'text-negative' : 'text-positive'}`}>
              {expenseDelta >= 0 ? '+' : '−'}
              {formatMoney(Math.abs(expenseDelta))} ggü. {previousLabel}
            </p>
          </div>
          <div>
            <div className="hero-label">Einnahmen diesen Monat</div>
            <div className="stat-value positive num">{formatMoney(yoy.current_income)}</div>
            <p className={`helptext ${incomeDelta >= 0 ? 'text-positive' : 'text-negative'}`}>
              {incomeDelta >= 0 ? '+' : '−'}
              {formatMoney(Math.abs(incomeDelta))} ggü. {previousLabel}
            </p>
          </div>
        </div>
      </div>

      <div className="section-title">Top-Ausgaben ({data.months.length} Monate)</div>
      {data.top_categories.length === 0 ? (
        <EmptyState>Noch keine Ausgaben in diesem Zeitraum erfasst.</EmptyState>
      ) : (
        <div className="row-list">
          {data.top_categories.map((c) => (
            <div className="row-item" key={c.id}>
              <div className="row-dot" style={{ background: c.color }} />
              <div className="row-main">
                <span className="row-title">{c.name}</span>
              </div>
              <div className="row-amount num negative">{formatMoney(c.total_spent)}</div>
            </div>
          ))}
        </div>
      )}

      <div className="section-title">Umschlag-Verlauf</div>
      <div className="card">
        <div className="field">
          <label htmlFor="trend-category">Umschlag</label>
          <select id="trend-category" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            {data.categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        {selectedCategory && (
          <TrendChart
            labels={monthLabels}
            series={[{ label: selectedCategory.name, color: selectedCategory.color, values: selectedCategory.spent_by_month.map(Number) }]}
            formatValue={(v) => `CHF ${formatMoney(v)}`}
            caption={`Ausgabenverlauf für ${selectedCategory.name} der letzten ${data.months.length} Monate.`}
          />
        )}
      </div>
    </>
  )
}
