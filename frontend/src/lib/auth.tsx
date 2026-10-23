import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, tokenStore } from './api'
import type { User } from './types'

type Ctx = { user: User | null; loading: boolean; login: (e: string, p: string) => Promise<void>; register: (e: string, p: string, n: string) => Promise<void>; logout: () => void; refresh: () => Promise<void>; setUser: (u: User) => void }
const AuthCtx = createContext<Ctx>(null as unknown as Ctx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const refresh = useCallback(async () => {
    if (!tokenStore.get()) { setUser(null); setLoading(false); return }
    try { setUser(await api<User>('/users/me')) } catch { setUser(null) } finally { setLoading(false) }
  }, [])
  useEffect(() => { refresh() }, [refresh])
  const login = async (email: string, password: string) => {
    const r = await api<{ access_token: string }>('/auth/login', { method: 'POST', json: { email, password } })
    tokenStore.set(r.access_token); await refresh()
  }
  const register = async (email: string, password: string, name: string) => {
    const r = await api<{ access_token: string }>('/auth/register', { method: 'POST', json: { email, password, name } })
    tokenStore.set(r.access_token); await refresh()
  }
  const logout = () => { tokenStore.set(null); setUser(null) }
  return <AuthCtx.Provider value={{ user, loading, login, register, logout, refresh, setUser }}>{children}</AuthCtx.Provider>
}
export const useAuth = () => useContext(AuthCtx)
