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

export function monthInfo(year: number, month: number): MonthInfo {
  const prev = month === 1 ? { y: year - 1, m: 12 } : { y: year, m: month - 1 }
  const next = month === 12 ? { y: year + 1, m: 1 } : { y: year, m: month + 1 }
  return {
    year,
    month,
    label: `${MONTH_NAMES[month - 1]} ${year}`,
    prevYear: prev.y,
    prevMonth: prev.m,
    nextYear: next.y,
    nextMonth: next.m,
  }
}
