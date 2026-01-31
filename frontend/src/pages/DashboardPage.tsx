import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { getTenants } from '../api/client'

const styles = {
  container: {
    minHeight: '100vh',
    background: '#f5f5f5',
  },
  header: {
    background: 'white',
    padding: '16px 32px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  logo: {
    fontSize: '24px',
    fontWeight: 700,
    color: '#667eea',
  },
  logoutBtn: {
    background: 'none',
    border: '1px solid #ddd',
    borderRadius: '6px',
    padding: '8px 16px',
    cursor: 'pointer',
  },
  main: {
    maxWidth: '800px',
    margin: '40px auto',
    padding: '0 20px',
  },
  title: {
    fontSize: '28px',
    marginBottom: '8px',
    color: '#1a1a2e',
  },
  subtitle: {
    color: '#666',
    marginBottom: '32px',
  },
  card: {
    background: 'white',
    borderRadius: '12px',
    padding: '32px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: 600,
    marginBottom: '8px',
    color: '#333',
  },
  select: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    borderRadius: '8px',
    border: '1px solid #ddd',
    marginBottom: '24px',
  },
  button: {
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    padding: '14px 32px',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    width: '100%',
  },
  disabledBtn: {
    background: '#ccc',
    cursor: 'not-allowed',
  },
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const [tenants, setTenants] = useState<{ id: string; name: string }[]>([])
  const [selectedTenant, setSelectedTenant] = useState('')

  useEffect(() => {
    async function loadTenants() {
      try {
        const data = await getTenants()
        setTenants(data.tenants)
        if (data.tenants.length > 0) {
          setSelectedTenant(data.tenants[0].id)
        }
      } catch {
        // Default tenants if API fails
        setTenants([
          { id: 'TL', name: 'Third Love' },
          { id: 'WH', name: 'Whispering Homes' },
        ])
        setSelectedTenant('TL')
      }
    }
    loadTenants()
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleAnalyze = () => {
    navigate(`/analyze?tenant=${selectedTenant}`)
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div style={styles.logo}>Ad Spend Agent</div>
        <button style={styles.logoutBtn} onClick={handleLogout}>
          Logout
        </button>
      </header>

      <main style={styles.main}>
        <h1 style={styles.title}>Dashboard</h1>
        <p style={styles.subtitle}>Select a tenant to analyze ad spend anomalies</p>

        <div style={styles.card}>
          <label style={styles.label}>Select Tenant</label>
          <select
            style={styles.select}
            value={selectedTenant}
            onChange={(e) => setSelectedTenant(e.target.value)}
          >
            {tenants.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.id})
              </option>
            ))}
          </select>

          <button
            style={{
              ...styles.button,
              ...(selectedTenant ? {} : styles.disabledBtn),
            }}
            onClick={handleAnalyze}
            disabled={!selectedTenant}
          >
            Run Analysis
          </button>
        </div>
      </main>
    </div>
  )
}
