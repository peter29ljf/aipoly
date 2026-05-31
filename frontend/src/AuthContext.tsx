import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

export type Role = 'admin' | 'guest'

interface AuthState {
  username: string
  role: Role
}

interface AuthContextValue {
  auth: AuthState | null
  login: (username: string, password: string) => boolean
  logout: () => void
  isGuest: boolean
  isAdmin: boolean
}

const ACCOUNTS: Record<string, { password: string; role: Role }> = {
  admin: { password: '12340987', role: 'admin' },
  guest: { password: 'guest',    role: 'guest'  },
}

const STORAGE_KEY = 'aipm_auth'

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })

  useEffect(() => {
    if (auth) localStorage.setItem(STORAGE_KEY, JSON.stringify(auth))
    else localStorage.removeItem(STORAGE_KEY)
  }, [auth])

  function login(username: string, password: string): boolean {
    const account = ACCOUNTS[username.trim().toLowerCase()]
    if (account && account.password === password) {
      setAuth({ username: username.trim().toLowerCase(), role: account.role })
      return true
    }
    return false
  }

  function logout() {
    setAuth(null)
  }

  return (
    <AuthContext.Provider value={{
      auth,
      login,
      logout,
      isGuest: auth?.role === 'guest',
      isAdmin: auth?.role === 'admin',
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
