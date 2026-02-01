import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { getTenants } from '../api/client'

// Consequential Logo Component
const ConsequentialLogo = ({ size = 32 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
    <path d="M8 12C8 10.8954 8.89543 10 10 10H14C15.1046 10 16 10.8954 16 12V28C16 29.1046 15.1046 30 14 30H10C8.89543 30 8 29.1046 8 28V12Z" fill="#9AE65C"/>
    <path d="M24 12C24 10.8954 24.8954 10 26 10H30C31.1046 10 32 10.8954 32 12V28C32 29.1046 31.1046 30 30 30H26C24.8954 30 24 29.1046 24 28V12Z" fill="#9AE65C"/>
    <path d="M4 16C4 14.8954 4.89543 14 6 14H8V26H6C4.89543 26 4 25.1046 4 24V16Z" fill="#9AE65C" opacity="0.6"/>
    <path d="M32 14H34C35.1046 14 36 14.8954 36 16V24C36 25.1046 35.1046 26 34 26H32V14Z" fill="#9AE65C" opacity="0.6"/>
  </svg>
)

const styles = {
  container: {
    minHeight: '100vh',
    background: '#0A0A0A',
    backgroundImage: `
      linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)
    `,
    backgroundSize: '50px 50px',
  },
  header: {
    background: '#0A0A0A',
    borderBottom: '1px solid rgba(255,255,255,0.1)',
    padding: '16px 32px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  logoContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  logoText: {
    fontSize: '20px',
    fontWeight: 600,
    color: '#FFFFFF',
  },
  logoutBtn: {
    background: 'transparent',
    border: '1px solid rgba(255,255,255,0.2)',
    borderRadius: '6px',
    padding: '8px 16px',
    cursor: 'pointer',
    color: '#A1A1A1',
    fontSize: '14px',
    transition: 'all 0.2s ease',
  },
  main: {
    maxWidth: '800px',
    margin: '40px auto',
    padding: '0 20px',
  },
  title: {
    fontSize: '28px',
    marginBottom: '8px',
    color: '#FFFFFF',
    fontWeight: 600,
  },
  subtitle: {
    color: '#A1A1A1',
    marginBottom: '32px',
  },
  card: {
    background: '#1A1A1A',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '12px',
    padding: '32px',
  },
  label: {
    display: 'block',
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '8px',
    color: '#FFFFFF',
  },
  select: {
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    borderRadius: '8px',
    border: '1px solid rgba(255,255,255,0.2)',
    marginBottom: '24px',
    background: '#0A0A0A',
    color: '#FFFFFF',
    cursor: 'pointer',
  },
  button: {
    background: '#9AE65C',
    color: '#0A0A0A',
    border: 'none',
    borderRadius: '8px',
    padding: '14px 32px',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    width: '100%',
    transition: 'all 0.2s ease',
  },
  disabledBtn: {
    background: '#333',
    color: '#666',
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
        <div style={styles.logoContainer}>
          <ConsequentialLogo size={28} />
          <span style={styles.logoText}>Consequential</span>
        </div>
        <button
          style={styles.logoutBtn}
          onClick={handleLogout}
          onMouseOver={(e) => {
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.4)'
            e.currentTarget.style.color = '#FFFFFF'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'
            e.currentTarget.style.color = '#A1A1A1'
          }}
        >
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
            onMouseOver={(e) => {
              if (selectedTenant) e.currentTarget.style.background = '#8BD84E'
            }}
            onMouseOut={(e) => {
              if (selectedTenant) e.currentTarget.style.background = '#9AE65C'
            }}
          >
            Run Analysis
          </button>
        </div>
      </main>
    </div>
  )
}
