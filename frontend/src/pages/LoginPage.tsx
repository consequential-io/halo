import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { getMetaLoginUrl } from '../api/client'

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column' as const,
    alignItems: 'center',
    justifyContent: 'center',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    padding: '20px',
  },
  card: {
    background: 'white',
    borderRadius: '16px',
    padding: '48px',
    boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
    textAlign: 'center' as const,
    maxWidth: '400px',
    width: '100%',
  },
  title: {
    fontSize: '32px',
    fontWeight: 700,
    marginBottom: '8px',
    color: '#1a1a2e',
  },
  subtitle: {
    fontSize: '16px',
    color: '#666',
    marginBottom: '32px',
  },
  button: {
    background: '#1877f2',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    padding: '14px 28px',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    width: '100%',
    marginBottom: '16px',
  },
  demoButton: {
    background: '#4CAF50',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    padding: '14px 28px',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    width: '100%',
  },
  divider: {
    margin: '20px 0',
    color: '#999',
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
        // No OAuth configured, use demo mode
        handleDemoLogin()
      }
    } catch {
      // If API fails, use demo mode
      handleDemoLogin()
    }
  }

  const handleDemoLogin = () => {
    login()
    navigate('/dashboard')
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Ad Spend Agent</h1>
        <p style={styles.subtitle}>AI-Powered Ad Spend Optimization</p>

        <button style={styles.button} onClick={handleFacebookLogin}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
          </svg>
          Login with Facebook
        </button>

        <div style={styles.divider}>or</div>

        <button style={styles.demoButton} onClick={handleDemoLogin}>
          Continue with Demo Mode
        </button>
      </div>
    </div>
  )
}
