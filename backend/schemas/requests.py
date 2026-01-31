"""
Request schemas for Agatha API.
"""

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Request to run anomaly analysis."""
    tenant: str = Field(..., description="Tenant identifier (e.g., 'TL', 'WH')")
    days: int = Field(default=30, ge=1, le=90, description="Days of data to analyze")
    source: str = Field(default="fixture", description="Data source: 'fixture' or 'bq'")


class RecommendRequest(BaseModel):
    """Request to generate recommendations."""
    session_id: str = Field(..., description="Session ID from analyze step")
    enable_llm_reasoning: bool = Field(
        default=True,
        description="Enable LLM-enhanced reasoning for recommendations"
    )


class ExecuteRequest(BaseModel):
    """Request to execute approved recommendations."""
    session_id: str = Field(..., description="Session ID from analyze/recommend steps")
    approved_ad_ids: list[str] | None = Field(
        default=None,
        description="List of ad IDs to execute. If None, executes all."
    )
    dry_run: bool = Field(
        default=True,
        description="If True, simulate execution without actual changes"
    )
