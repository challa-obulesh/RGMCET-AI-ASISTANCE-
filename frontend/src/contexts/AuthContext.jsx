import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from '../services/api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const hydrate = useCallback(async () => {
    const token = localStorage.getItem('rgmcet-token')
    if (!token) { setLoading(false); return }
    try {
      const profile = await api.me()
      setUser(profile)
    } catch {
      localStorage.removeItem('rgmcet-token')
      localStorage.removeItem('rgmcet-user')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { hydrate() }, [hydrate])

  const login = useCallback(async (email, password) => {
    const data = await api.login({ email, password })
    localStorage.setItem('rgmcet-token', data.access_token)
    const profile = await api.me()
    setUser(profile)
    return profile
  }, [])

  const register = useCallback(async (name, email, password, role = 'student', professor_id = null) => {
    const data = await api.register({ name, email, password, role, professor_id })
    if (data.approval_status === 'APPROVED') {
      localStorage.setItem('rgmcet-token', data.access_token)
      try {
        const profile = await api.me()
        setUser(profile)
        return profile
      } catch {
        return data
      }
    }
    return data
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('rgmcet-token')
    localStorage.removeItem('rgmcet-user')
    localStorage.removeItem('rgmcet-recent-chats')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
