import { formatMoney } from '../utils/format'

interface Props {
  data: { month: number; total_balance: string }[]
}

export function PayoffChart({ data }: Props) {
  if (data.length === 0) return null

  const width = 640
  const height = 220
  const padding = 32
  const values = data.map((d) => parseFloat(d.total_balance))
  const maxVal = Math.max(...values, 1)
  const stepX = data.length > 1 ? (width - padding * 2) / (data.length - 1) : 0

  const points = data.map((d, i) => ({
    x: padding + i * stepX,
    y: height - padding - (parseFloat(d.total_balance) / maxVal) * (height - padding * 2),
  }))

  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const last = points[points.length - 1]
  const first = points[0]
  const areaPath = `${path} L${last.x.toFixed(1)},${height - padding} L${first.x.toFixed(1)},${height - padding} Z`
  const labelEvery = Math.max(1, Math.ceil(data.length / 8))

  const startBalance = formatMoney(data[0].total_balance)
  const endBalance = formatMoney(data[data.length - 1].total_balance)
  const caption = `Verlauf über ${data.length} ${data.length === 1 ? 'Monat' : 'Monate'}: von CHF ${startBalance} auf CHF ${endBalance} Restschuld.`

  return (
    <>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={caption}>
        <title>{caption}</title>
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--color-border)" />
        <path d={areaPath} fill="var(--color-secondary-soft)" stroke="none" />
        <path d={path} fill="none" stroke="var(--color-secondary)" strokeWidth={2.5} />
        {points.map((p, i) =>
          i % labelEvery === 0 ? (
            <text key={data[i].month} x={p.x} y={height - padding + 18} textAnchor="middle" className="chart-tooltip">
              M{data[i].month}
            </text>
          ) : null,
        )}
      </svg>
      <p className="chart-caption">{caption}</p>
    </>
  )
}
