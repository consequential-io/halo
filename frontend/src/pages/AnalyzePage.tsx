import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { analyze, AnalyzeResponse } from '../api/client'

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
    marginBottom: '24px',
  },
  formGroup: {
    marginBottom: '20px',
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
  },
  dateRangeGroup: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: '16px',
    marginBottom: '24px',
  },
  dateRangeBtn: {
    padding: '12px 16px',
    fontSize: '14px',
    borderRadius: '8px',
    border: '2px solid #ddd',
    background: 'white',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  dateRangeBtnActive: {
    borderColor: '#667eea',
    background: '#f0f4ff',
    color: '#667eea',
    fontWeight: 600,
  },
  loading: {
    textAlign: 'center' as const,
    padding: '60px 0',
  },
  spinner: {
    width: '48px',
    height: '48px',
    border: '4px solid #f3f3f3',
    borderTop: '4px solid #667eea',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 16px',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '20px',
    marginBottom: '24px',
  },
  stat: {
    textAlign: 'center' as const,
    padding: '16px',
    background: '#f9f9f9',
    borderRadius: '8px',
  },
  statValue: {
    fontSize: '32px',
    fontWeight: 700,
    color: '#667eea',
  },
  statLabel: {
    fontSize: '14px',
    color: '#666',
    marginTop: '4px',
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
  buttonDisabled: {
    background: '#ccc',
    cursor: 'not-allowed',
  },
  error: {
    background: '#fee',
    color: '#c00',
    padding: '16px',
    borderRadius: '8px',
    marginBottom: '16px',
  },
  sourceToggle: {
    display: 'flex',
    gap: '12px',
    marginBottom: '24px',
  },
  sourceBtn: {
    flex: 1,
    padding: '10px 16px',
    fontSize: '14px',
    borderRadius: '8px',
    border: '2px solid #ddd',
    background: 'white',
    cursor: 'pointer',
  },
  sourceBtnActive: {
    borderColor: '#667eea',
    background: '#667eea',
    color: 'white',
  },
}

const DATE_RANGES = [
  { label: 'Last 7 Days', days: 7 },
  { label: 'Last 14 Days', days: 14 },
  { label: 'Last 30 Days', days: 30 },
  { label: 'Last 60 Days', days: 60 },
  { label: 'Last 90 Days', days: 90 },
]

export default function AnalyzePage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const tenant = searchParams.get('tenant') || 'TL'

  const [days, setDays] = useState(30)
  const [source, setSource] = useState<'bq' | 'fixture'>('bq')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AnalyzeResponse | null>(null)

  const runAnalysis = async () => {
    try {
      setLoading(true)
      setError(null)
      setResult(null)
      const data = await analyze({ tenant, days, source })
      setResult(data)
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
    <div style={styles.container}>
      <style>
        {`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}
      </style>

      <header style={styles.header}>
        <div style={styles.logo} onClick={() => navigate('/dashboard')}>
          Ad Spend Agent
        </div>
      </header>

      <main style={styles.main}>
        <h1 style={styles.title}>Analysis: {tenant}</h1>
        <p style={styles.subtitle}>Configure and run anomaly detection on ad spend data</p>

        {!result && !loading && (
          <div style={styles.card}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Data Source</label>
              <div style={styles.sourceToggle}>
                <button
                  style={{
                    ...styles.sourceBtn,
                    ...(source === 'bq' ? styles.sourceBtnActive : {}),
                  }}
                  onClick={() => setSource('bq')}
                >
                  BigQuery (Live)
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

            <div style={styles.formGroup}>
              <label style={styles.label}>Date Range</label>
              <div style={styles.dateRangeGroup}>
                {DATE_RANGES.map((range) => (
                  <button
                    key={range.days}
                    style={{
                      ...styles.dateRangeBtn,
                      ...(days === range.days ? styles.dateRangeBtnActive : {}),
                    }}
                    onClick={() => setDays(range.days)}
                  >
                    {range.label}
                  </button>
                ))}
              </div>
            </div>

            <button style={styles.button} onClick={runAnalysis}>
              Run Analysis
            </button>
          </div>
        )}

        {loading && (
          <div style={styles.card}>
            <div style={styles.loading}>
              <div style={styles.spinner}></div>
              <p>Analyzing {days} days of ad spend data from {source === 'bq' ? 'BigQuery' : 'sample data'}...</p>
            </div>
          </div>
        )}

        {error && (
          <div style={styles.card}>
            <div style={styles.error}>{error}</div>
            <button style={styles.button} onClick={() => { setError(null); setResult(null); }}>
              Try Again
            </button>
          </div>
        )}

        {result && !loading && (
          <div style={styles.card}>
            <div style={styles.statsGrid}>
              <div style={styles.stat}>
                <div style={styles.statValue}>{result.total_ads}</div>
                <div style={styles.statLabel}>Total Ads</div>
              </div>
              <div style={styles.stat}>
                <div style={{ ...styles.statValue, color: result.anomalies_found > 0 ? '#e74c3c' : '#27ae60' }}>
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
              <button style={styles.button} onClick={handleGetRecommendations}>
                Get Recommendations
              </button>
            )}

            {result.anomalies_found === 0 && (
              <>
                <div style={{ textAlign: 'center', padding: '20px', color: '#27ae60', marginBottom: '16px' }}>
                  No anomalies detected. Your ads are performing well.
                </div>
                <button
                  style={{ ...styles.button, background: '#6c757d' }}
                  onClick={() => setResult(null)}
                >
                  Run New Analysis
                </button>
              </>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
