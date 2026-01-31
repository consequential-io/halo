"""Request schemas for Agatha API."""

from typing import List, Optional
from pydantic import BaseModel, Field


class AdInput(BaseModel):
    """Single ad input for analysis."""
    ad_name: str
    ad_provider: str
    spend: float = Field(ge=0)
    roas: float = Field(ge=0)
    days_active: int = Field(ge=0)


class AnalyzeRequest(BaseModel):
    """Request to analyze ad performance."""
    account_avg_roas: float = Field(gt=0, description="Account average ROAS")
    ads: List[AdInput] = Field(min_length=1, description="List of ads to analyze")
    tenant: str = Field(default="tl", description="Tenant identifier (tl or wh)")

    class Config:
        json_schema_extra = {
            "example": {
                "account_avg_roas": 6.90,
                "ads": [
                    {
                        "ad_name": "Summer Sale Campaign",
                        "ad_provider": "Google Ads",
                        "spend": 50000,
                        "roas": 12.5,
                        "days_active": 30
                    }
                ],
                "tenant": "tl"
            }
        }


class RecommendRequest(BaseModel):
    """Request to generate recommendations from analysis."""
    session_id: Optional[str] = Field(None, description="Session ID to retrieve cached analysis")
    analysis_results: Optional[List[dict]] = Field(None, description="Direct analysis results")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123"
            }
        }


class ExecuteRequest(BaseModel):
    """Request to execute recommendations."""
    session_id: Optional[str] = Field(None, description="Session ID to retrieve cached recommendations")
    recommendations: Optional[List[dict]] = Field(None, description="Direct recommendations to execute")
    approved_ads: Optional[List[str]] = Field(None, description="List of ad names to execute (if None, execute all)")
    mock_mode: bool = Field(default=True, description="If True, don't make real API calls")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "abc123",
                "approved_ads": ["Thirdlove® Bras"],
                "mock_mode": True
            }
        }
