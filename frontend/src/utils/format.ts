export function formatMoney(value: string | number): string {
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (Number.isNaN(num)) return '0.00'
  return num.toLocaleString('de-CH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function moneyClass(value: string | number): 'positive' | 'negative' {
  const num = typeof value === 'string' ? parseFloat(value) : value
  return num < 0 ? 'negative' : 'positive'
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString('de-CH', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

export function formatMonthLabel(date: string | null | undefined, monthIndex: number): string {
  if (!date) return `M${monthIndex}`
  const d = new Date(date)
  if (Number.isNaN(d.getTime())) return `M${monthIndex}`
  return d.toLocaleDateString('de-CH', { month: 'short', year: '2-digit' })
}
