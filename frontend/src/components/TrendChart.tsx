import { useEffect, useRef, useState } from 'react'

interface Series {
  label: string
  color: string
  values: number[]
}

interface Props {
  labels: string[]
  series: Series[]
  caption: string
  formatValue?: (value: number) => string
}

const HEIGHT = 220
const PADDING = 32
const MIN_WIDTH = 320
const DEFAULT_WIDTH = 640

export function TrendChart({ labels, series, caption, formatValue }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(DEFAULT_WIDTH)

  // Breite am tatsächlich verfügbaren Platz messen statt per CSS width:100% zu
  // strecken — sonst würde bei einem breiten Container die ganze SVG inkl.
  // Schrift/Linienstärke proportional mitskalieren und riesig wirken.
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

  if (labels.length === 0 || series.length === 0) return null

  const allValues = series.flatMap((s) => s.values)
  const maxVal = Math.max(...allValues, 0)
  const minVal = Math.min(...allValues, 0)
  const range = maxVal - minVal || 1
  const stepX = labels.length > 1 ? (width - PADDING * 2) / (labels.length - 1) : 0
  const zeroY = HEIGHT - PADDING - ((0 - minVal) / range) * (HEIGHT - PADDING * 2)
  const labelEvery = Math.max(1, Math.ceil(labels.length / 8))
  const fmt = formatValue ?? ((v: number) => v.toFixed(0))

  function pathFor(values: number[]) {
    return values
      .map((v, i) => {
        const x = PADDING + i * stepX
        const y = HEIGHT - PADDING - ((v - minVal) / range) * (HEIGHT - PADDING * 2)
        return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
      })
      .join(' ')
  }

  return (
    <div ref={containerRef}>
      <svg width={width} height={HEIGHT} viewBox={`0 0 ${width} ${HEIGHT}`} role="img" aria-label={caption}>
        <title>{caption}</title>
        <line x1={PADDING} y1={zeroY} x2={width - PADDING} y2={zeroY} stroke="var(--color-border)" />
        {series.map((s) => (
          <path key={s.label} d={pathFor(s.values)} fill="none" stroke={s.color} strokeWidth={2.5} />
        ))}
        {labels.map((text, i) =>
          i % labelEvery === 0 ? (
            <text key={text} x={PADDING + i * stepX} y={HEIGHT - PADDING + 18} textAnchor="middle" className="chart-tooltip">
              {text}
            </text>
          ) : null,
        )}
      </svg>
      <p className="chart-caption">{caption}</p>
      {series.length > 1 && (
        <div className="chart-legend">
          {series.map((s) => (
            <span className="chart-legend-item" key={s.label}>
              <span className="chart-legend-dot" style={{ background: s.color }} />
              {s.label}: {fmt(s.values[s.values.length - 1] ?? 0)}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
