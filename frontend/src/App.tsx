import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './hooks/useAuth'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import AnalyzePage from './pages/AnalyzePage'
import RecommendationsPage from './pages/RecommendationsPage'
import ExecutePage from './pages/ExecutePage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/analyze"
        element={
          <ProtectedRoute>
            <AnalyzePage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/recommendations/:sessionId"
        element={
          <ProtectedRoute>
            <RecommendationsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/execute/:sessionId"
        element={
          <ProtectedRoute>
            <ExecutePage />
          </ProtectedRoute>
        }
      />
      <Route path="/" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
