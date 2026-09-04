import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import api from '../api/client'
import { useAuth } from './AuthContext'

interface BudgetSettingsResponse {
  month_start_day: number
}

interface SettingsContextValue {
  monthStartDay: number
  loading: boolean
  updateMonthStartDay: (value: number) => Promise<void>
}

const SettingsContext = createContext<SettingsContextValue | undefined>(undefined)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [monthStartDay, setMonthStartDay] = useState(1)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) {
      setLoading(false)
      return
    }
    let cancelled = false
    api
      .get<BudgetSettingsResponse>('/settings/')
      .then((res) => {
        if (!cancelled) setMonthStartDay(res.data.month_start_day)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [user])

  const updateMonthStartDay = useCallback(async (value: number) => {
    const res = await api.put<BudgetSettingsResponse>('/settings/', { month_start_day: value })
    setMonthStartDay(res.data.month_start_day)
  }, [])

  return (
    <SettingsContext.Provider value={{ monthStartDay, loading, updateMonthStartDay }}>
      {children}
    </SettingsContext.Provider>
  )
}

export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext)
  if (!ctx) {
    throw new Error('useSettings must be used within a SettingsProvider')
  }
  return ctx
}
