import { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface User {
  email: string
  name: string
}

interface AuthContextType {
  isAuthenticated: boolean
  user: User | null
  tenantName: string
  login: (tenantName?: string) => void
  logout: () => void
  setTenant: (name: string) => void
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

function getInitialTenant(): string {
  return localStorage.getItem('agatha_tenant') || 'Demo Account'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(getInitialAuthState)
  const [tenantName, setTenantName] = useState(getInitialTenant)
  const [user] = useState<User>({
    email: 'demo@consequential.io',
    name: 'Demo User',
  })

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('auth') === 'success') {
      setIsAuthenticated(true)
      localStorage.setItem('agatha_auth', 'true')
      window.history.replaceState({}, '', window.location.pathname)
    }
  }, [])

  const login = (tenant?: string) => {
    setIsAuthenticated(true)
    localStorage.setItem('agatha_auth', 'true')
    if (tenant) {
      setTenantName(tenant)
      localStorage.setItem('agatha_tenant', tenant)
    }
  }

  const logout = () => {
    setIsAuthenticated(false)
    localStorage.removeItem('agatha_auth')
    localStorage.removeItem('agatha_tenant')
    localStorage.removeItem('agatha_session')
  }

  const setTenant = (name: string) => {
    setTenantName(name)
    localStorage.setItem('agatha_tenant', name)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, tenantName, login, logout, setTenant }}>
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
