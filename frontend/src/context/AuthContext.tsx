import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import type { AuthUser } from '../api'
import { authMe } from '../api'

interface AuthState {
  user: AuthUser | null
  token: string | null
  loading: boolean
  login: (user: AuthUser) => void
  logout: () => void
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  loading: true,
  login: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('catan_token'))
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (token) {
      authMe(token)
        .then(u => {
          setUser(u)
          setLoading(false)
        })
        .catch(() => {
          localStorage.removeItem('catan_token')
          setToken(null)
          setLoading(false)
        })
    } else {
      setLoading(false)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback((u: AuthUser) => {
    setUser(u)
    setToken(u.token)
    localStorage.setItem('catan_token', u.token)
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('catan_token')
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  return useContext(AuthContext)
}
