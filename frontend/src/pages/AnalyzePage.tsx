import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyze, AnalyzeResponse, trackEvent } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import Layout from '../components/Layout'
import DateRangePicker from '../components/DateRangePicker'

const styles = {
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '32px',
  },
  welcome: {
    fontSize: '28px',
    fontWeight: 600,
    color: '#FFFFFF',
    marginBottom: '8px',
  },
  subtitle: {
    color: '#A1A1A1',
    fontSize: '15px',
  },
  card: {
    background: '#1A1A1A',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '12px',
    padding: '24px',
    marginBottom: '24px',
  },
  formRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    fontSize: '14px',
    fontWeight: 500,
    color: '#FFFFFF',
    marginBottom: '8px',
  },
  sourceToggle: {
    display: 'flex',
    gap: '8px',
  },
  sourceBtn: {
    padding: '10px 20px',
    fontSize: '14px',
    fontWeight: 500,
    borderRadius: '8px',
    border: '1px solid rgba(255,255,255,0.2)',
    background: 'transparent',
    color: '#A1A1A1',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  sourceBtnActive: {
    borderColor: '#9AE65C',
    background: '#9AE65C',
    color: '#0A0A0A',
  },
  analyzeBtn: {
    background: '#9AE65C',
    color: '#0A0A0A',
    border: 'none',
    borderRadius: '8px',
    padding: '12px 32px',
    fontSize: '15px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  loading: {
    textAlign: 'center' as const,
    padding: '60px 0',
  },
  spinner: {
    width: '48px',
    height: '48px',
    border: '3px solid #333',
    borderTop: '3px solid #9AE65C',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 16px',
  },
  loadingText: {
    color: '#A1A1A1',
    fontSize: '15px',
  },
  resultsCard: {
    background: '#1A1A1A',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '12px',
    padding: '32px',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '16px',
    marginBottom: '24px',
  },
  stat: {
    textAlign: 'center' as const,
    padding: '24px',
    background: '#0A0A0A',
    borderRadius: '12px',
    border: '1px solid rgba(255,255,255,0.1)',
  },
  statValue: {
    fontSize: '48px',
    fontWeight: 700,
    color: '#9AE65C',
    lineHeight: 1,
    marginBottom: '8px',
  },
  statLabel: {
    fontSize: '14px',
    color: '#A1A1A1',
  },
  getRecsBtn: {
    background: '#9AE65C',
    color: '#0A0A0A',
    border: 'none',
    borderRadius: '8px',
    padding: '16px',
    fontSize: '16px',
    fontWeight: 600,
    cursor: 'pointer',
    width: '100%',
    transition: 'all 0.2s ease',
  },
  successMessage: {
    textAlign: 'center' as const,
    padding: '20px',
    color: '#9AE65C',
    marginBottom: '16px',
  },
  secondaryBtn: {
    background: 'transparent',
    color: '#A1A1A1',
    border: '1px solid rgba(255,255,255,0.2)',
    borderRadius: '8px',
    padding: '14px',
    fontSize: '15px',
    fontWeight: 500,
    cursor: 'pointer',
    width: '100%',
  },
  error: {
    background: 'rgba(255, 107, 107, 0.1)',
    border: '1px solid rgba(255, 107, 107, 0.3)',
    color: '#FF6B6B',
    padding: '16px',
    borderRadius: '8px',
    marginBottom: '16px',
    textAlign: 'center' as const,
  },
}

export default function AnalyzePage() {
  const navigate = useNavigate()
  const { tenantName } = useAuth()

  // Date range state - default to last 14 days
  const [endDate, setEndDate] = useState(() => new Date())
  const [startDate, setStartDate] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 13)
    return d
  })

  const [source, setSource] = useState<'bq' | 'fixture'>('bq')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)

  // Track page view (successful login)
  useEffect(() => {
    trackEvent('page_analyze')
  }, [])

  // Load any existing session
  useEffect(() => {
    const savedSession = localStorage.getItem('agatha_session')
    if (savedSession) {
      setSessionId(savedSession)
    }
  }, [])

  const days = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)) + 1

  const handleDateChange = (start: Date, end: Date) => {
    setStartDate(start)
    setEndDate(end)
  }

  const runAnalysis = async () => {
    try {
      setLoading(true)
      setError(null)
      setResult(null)
      // Use TL as default tenant ID for the API
      const data = await analyze({ tenant: 'TL', days, source })
      setResult(data)
      setSessionId(data.session_id)
      localStorage.setItem('agatha_session', data.session_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  const handleGetRecommendations = () => {
    if (result) {
      navigate(`/recommendations/${result.session_id}`)
    }
  }

  return (
    <Layout
      tenantName={tenantName}
      sessionId={sessionId}
      hasAnalysis={!!result && result.anomalies_found > 0}
    >
      <style>
        {`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}
      </style>

      {/* Header Row */}
      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.welcome}>Welcome to Consequential.io</h1>
          <p style={styles.subtitle}>Identify opportunities to improve your Ad Performance</p>
        </div>
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onChange={handleDateChange}
        />
      </div>

      {/* Analysis Form */}
      {!result && !loading && (
        <div style={styles.card}>
          <div style={styles.formRow}>
            <div>
              <div style={styles.label}>Data Source</div>
              <div style={styles.sourceToggle}>
                <button
                  style={{
                    ...styles.sourceBtn,
                    ...(source === 'bq' ? styles.sourceBtnActive : {}),
                  }}
                  onClick={() => setSource('bq')}
                >
                  Live Data
                </button>
                <button
                  style={{
                    ...styles.sourceBtn,
                    ...(source === 'fixture' ? styles.sourceBtnActive : {}),
                  }}
                  onClick={() => setSource('fixture')}
                >
                  Sample Data
                </button>
              </div>
            </div>
            <button
              style={styles.analyzeBtn}
              onClick={runAnalysis}
              onMouseOver={(e) => { e.currentTarget.style.background = '#8BD84E' }}
              onMouseOut={(e) => { e.currentTarget.style.background = '#9AE65C' }}
            >
              Analyze
            </button>
          </div>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={styles.card}>
          <div style={styles.loading}>
            <div style={styles.spinner}></div>
            <p style={styles.loadingText}>
              Analyzing {days} days of Acquisition metrics...
            </p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div style={styles.card}>
          <div style={styles.error}>{error}</div>
          <button
            style={styles.secondaryBtn}
            onClick={() => { setError(null); setResult(null); }}
          >
            Try Again
          </button>
        </div>
      )}

      {/* Results */}
      {result && !loading && (
        <div style={styles.resultsCard}>
          <div style={styles.statsGrid}>
            <div style={styles.stat}>
              <div style={styles.statValue}>{result.total_ads}</div>
              <div style={styles.statLabel}>Total Ads</div>
            </div>
            <div style={styles.stat}>
              <div style={{ ...styles.statValue, color: result.anomalies_found > 0 ? '#FF6B6B' : '#9AE65C' }}>
                {result.anomalies_found}
              </div>
              <div style={styles.statLabel}>Anomalies Found</div>
            </div>
            <div style={styles.stat}>
              <div style={styles.statValue}>{days}</div>
              <div style={styles.statLabel}>Days Analyzed</div>
            </div>
          </div>

          {result.anomalies_found > 0 && (
            <button
              style={styles.getRecsBtn}
              onClick={handleGetRecommendations}
              onMouseOver={(e) => { e.currentTarget.style.background = '#8BD84E' }}
              onMouseOut={(e) => { e.currentTarget.style.background = '#9AE65C' }}
            >
              Get Recommendations
            </button>
          )}

          {result.anomalies_found === 0 && (
            <>
              <div style={styles.successMessage}>
                No anomalies detected. Your ads are performing well.
              </div>
              <button
                style={styles.secondaryBtn}
                onClick={() => setResult(null)}
              >
                Run New Analysis
              </button>
            </>
          )}
        </div>
      )}
    </Layout>
  )
}
