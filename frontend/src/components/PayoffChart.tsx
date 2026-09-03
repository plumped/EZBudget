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

  return (
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Tilgungsverlauf">
      <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--border)" />
      <path d={areaPath} fill="var(--primary-soft)" stroke="none" />
      <path d={path} fill="none" stroke="var(--primary)" strokeWidth={2.5} />
      {points.map((p, i) =>
        i % labelEvery === 0 ? (
          <text key={data[i].month} x={p.x} y={height - padding + 18} textAnchor="middle" className="chart-tooltip">
            M{data[i].month}
          </text>
        ) : null,
      )}
    </svg>
  )
}
