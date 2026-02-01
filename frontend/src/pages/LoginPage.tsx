import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { getMetaLoginUrl } from '../api/client'

// Consequential Logo Component - Green C + vertical bars
const ConsequentialLogo = ({ size = 40 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" fill="none">
    {/* C shape (crescent) */}
    <path
      d="M20 4C11.163 4 4 11.163 4 20C4 28.837 11.163 36 20 36C22.5 36 24.8 35.4 26.8 34.3L22 28C21.4 28.3 20.7 28.5 20 28.5C15.3 28.5 11.5 24.7 11.5 20C11.5 15.3 15.3 11.5 20 11.5C20.7 11.5 21.4 11.7 22 12L26.8 5.7C24.8 4.6 22.5 4 20 4Z"
      fill="#9AE65C"
    />
    {/* Two vertical bars */}
    <rect x="28" y="8" width="4" height="24" rx="2" fill="#9AE65C"/>
    <rect x="34" y="12" width="4" height="16" rx="2" fill="#9AE65C"/>
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
    login('Third Love')
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
