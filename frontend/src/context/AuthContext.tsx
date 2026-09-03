import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import api from '../api/client'
import type { User } from '../api/types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  signup: (username: string, password: string, email?: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function init() {
      try {
        await api.get('/auth/csrf/')
        const res = await api.get<User>('/auth/me/')
        if (!cancelled) setUser(res.data)
      } catch {
        if (!cancelled) setUser(null)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    init()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.post<User>('/auth/login/', { username, password })
    setUser(res.data)
  }, [])

  const signup = useCallback(async (username: string, password: string, email?: string) => {
    const res = await api.post<User>('/auth/signup/', { username, password, email })
    setUser(res.data)
  }, [])

  const logout = useCallback(async () => {
    await api.post('/auth/logout/')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>{children}</AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}
