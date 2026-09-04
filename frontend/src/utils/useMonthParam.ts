import { useSearchParams } from 'react-router-dom'
import { useSettings } from '../context/SettingsContext'
import { monthInfo, type MonthInfo } from './month'

export function useMonthParam(): MonthInfo & { setMonth: (year: number, month: number) => void } {
  const [params, setParams] = useSearchParams()
  const { monthStartDay } = useSettings()
  const today = new Date()
  const year = Number(params.get('year')) || today.getFullYear()
  const month = Number(params.get('month')) || today.getMonth() + 1
  const info = monthInfo(year, month, monthStartDay)

  const setMonth = (y: number, m: number) => {
    const next = new URLSearchParams(params)
    next.set('year', String(y))
    next.set('month', String(m))
    setParams(next)
  }

  return { ...info, setMonth }
}
