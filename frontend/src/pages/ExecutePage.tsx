import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { execute, ExecuteResponse, ExecutionResult } from '../api/client'

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
  summary: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px',
    marginBottom: '24px',
  },
  summaryCard: {
    background: 'white',
    borderRadius: '8px',
    padding: '16px',
    textAlign: 'center' as const,
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  summaryValue: {
    fontSize: '24px',
    fontWeight: 700,
  },
  summaryLabel: {
    fontSize: '12px',
    color: '#666',
    marginTop: '4px',
  },
  card: {
    background: 'white',
    borderRadius: '12px',
    padding: '20px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    marginBottom: '12px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  adInfo: {
    flex: 1,
  },
  adName: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#1a1a2e',
    marginBottom: '4px',
  },
  message: {
    fontSize: '14px',
    color: '#666',
  },
  statusBadge: {
    padding: '6px 16px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: 600,
    textTransform: 'uppercase' as const,
  },
  success: {
    background: '#e8f5e9',
    color: '#2e7d32',
  },
  failed: {
    background: '#fee',
    color: '#c00',
  },
  skipped: {
    background: '#fff3e0',
    color: '#e65100',
  },
  dryRunBanner: {
    background: '#e3f2fd',
    color: '#1565c0',
    padding: '12px 20px',
    borderRadius: '8px',
    marginBottom: '24px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
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
    marginTop: '24px',
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
}

export default function ExecutePage() {
  const navigate = useNavigate()
  const { sessionId } = useParams<{ sessionId: string }>()
  const [searchParams] = useSearchParams()
  const approvedAds = searchParams.get('ads')?.split(',').filter(Boolean) || undefined

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<ExecuteResponse | null>(null)
  const hasExecuted = useRef(false)

  useEffect(() => {
    async function runExecution() {
      if (!sessionId || hasExecuted.current) return
      hasExecuted.current = true
      try {
        setLoading(true)
        const result = await execute({
          session_id: sessionId,
          approved_ad_ids: approvedAds,
          dry_run: true,
        })
        setData(result)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Execution failed')
      } finally {
        setLoading(false)
      }
    }
    runExecution()
  }, [sessionId])

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'success':
        return styles.success
      case 'failed':
        return styles.failed
      default:
        return styles.skipped
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
        <h1 style={styles.title}>Execution Results</h1>
        <p style={styles.subtitle}>Review the results of executed recommendations</p>

        {loading && (
          <div style={styles.loading}>
            <div style={styles.spinner}></div>
            <p>Executing recommendations...</p>
          </div>
        )}

        {error && (
          <div style={{ background: '#fee', color: '#c00', padding: '16px', borderRadius: '8px' }}>
            {error}
          </div>
        )}

        {data && !loading && (
          <>
            {data.summary.dry_run && (
              <div style={styles.dryRunBanner}>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
                </svg>
                <span>
                  <strong>Dry Run Mode</strong> - No actual changes were made. This is a simulation.
                </span>
              </div>
            )}

            <div style={styles.summary}>
              <div style={styles.summaryCard}>
                <div style={{ ...styles.summaryValue, color: '#667eea' }}>
                  {data.summary.total_processed}
                </div>
                <div style={styles.summaryLabel}>Processed</div>
              </div>
              <div style={styles.summaryCard}>
                <div style={{ ...styles.summaryValue, color: '#27ae60' }}>
                  {data.summary.success}
                </div>
                <div style={styles.summaryLabel}>Success</div>
              </div>
              <div style={styles.summaryCard}>
                <div style={{ ...styles.summaryValue, color: '#e74c3c' }}>
                  {data.summary.failed}
                </div>
                <div style={styles.summaryLabel}>Failed</div>
              </div>
              <div style={styles.summaryCard}>
                <div style={{ ...styles.summaryValue, color: '#f39c12' }}>
                  {data.summary.skipped}
                </div>
                <div style={styles.summaryLabel}>Skipped</div>
              </div>
            </div>

            {data.results.map((result: ExecutionResult, index: number) => (
              <div key={index} style={styles.card}>
                <div style={styles.adInfo}>
                  <div style={styles.adName}>{result.ad_name}</div>
                  <div style={styles.message}>{result.message}</div>
                </div>
                <span style={{ ...styles.statusBadge, ...getStatusStyle(result.status) }}>
                  {result.status}
                </span>
              </div>
            ))}

            <button style={styles.button} onClick={() => navigate('/dashboard')}>
              Back to Dashboard
            </button>
          </>
        )}
      </main>
    </div>
  )
}
