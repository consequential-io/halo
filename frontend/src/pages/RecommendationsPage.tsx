import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getRecommendations, Recommendation, RecommendResponse } from '../api/client'

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
    maxWidth: '1000px',
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
    padding: '24px',
    boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
    marginBottom: '16px',
    display: 'flex',
    alignItems: 'flex-start',
    gap: '16px',
  },
  checkbox: {
    width: '24px',
    height: '24px',
    cursor: 'pointer',
    marginTop: '4px',
  },
  cardContent: {
    flex: 1,
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '8px',
  },
  adName: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#1a1a2e',
  },
  badge: {
    padding: '4px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: 600,
    textTransform: 'uppercase' as const,
  },
  actionBadge: {
    pause: { background: '#fee', color: '#c00' },
    reduce: { background: '#fff3e0', color: '#e65100' },
    scale: { background: '#e8f5e9', color: '#2e7d32' },
    refresh_creative: { background: '#e3f2fd', color: '#1565c0' },
  },
  priorityBadge: {
    critical: { background: '#fee', color: '#c00' },
    high: { background: '#fff3e0', color: '#e65100' },
    medium: { background: '#fff9c4', color: '#f57f17' },
    low: { background: '#e8f5e9', color: '#2e7d32' },
  },
  reasoning: {
    fontSize: '14px',
    color: '#666',
    marginBottom: '12px',
  },
  details: {
    display: 'flex',
    gap: '24px',
    fontSize: '14px',
    color: '#333',
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
    position: 'fixed' as const,
    bottom: '24px',
    right: '24px',
    boxShadow: '0 4px 12px rgba(102, 126, 234, 0.4)',
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

export default function RecommendationsPage() {
  const navigate = useNavigate()
  const { sessionId } = useParams<{ sessionId: string }>()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RecommendResponse | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())

  useEffect(() => {
    async function loadRecommendations() {
      if (!sessionId) return
      try {
        setLoading(true)
        const result = await getRecommendations({
          session_id: sessionId,
          enable_llm_reasoning: false,
        })
        setData(result)
        // Select all by default
        setSelected(new Set(result.recommendations.map((r) => r.ad_id)))
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load recommendations')
      } finally {
        setLoading(false)
      }
    }
    loadRecommendations()
  }, [sessionId])

  const toggleSelection = (adId: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(adId)) {
        next.delete(adId)
      } else {
        next.add(adId)
      }
      return next
    })
  }

  const toggleSelectAll = () => {
    if (!data) return
    if (selected.size === data.recommendations.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(data.recommendations.map((r) => r.ad_id)))
    }
  }

  const handleExecute = () => {
    navigate(`/execute/${sessionId}?ads=${Array.from(selected).join(',')}`)
  }

  const getActionStyle = (action: string) => {
    return styles.actionBadge[action as keyof typeof styles.actionBadge] || { background: '#eee', color: '#333' }
  }

  const getPriorityStyle = (priority: string) => {
    return styles.priorityBadge[priority as keyof typeof styles.priorityBadge] || { background: '#eee', color: '#333' }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
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
        <h1 style={styles.title}>Recommendations</h1>
        <p style={styles.subtitle}>Review and approve recommendations for execution</p>

        {loading && (
          <div style={styles.loading}>
            <div style={styles.spinner}></div>
            <p>Generating recommendations...</p>
          </div>
        )}

        {error && (
          <div style={{ background: '#fee', color: '#c00', padding: '16px', borderRadius: '8px' }}>
            {error}
          </div>
        )}

        {data && !loading && (
          <>
            <div style={styles.summary}>
              <div style={styles.summaryCard}>
                <div style={{ ...styles.summaryValue, color: '#667eea' }}>
                  {data.summary.total_recommendations}
                </div>
                <div style={styles.summaryLabel}>Total</div>
              </div>
              <div style={styles.summaryCard}>
                <div style={{ ...styles.summaryValue, color: '#e74c3c' }}>
                  {(data.summary.by_action.pause || 0) + (data.summary.by_action.reduce || 0)}
                </div>
                <div style={styles.summaryLabel}>Cut/Pause</div>
              </div>
              <div style={styles.summaryCard}>
                <div style={{ ...styles.summaryValue, color: '#27ae60' }}>
                  {data.summary.by_action.scale || 0}
                </div>
                <div style={styles.summaryLabel}>Scale</div>
              </div>
              <div style={styles.summaryCard}>
                <div style={{ ...styles.summaryValue, color: '#3498db' }}>
                  {data.summary.by_action.refresh_creative || 0}
                </div>
                <div style={styles.summaryLabel}>Refresh</div>
              </div>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={selected.size === data.recommendations.length}
                  onChange={toggleSelectAll}
                  style={{ width: '18px', height: '18px' }}
                />
                <span>Select All ({selected.size}/{data.recommendations.length})</span>
              </label>
            </div>

            {data.recommendations.map((rec: Recommendation) => (
              <div key={rec.ad_id} style={styles.card}>
                <input
                  type="checkbox"
                  checked={selected.has(rec.ad_id)}
                  onChange={() => toggleSelection(rec.ad_id)}
                  style={styles.checkbox}
                />
                <div style={styles.cardContent}>
                  <div style={styles.cardHeader}>
                    <div>
                      <div style={styles.adName}>{rec.ad_name}</div>
                      <div style={{ fontSize: '12px', color: '#999' }}>{rec.ad_provider}</div>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <span style={{ ...styles.badge, ...getActionStyle(rec.action) }}>
                        {rec.action.replace('_', ' ')}
                      </span>
                      <span style={{ ...styles.badge, ...getPriorityStyle(rec.priority) }}>
                        {rec.priority}
                      </span>
                    </div>
                  </div>
                  <div style={styles.reasoning}>{rec.reasoning}</div>
                  <div style={styles.details}>
                    <span>Spend: {formatCurrency(rec.current_spend)}</span>
                    <span>Change: {rec.recommended_change}</span>
                    <span>Impact: {formatCurrency(rec.estimated_impact)}</span>
                    <span>Confidence: {Math.round(rec.confidence * 100)}%</span>
                  </div>
                </div>
              </div>
            ))}

            {selected.size > 0 && (
              <button style={styles.button} onClick={handleExecute}>
                Execute {selected.size} Recommendation{selected.size > 1 ? 's' : ''}
              </button>
            )}
          </>
        )}
      </main>
    </div>
  )
}
