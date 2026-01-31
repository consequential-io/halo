import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080'
const API_TOKEN = import.meta.env.VITE_API_TOKEN || ''

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    ...(API_TOKEN ? { Authorization: `Bearer ${API_TOKEN}` } : {}),
  },
})

// Types
export interface AnalyzeRequest {
  tenant: string
  days?: number
  source?: string  // 'fixture' or 'bq'
}

export interface AnalyzeResponse {
  session_id: string
  tenant: string
  summary: Record<string, unknown>
  anomalies_found: number
  total_ads: number
}

export interface RecommendRequest {
  session_id: string
  enable_llm_reasoning?: boolean
}

export interface Recommendation {
  action: string
  ad_name: string
  ad_id: string
  ad_provider: string
  current_spend: number
  recommended_change: string
  reasoning: string
  estimated_impact: number
  priority: string
  confidence: number
}

export interface RecommendResponse {
  session_id: string
  recommendations: Recommendation[]
  summary: {
    total_recommendations: number
    by_action: Record<string, number>
    by_priority: Record<string, number>
    total_potential_savings: number
    total_potential_revenue: number
  }
}

export interface ExecuteRequest {
  session_id: string
  approved_ad_ids?: string[]
  dry_run?: boolean
}

export interface ExecutionResult {
  status: string
  action: string
  ad_id: string
  ad_name: string
  message: string
  dry_run: boolean
}

export interface ExecuteResponse {
  session_id: string
  results: ExecutionResult[]
  summary: {
    total_processed: number
    success: number
    failed: number
    skipped: number
    dry_run: boolean
  }
  timestamp: string
}

// API functions
export async function analyze(request: AnalyzeRequest): Promise<AnalyzeResponse> {
  const response = await apiClient.post<AnalyzeResponse>('/api/analyze', request)
  return response.data
}

export async function getRecommendations(request: RecommendRequest): Promise<RecommendResponse> {
  const response = await apiClient.post<RecommendResponse>('/api/recommendations', request)
  return response.data
}

export async function execute(request: ExecuteRequest): Promise<ExecuteResponse> {
  const response = await apiClient.post<ExecuteResponse>('/api/execute', request)
  return response.data
}

export async function getTenants(): Promise<{ tenants: { id: string; name: string }[] }> {
  const response = await apiClient.get('/api/tenants')
  return response.data
}

export async function getMetaLoginUrl(): Promise<{ oauth_url: string }> {
  const response = await apiClient.post('/auth/meta/login')
  return response.data
}
