import { useEffect, useRef, useState } from 'react'
import { formatMoney, formatMonthLabel } from '../utils/format'

interface Props {
  data: { month: number; date: string | null; total_balance: string }[]
}

const HEIGHT = 220
const PADDING = 32
const MIN_WIDTH = 320
const DEFAULT_WIDTH = 640

export function PayoffChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(DEFAULT_WIDTH)

  // Breite am tatsächlich verfügbaren Platz messen statt per CSS width:100% zu
  // strecken — sonst würde bei einem breiten Container (z.B. volle Fensterbreite)
  // die ganze SVG inkl. Schrift/Linienstärke proportional mitskalieren und riesig wirken.
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      const measured = entries[0]?.contentRect.width
      if (measured) setWidth(Math.max(MIN_WIDTH, Math.round(measured)))
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  if (data.length === 0) return null

  const values = data.map((d) => parseFloat(d.total_balance))
  const maxVal = Math.max(...values, 1)
  const stepX = data.length > 1 ? (width - PADDING * 2) / (data.length - 1) : 0

  const points = data.map((d, i) => ({
    x: PADDING + i * stepX,
    y: HEIGHT - PADDING - (parseFloat(d.total_balance) / maxVal) * (HEIGHT - PADDING * 2),
  }))

  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const last = points[points.length - 1]
  const first = points[0]
  const areaPath = `${path} L${last.x.toFixed(1)},${HEIGHT - PADDING} L${first.x.toFixed(1)},${HEIGHT - PADDING} Z`
  const labelEvery = Math.max(1, Math.ceil(data.length / 8))

  const startBalance = formatMoney(data[0].total_balance)
  const endBalance = formatMoney(data[data.length - 1].total_balance)
  const caption = `Verlauf über ${data.length} ${data.length === 1 ? 'Monat' : 'Monate'}: von CHF ${startBalance} auf CHF ${endBalance} Restschuld.`

  return (
    <div ref={containerRef}>
      <svg width={width} height={HEIGHT} viewBox={`0 0 ${width} ${HEIGHT}`} role="img" aria-label={caption}>
        <title>{caption}</title>
        <line x1={PADDING} y1={HEIGHT - PADDING} x2={width - PADDING} y2={HEIGHT - PADDING} stroke="var(--color-border)" />
        <path d={areaPath} fill="var(--color-secondary-soft)" stroke="none" />
        <path d={path} fill="none" stroke="var(--color-secondary)" strokeWidth={2.5} />
        {points.map((p, i) =>
          i % labelEvery === 0 ? (
            <text key={data[i].month} x={p.x} y={HEIGHT - PADDING + 18} textAnchor="middle" className="chart-tooltip">
              {formatMonthLabel(data[i].date, data[i].month)}
            </text>
          ) : null,
        )}
      </svg>
      <p className="chart-caption">{caption}</p>
    </div>
  )
}
