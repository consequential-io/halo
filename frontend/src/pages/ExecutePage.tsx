import { useState, useEffect, useRef } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { execute, ExecuteResponse, ExecutionResult } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import Layout from '../components/Layout'

const styles = {
  headerRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '32px',
  },
  title: {
    fontSize: '28px',
    fontWeight: 600,
    color: '#FFFFFF',
    marginBottom: '8px',
  },
  subtitle: {
    color: '#A1A1A1',
    fontSize: '15px',
  },
  summary: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '16px',
    marginBottom: '24px',
  },
  summaryCard: {
    background: '#1A1A1A',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '12px',
    padding: '20px',
    textAlign: 'center' as const,
  },
  summaryValue: {
    fontSize: '28px',
    fontWeight: 700,
  },
  summaryLabel: {
    fontSize: '12px',
    color: '#A1A1A1',
    marginTop: '4px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  dryRunBanner: {
    background: 'rgba(100, 181, 246, 0.1)',
    border: '1px solid rgba(100, 181, 246, 0.3)',
    color: '#64B5F6',
    padding: '16px 20px',
    borderRadius: '12px',
    marginBottom: '24px',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  card: {
    background: '#1A1A1A',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '12px',
    padding: '20px',
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
    color: '#FFFFFF',
    marginBottom: '4px',
  },
  message: {
    fontSize: '14px',
    color: '#A1A1A1',
  },
  statusBadge: {
    padding: '8px 16px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  success: {
    background: 'rgba(154, 230, 92, 0.15)',
    color: '#9AE65C',
  },
  failed: {
    background: 'rgba(255, 107, 107, 0.15)',
    color: '#FF6B6B',
  },
  skipped: {
    background: 'rgba(255, 183, 77, 0.15)',
    color: '#FFB74D',
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
    marginTop: '24px',
    transition: 'all 0.2s ease',
  },
  loading: {
    textAlign: 'center' as const,
    padding: '80px 0',
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
  error: {
    background: 'rgba(255, 107, 107, 0.1)',
    border: '1px solid rgba(255, 107, 107, 0.3)',
    color: '#FF6B6B',
    padding: '20px',
    borderRadius: '12px',
    textAlign: 'center' as const,
  },
}

export default function ExecutePage() {
  const navigate = useNavigate()
  const { sessionId } = useParams<{ sessionId: string }>()
  const [searchParams] = useSearchParams()
  const approvedAds = searchParams.get('ads')?.split(',').filter(Boolean) || undefined
  const { tenantName } = useAuth()

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
    <Layout
      tenantName={tenantName}
      sessionId={sessionId}
      hasAnalysis={true}
      hasRecommendations={true}
    >
      <style>
        {`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}
      </style>

      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.title}>Execution Results</h1>
          <p style={styles.subtitle}>Review the results of executed recommendations</p>
        </div>
      </div>

      {loading && (
        <div style={styles.loading}>
          <div style={styles.spinner}></div>
          <p style={{ color: '#A1A1A1' }}>Executing recommendations...</p>
        </div>
      )}

      {error && (
        <div style={styles.error}>{error}</div>
      )}

      {data && !loading && (
        <>
          {data.summary.dry_run && (
            <div style={styles.dryRunBanner}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z" />
              </svg>
              <div>
                <strong>Dry Run Mode</strong>
                <div style={{ fontSize: '14px', opacity: 0.8, marginTop: '2px' }}>
                  No actual changes were made. This is a simulation.
                </div>
              </div>
            </div>
          )}

          <div style={styles.summary}>
            <div style={styles.summaryCard}>
              <div style={{ ...styles.summaryValue, color: '#9AE65C' }}>
                {data.summary.total_processed}
              </div>
              <div style={styles.summaryLabel}>Processed</div>
            </div>
            <div style={styles.summaryCard}>
              <div style={{ ...styles.summaryValue, color: '#9AE65C' }}>
                {data.summary.success}
              </div>
              <div style={styles.summaryLabel}>Success</div>
            </div>
            <div style={styles.summaryCard}>
              <div style={{ ...styles.summaryValue, color: '#FF6B6B' }}>
                {data.summary.failed}
              </div>
              <div style={styles.summaryLabel}>Failed</div>
            </div>
            <div style={styles.summaryCard}>
              <div style={{ ...styles.summaryValue, color: '#FFB74D' }}>
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

          <button
            style={styles.button}
            onClick={() => navigate('/analyze')}
            onMouseOver={(e) => { e.currentTarget.style.background = '#8BD84E' }}
            onMouseOut={(e) => { e.currentTarget.style.background = '#9AE65C' }}
          >
            Start New Analysis
          </button>
        </>
      )}
    </Layout>
  )
}
