"""
Response schemas for Agatha API.
"""

from typing import Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "0.1.0"
    environment: str = "development"


class AnalyzeResponse(BaseModel):
    """Response from analyze endpoint."""
    session_id: str = Field(..., description="Session ID for subsequent requests")
    tenant: str = Field(..., description="Tenant that was analyzed")
    summary: dict[str, Any] = Field(..., description="Analysis summary")
    anomalies_found: int = Field(..., description="Number of anomalies detected")
    total_ads: int = Field(..., description="Total ads analyzed")


class RecommendResponse(BaseModel):
    """Response from recommendations endpoint."""
    session_id: str = Field(..., description="Session ID")
    recommendations: list[dict[str, Any]] = Field(
        ..., description="List of recommendations"
    )
    summary: dict[str, Any] = Field(..., description="Recommendations summary")


class ExecuteResponse(BaseModel):
    """Response from execute endpoint."""
    session_id: str = Field(..., description="Session ID")
    results: list[dict[str, Any]] = Field(..., description="Execution results per ad")
    summary: dict[str, Any] = Field(..., description="Execution summary")
    timestamp: str = Field(..., description="Execution timestamp")


class ErrorResponse(BaseModel):
    """Error response."""
    error: str = Field(..., description="Error message")
    detail: str | None = Field(default=None, description="Error details")
    code: str | None = Field(default=None, description="Error code")
