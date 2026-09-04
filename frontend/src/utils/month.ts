export interface MonthInfo {
  year: number
  month: number
  label: string
  prevYear: number
  prevMonth: number
  nextYear: number
  nextMonth: number
}

const MONTH_NAMES = [
  'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
  'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember',
]

function daysInMonth(year: number, month: number): number {
  return new Date(year, month, 0).getDate()
}

function periodStart(year: number, month: number, startDay: number): Date {
  if (startDay <= 1) return new Date(year, month - 1, 1)
  return new Date(year, month - 1, Math.min(startDay, daysInMonth(year, month)))
}

function formatShort(d: Date): string {
  return d.toLocaleDateString('de-CH', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

/** monthStartDay: Tag im Monat, an dem der Budget-Monat beginnt (1 = Kalendermonat). */
export function monthInfo(year: number, month: number, monthStartDay = 1): MonthInfo {
  const prev = month === 1 ? { y: year - 1, m: 12 } : { y: year, m: month - 1 }
  const next = month === 12 ? { y: year + 1, m: 1 } : { y: year, m: month + 1 }

  let label = `${MONTH_NAMES[month - 1]} ${year}`
  if (monthStartDay > 1) {
    const start = periodStart(year, month, monthStartDay)
    const nextStart = periodStart(next.y, next.m, monthStartDay)
    const end = new Date(nextStart)
    end.setDate(end.getDate() - 1)
    label = `${formatShort(start)} – ${formatShort(end)}`
  }

  return {
    year,
    month,
    label,
    prevYear: prev.y,
    prevMonth: prev.m,
    nextYear: next.y,
    nextMonth: next.m,
  }
}
