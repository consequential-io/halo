import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { getMetaLoginUrl } from '../api/client'

// Consequential Logo Component
const ConsequentialLogo = ({ size = 40 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
    <path
      d="M8 12C8 10.8954 8.89543 10 10 10H14C15.1046 10 16 10.8954 16 12V28C16 29.1046 15.1046 30 14 30H10C8.89543 30 8 29.1046 8 28V12Z"
      fill="#9AE65C"
    />
    <path
      d="M24 12C24 10.8954 24.8954 10 26 10H30C31.1046 10 32 10.8954 32 12V28C32 29.1046 31.1046 30 30 30H26C24.8954 30 24 29.1046 24 28V12Z"
      fill="#9AE65C"
    />
    <path
      d="M4 16C4 14.8954 4.89543 14 6 14H8V26H6C4.89543 26 4 25.1046 4 24V16Z"
      fill="#9AE65C"
      opacity="0.6"
    />
    <path
      d="M32 14H34C35.1046 14 36 14.8954 36 16V24C36 25.1046 35.1046 26 34 26H32V14Z"
      fill="#9AE65C"
      opacity="0.6"
    />
  </svg>
)

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    background: '#0A0A0A',
    backgroundImage: `
      linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
    `,
    backgroundSize: '50px 50px',
    padding: '20px',
  },
  card: {
    background: '#1A1A1A',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '16px',
    padding: '48px',
    textAlign: 'center' as const,
    maxWidth: '420px',
    width: '100%',
  },
  logoContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    marginBottom: '24px',
  },
  logoText: {
    fontSize: '24px',
    fontWeight: 600,
    color: '#FFFFFF',
  },
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    background: 'rgba(154, 230, 92, 0.1)',
    border: '1px solid rgba(154, 230, 92, 0.3)',
    borderRadius: '20px',
    padding: '6px 14px',
    fontSize: '12px',
    fontWeight: 500,
    color: '#9AE65C',
    marginBottom: '20px',
  },
  title: {
    fontSize: '32px',
    fontWeight: 700,
    marginBottom: '8px',
    color: '#FFFFFF',
  },
  subtitle: {
    fontSize: '16px',
    color: '#A1A1A1',
    marginBottom: '32px',
  },
  facebookButton: {
    background: 'transparent',
    color: '#4267B2',
    border: '1px solid #4267B2',
    borderRadius: '8px',
    padding: '14px 28px',
    fontSize: '16px',
    fontWeight: 500,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    width: '100%',
    marginBottom: '16px',
    transition: 'all 0.2s ease',
  },
  demoButton: {
    background: '#9AE65C',
    color: '#0A0A0A',
    border: 'none',
    borderRadius: '8px',
    padding: '14px 28px',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    width: '100%',
    transition: 'all 0.2s ease',
  },
  divider: {
    margin: '20px 0',
    color: '#666',
    fontSize: '14px',
  },
}

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()

  const handleFacebookLogin = async () => {
    try {
      const { oauth_url } = await getMetaLoginUrl()
      if (oauth_url) {
        window.location.href = oauth_url
      } else {
        handleDemoLogin()
      }
    } catch {
      handleDemoLogin()
    }
  }

  const handleDemoLogin = () => {
    login('Demo Account')
    navigate('/analyze')
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.logoContainer}>
          <ConsequentialLogo size={36} />
          <span style={styles.logoText}>Consequential</span>
        </div>

        <div style={styles.badge}>
          <span>⚡</span>
          <span>Powered by AI Agents</span>
        </div>

        <h1 style={styles.title}>Ad Spend Agent</h1>
        <p style={styles.subtitle}>AI-Powered Ad Spend Optimization</p>

        <button
          style={styles.facebookButton}
          onClick={handleFacebookLogin}
          onMouseOver={(e) => {
            e.currentTarget.style.background = 'rgba(66, 103, 178, 0.1)'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.background = 'transparent'
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="#4267B2">
            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
          </svg>
          Continue with Facebook
        </button>

        <div style={styles.divider}>or</div>

        <button
          style={styles.demoButton}
          onClick={handleDemoLogin}
          onMouseOver={(e) => {
            e.currentTarget.style.background = '#8BD84E'
          }}
          onMouseOut={(e) => {
            e.currentTarget.style.background = '#9AE65C'
          }}
        >
          Continue with Demo Mode
        </button>
      </div>
    </div>
  )
}
