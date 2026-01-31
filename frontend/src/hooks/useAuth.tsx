import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface AuthContextType {
  isAuthenticated: boolean
  login: () => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

// Check auth synchronously to avoid race condition
function getInitialAuthState(): boolean {
  const params = new URLSearchParams(window.location.search)
  if (params.get('auth') === 'success') {
    localStorage.setItem('agatha_auth', 'true')
    window.history.replaceState({}, '', window.location.pathname)
    return true
  }
  return localStorage.getItem('agatha_auth') === 'true'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(getInitialAuthState)

  useEffect(() => {
    // Re-check in case of any updates
    const params = new URLSearchParams(window.location.search)
    if (params.get('auth') === 'success') {
      setIsAuthenticated(true)
      localStorage.setItem('agatha_auth', 'true')
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  const login = () => {
    setIsAuthenticated(true)
    localStorage.setItem('agatha_auth', 'true')
  }

  const logout = () => {
    setIsAuthenticated(false)
    localStorage.removeItem('agatha_auth')
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
