import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getRecommendations, Recommendation, RecommendResponse } from '../api/client'
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
    marginBottom: '32px',
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
  selectAll: {
    marginBottom: '20px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    color: '#A1A1A1',
    cursor: 'pointer',
    fontSize: '14px',
  },
  cardsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '20px',
    marginBottom: '100px',
  },
  card: {
    background: '#1A1A1A',
    border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '12px',
    padding: '24px',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  cardSelected: {
    borderColor: '#9AE65C',
    boxShadow: '0 0 0 1px #9AE65C',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '16px',
  },
  categoryBadge: {
    display: 'inline-block',
    padding: '6px 12px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  impactMetric: {
    textAlign: 'right' as const,
  },
  impactValue: {
    fontSize: '32px',
    fontWeight: 700,
    lineHeight: 1,
  },
  impactLabel: {
    fontSize: '12px',
    color: '#A1A1A1',
    marginTop: '4px',
  },
  providerInfo: {
    fontSize: '13px',
    color: '#A1A1A1',
    marginBottom: '16px',
  },
  cardTitle: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#FFFFFF',
    marginBottom: '8px',
    lineHeight: 1.3,
  },
  cardDescription: {
    fontSize: '14px',
    color: '#A1A1A1',
    lineHeight: 1.5,
    marginBottom: '16px',
  },
  cardFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: '16px',
    borderTop: '1px solid rgba(255,255,255,0.1)',
  },
  cardMeta: {
    fontSize: '13px',
    color: '#666',
  },
  checkbox: {
    width: '20px',
    height: '20px',
    cursor: 'pointer',
    accentColor: '#9AE65C',
  },
  fixedFooter: {
    position: 'fixed' as const,
    bottom: 0,
    left: '260px',
    right: 0,
    padding: '20px 32px',
    background: '#0A0A0A',
    borderTop: '1px solid rgba(255,255,255,0.1)',
    display: 'flex',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: '16px',
  },
  selectedCount: {
    color: '#A1A1A1',
    fontSize: '14px',
  },
  executeBtn: {
    background: '#9AE65C',
    color: '#0A0A0A',
    border: 'none',
    borderRadius: '8px',
    padding: '14px 32px',
    fontSize: '15px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  executeBtnDisabled: {
    background: '#333',
    color: '#666',
    cursor: 'not-allowed',
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

const actionLabels: Record<string, string> = {
  pause: 'High CPA',
  reduce: 'Reduce Spend',
  scale: 'Scale Opportunity',
  refresh_creative: 'Creative Fatigue',
}

const actionColors: Record<string, { bg: string; color: string }> = {
  pause: { bg: 'rgba(255, 107, 107, 0.15)', color: '#FF6B6B' },
  reduce: { bg: 'rgba(255, 183, 77, 0.15)', color: '#FFB74D' },
  scale: { bg: 'rgba(154, 230, 92, 0.15)', color: '#9AE65C' },
  refresh_creative: { bg: 'rgba(100, 181, 246, 0.15)', color: '#64B5F6' },
}

export default function RecommendationsPage() {
  const navigate = useNavigate()
  const { sessionId } = useParams<{ sessionId: string }>()
  const { tenantName } = useAuth()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<RecommendResponse | null>(null)
  // Start with nothing selected
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
        // Start with nothing selected (user must choose)
        setSelected(new Set())
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
    if (selected.size === 0) return
    navigate(`/execute/${sessionId}?ads=${Array.from(selected).join(',')}`)
  }

  const formatCurrency = (value: number) => {
    if (Math.abs(value) >= 1000) {
      return `$${(value / 1000).toFixed(1)}K`
    }
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value)
  }

  const formatImpact = (rec: Recommendation) => {
    const impact = rec.estimated_impact
    if (rec.action === 'scale') {
      return `+${formatCurrency(impact)}`
    } else if (rec.action === 'pause' || rec.action === 'reduce') {
      return `-${Math.abs(Math.round(rec.confidence * 100))}%`
    }
    return formatCurrency(Math.abs(impact))
  }

  const getImpactLabel = (rec: Recommendation) => {
    switch (rec.action) {
      case 'scale': return 'Revenue Potential'
      case 'pause': return 'Waste Eliminated'
      case 'reduce': return 'Spend Reduction'
      case 'refresh_creative': return 'Performance Lift'
      default: return 'Impact'
    }
  }

  const getActionTitle = (rec: Recommendation) => {
    const adName = rec.ad_name.length > 40 ? rec.ad_name.substring(0, 40) + '...' : rec.ad_name
    switch (rec.action) {
      case 'pause': return `Pause Underperforming: ${adName}`
      case 'reduce': return `Reduce Budget: ${adName}`
      case 'scale': return `Scale High Performer: ${adName}`
      case 'refresh_creative': return `Refresh Creative: ${adName}`
      default: return rec.ad_name
    }
  }

  return (
    <Layout
      tenantName={tenantName}
      sessionId={sessionId}
      hasAnalysis={true}
      hasRecommendations={selected.size > 0}
    >
      <style>
        {`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
          @media (max-width: 1200px) {
            .cards-grid { grid-template-columns: 1fr !important; }
          }`}
      </style>

      <div style={styles.headerRow}>
        <div>
          <h1 style={styles.title}>Recommendations</h1>
          <p style={styles.subtitle}>Review and approve AI-generated optimization recommendations</p>
        </div>
      </div>

      {loading && (
        <div style={styles.loading}>
          <div style={styles.spinner}></div>
          <p style={{ color: '#A1A1A1' }}>Generating recommendations...</p>
        </div>
      )}

      {error && (
        <div style={styles.error}>{error}</div>
      )}

      {data && !loading && (
        <>
          <div style={styles.summary}>
            <div style={styles.summaryCard}>
              <div style={{ ...styles.summaryValue, color: '#9AE65C' }}>
                {data.summary.total_recommendations}
              </div>
              <div style={styles.summaryLabel}>Total</div>
            </div>
            <div style={styles.summaryCard}>
              <div style={{ ...styles.summaryValue, color: '#FF6B6B' }}>
                {(data.summary.by_action.pause || 0) + (data.summary.by_action.reduce || 0)}
              </div>
              <div style={styles.summaryLabel}>Cut/Pause</div>
            </div>
            <div style={styles.summaryCard}>
              <div style={{ ...styles.summaryValue, color: '#9AE65C' }}>
                {data.summary.by_action.scale || 0}
              </div>
              <div style={styles.summaryLabel}>Scale</div>
            </div>
            <div style={styles.summaryCard}>
              <div style={{ ...styles.summaryValue, color: '#64B5F6' }}>
                {data.summary.by_action.refresh_creative || 0}
              </div>
              <div style={styles.summaryLabel}>Refresh</div>
            </div>
          </div>

          <label style={styles.selectAll} onClick={toggleSelectAll}>
            <input
              type="checkbox"
              checked={data.recommendations.length > 0 && selected.size === data.recommendations.length}
              onChange={toggleSelectAll}
              style={styles.checkbox}
            />
            <span>Select All ({selected.size}/{data.recommendations.length})</span>
          </label>

          <div className="cards-grid" style={styles.cardsGrid}>
            {data.recommendations.map((rec: Recommendation) => {
              const actionStyle = actionColors[rec.action] || actionColors.pause
              const isSelected = selected.has(rec.ad_id)

              return (
                <div
                  key={rec.ad_id}
                  style={{
                    ...styles.card,
                    ...(isSelected ? styles.cardSelected : {}),
                  }}
                  onClick={() => toggleSelection(rec.ad_id)}
                >
                  <div style={styles.cardHeader}>
                    <div>
                      <span style={{
                        ...styles.categoryBadge,
                        background: actionStyle.bg,
                        color: actionStyle.color,
                      }}>
                        {actionLabels[rec.action] || rec.action}
                      </span>
                      <div style={styles.providerInfo}>
                        {rec.ad_provider} • {formatCurrency(rec.current_spend)}/day
                      </div>
                    </div>
                    <div style={styles.impactMetric}>
                      <div style={{
                        ...styles.impactValue,
                        color: rec.action === 'pause' || rec.action === 'reduce' ? '#FF6B6B' : '#9AE65C',
                      }}>
                        {formatImpact(rec)}
                      </div>
                      <div style={styles.impactLabel}>{getImpactLabel(rec)}</div>
                    </div>
                  </div>

                  <h3 style={styles.cardTitle}>{getActionTitle(rec)}</h3>
                  <p style={styles.cardDescription}>{rec.reasoning}</p>

                  <div style={styles.cardFooter}>
                    <span style={styles.cardMeta}>
                      Confidence: {Math.round(rec.confidence * 100)}%
                    </span>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelection(rec.ad_id)}
                      onClick={(e) => e.stopPropagation()}
                      style={styles.checkbox}
                    />
                  </div>
                </div>
              )
            })}
          </div>

          {/* Fixed Footer with Execute Button */}
          <div style={styles.fixedFooter}>
            <span style={styles.selectedCount}>
              {selected.size} of {data.recommendations.length} selected
            </span>
            <button
              style={{
                ...styles.executeBtn,
                ...(selected.size === 0 ? styles.executeBtnDisabled : {}),
              }}
              onClick={handleExecute}
              disabled={selected.size === 0}
              onMouseOver={(e) => {
                if (selected.size > 0) e.currentTarget.style.background = '#8BD84E'
              }}
              onMouseOut={(e) => {
                if (selected.size > 0) e.currentTarget.style.background = '#9AE65C'
              }}
            >
              Execute {selected.size > 0 ? `${selected.size} Recommendation${selected.size > 1 ? 's' : ''}` : 'Selected'}
            </button>
          </div>
        </>
      )}
    </Layout>
  )
}
