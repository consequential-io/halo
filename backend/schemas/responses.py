"""Response schemas for Agatha API."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ChainOfThought(BaseModel):
    """Chain of thought reasoning."""
    data_extracted: Dict[str, Any]
    comparison: Dict[str, Any]
    qualification: Dict[str, Any]
    classification_logic: Dict[str, Any]
    confidence_rationale: Dict[str, Any]


class Metrics(BaseModel):
    """Ad metrics."""
    spend: float
    roas: float
    days_active: int
    account_avg_roas: float


class AnalysisResult(BaseModel):
    """Single ad analysis result."""
    ad_name: str
    ad_provider: Optional[str] = None
    metrics: Metrics
    chain_of_thought: ChainOfThought
    classification: str
    recommended_action: str
    confidence: str
    user_explanation: str


class AnalyzeResponse(BaseModel):
    """Response from analyze endpoint."""
    session_id: str
    account_avg_roas: float
    total_ads: int
    results: List[AnalysisResult]
    summary: Dict[str, int]  # Classification counts


class ExpectedImpact(BaseModel):
    """Expected impact of a recommendation."""
    calculation: str
    estimated_revenue_change: float


class Recommendation(BaseModel):
    """Single recommendation."""
    ad_name: str
    action: str
    current_spend: float
    change_percentage: float
    proposed_new_spend: float
    expected_impact: ExpectedImpact
    confidence: str
    rationale: str


class RecommendResponse(BaseModel):
    """Response from recommend endpoint."""
    session_id: str
    total_recommendations: int
    actionable_count: int
    recommendations: List[Recommendation]
    total_spend_change: float
    total_expected_revenue: float


class ExecutionResult(BaseModel):
    """Single execution result."""
    ad_name: str
    action_taken: str
    old_budget: float
    new_budget: float
    status: str
    message: str
    rationale: Optional[str] = None


class ExecuteResponse(BaseModel):
    """Response from execute endpoint."""
    session_id: str
    executed: List[ExecutionResult]
    summary: str
    timestamp: str
    mock_mode: bool
