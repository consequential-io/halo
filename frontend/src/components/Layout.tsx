import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

// Consequential Logo Component
const ConsequentialLogo = ({ size = 24 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
    <path d="M8 12C8 10.8954 8.89543 10 10 10H14C15.1046 10 16 10.8954 16 12V28C16 29.1046 15.1046 30 14 30H10C8.89543 30 8 29.1046 8 28V12Z" fill="#9AE65C"/>
    <path d="M24 12C24 10.8954 24.8954 10 26 10H30C31.1046 10 32 10.8954 32 12V28C32 29.1046 31.1046 30 30 30H26C24.8954 30 24 29.1046 24 28V12Z" fill="#9AE65C"/>
    <path d="M4 16C4 14.8954 4.89543 14 6 14H8V26H6C4.89543 26 4 25.1046 4 24V16Z" fill="#9AE65C" opacity="0.6"/>
    <path d="M32 14H34C35.1046 14 36 14.8954 36 16V24C36 25.1046 35.1046 26 34 26H32V14Z" fill="#9AE65C" opacity="0.6"/>
  </svg>
)

// Icons
const AnalyzeIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
  </svg>
)

const RecommendIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
  </svg>
)

const ExecuteIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M13 10V3L4 14h7v7l9-11h-7z"/>
  </svg>
)

const LogoutIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>
  </svg>
)

interface LayoutProps {
  children: React.ReactNode
  tenantName?: string
  sessionId?: string | null
  hasAnalysis?: boolean
  hasRecommendations?: boolean
}

const styles = {
  container: {
    display: 'flex',
    minHeight: '100vh',
    background: '#0A0A0A',
  },
  sidebar: {
    width: '260px',
    background: '#0A0A0A',
    borderRight: '1px solid rgba(255,255,255,0.1)',
    display: 'flex',
    flexDirection: 'column' as const,
    position: 'fixed' as const,
    top: 0,
    left: 0,
    bottom: 0,
    zIndex: 100,
  },
  sidebarHeader: {
    padding: '20px',
    borderBottom: '1px solid rgba(255,255,255,0.1)',
  },
  tenantSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '8px',
  },
  tenantAvatar: {
    width: '36px',
    height: '36px',
    borderRadius: '8px',
    background: '#9AE65C',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '16px',
    fontWeight: 600,
    color: '#0A0A0A',
  },
  tenantName: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#FFFFFF',
  },
  userName: {
    fontSize: '13px',
    color: '#A1A1A1',
    marginLeft: '48px',
  },
  nav: {
    flex: 1,
    padding: '20px 12px',
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    color: '#A1A1A1',
    fontSize: '14px',
    fontWeight: 500,
    marginBottom: '4px',
    transition: 'all 0.2s ease',
    border: 'none',
    background: 'transparent',
    width: '100%',
    textAlign: 'left' as const,
  },
  navItemActive: {
    background: 'rgba(154, 230, 92, 0.1)',
    color: '#9AE65C',
  },
  navItemDisabled: {
    opacity: 0.5,
    cursor: 'not-allowed',
  },
  sidebarFooter: {
    padding: '20px',
    borderTop: '1px solid rgba(255,255,255,0.1)',
  },
  logoutBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 16px',
    borderRadius: '8px',
    cursor: 'pointer',
    color: '#A1A1A1',
    fontSize: '14px',
    fontWeight: 500,
    border: 'none',
    background: 'transparent',
    width: '100%',
    textAlign: 'left' as const,
    transition: 'all 0.2s ease',
  },
  main: {
    flex: 1,
    marginLeft: '260px',
    minHeight: '100vh',
    backgroundImage: `
      linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)
    `,
    backgroundSize: '50px 50px',
  },
  header: {
    padding: '16px 32px',
    borderBottom: '1px solid rgba(255,255,255,0.1)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerLogo: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  logoText: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#FFFFFF',
  },
  content: {
    padding: '32px',
  },
}

export default function Layout({
  children,
  tenantName = 'Demo Account',
  sessionId = null,
  hasAnalysis = false,
  hasRecommendations = false,
}: LayoutProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { logout, user } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const isActive = (path: string) => location.pathname.startsWith(path)

  const navItems = [
    {
      path: '/analyze',
      label: 'Analyze',
      icon: <AnalyzeIcon />,
      enabled: true,
    },
    {
      path: sessionId ? `/recommendations/${sessionId}` : '/recommendations',
      label: 'Recommend',
      icon: <RecommendIcon />,
      enabled: hasAnalysis,
    },
    {
      path: sessionId ? `/execute/${sessionId}` : '/execute',
      label: 'Execute',
      icon: <ExecuteIcon />,
      enabled: hasRecommendations,
    },
  ]

  return (
    <div style={styles.container}>
      {/* Left Sidebar */}
      <aside style={styles.sidebar}>
        <div style={styles.sidebarHeader}>
          <div style={styles.tenantSection}>
            <div style={styles.tenantAvatar}>
              {tenantName.charAt(0).toUpperCase()}
            </div>
            <span style={styles.tenantName}>{tenantName}</span>
          </div>
          <div style={styles.userName}>{user?.email || 'demo@consequential.io'}</div>
        </div>

        <nav style={styles.nav}>
          {navItems.map((item) => (
            <button
              key={item.path}
              style={{
                ...styles.navItem,
                ...(isActive(item.path.split('/')[1] === 'recommendations' ? '/recommendations' :
                    item.path.split('/')[1] === 'execute' ? '/execute' : item.path)
                    ? styles.navItemActive : {}),
                ...(!item.enabled ? styles.navItemDisabled : {}),
              }}
              onClick={() => item.enabled && navigate(item.path)}
              disabled={!item.enabled}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </nav>

        <div style={styles.sidebarFooter}>
          <button
            style={styles.logoutBtn}
            onClick={handleLogout}
            onMouseOver={(e) => { e.currentTarget.style.color = '#FFFFFF' }}
            onMouseOut={(e) => { e.currentTarget.style.color = '#A1A1A1' }}
          >
            <LogoutIcon />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={styles.main}>
        <header style={styles.header}>
          <div style={styles.headerLogo}>
            <ConsequentialLogo size={24} />
            <span style={styles.logoText}>Consequential</span>
          </div>
        </header>
        <div style={styles.content}>
          {children}
        </div>
      </main>
    </div>
  )
}
