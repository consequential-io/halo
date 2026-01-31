"""Shared test fixtures and configuration."""

import pytest
import json
from pathlib import Path
from typing import Dict, Any


# Path to fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def thirdlove_ads() -> Dict[str, Any]:
    """Load ThirdLove test ads fixture."""
    fixture_file = FIXTURES_DIR / "thirdlove_ads.json"
    with open(fixture_file, "r") as f:
        return json.load(f)


@pytest.fixture
def sample_ad() -> Dict[str, Any]:
    """Single sample ad for unit tests."""
    return {
        "ad_name": "Test Ad Campaign",
        "ad_provider": "Facebook Ads",
        "spend": 50000,
        "roas": 15.0,
        "days_active": 30,
    }


@pytest.fixture
def good_ad() -> Dict[str, Any]:
    """Sample ad classified as GOOD (high ROAS)."""
    return {
        "ad_name": "High Performer",
        "ad_provider": "Google Ads",
        "spend": 100000,
        "roas": 25.0,
        "days_active": 45,
    }


@pytest.fixture
def bad_ad() -> Dict[str, Any]:
    """Sample ad classified as BAD (zero ROAS)."""
    return {
        "ad_name": "Zero Return",
        "ad_provider": "TikTok Ads",
        "spend": 50000,
        "roas": 0.0,
        "days_active": 30,
    }


@pytest.fixture
def wait_ad() -> Dict[str, Any]:
    """Sample ad classified as WAIT (insufficient data)."""
    return {
        "ad_name": "New Campaign",
        "ad_provider": "Facebook Ads",
        "spend": 500,
        "roas": 10.0,
        "days_active": 3,
    }


@pytest.fixture
def account_avg_roas() -> float:
    """Account average ROAS for ThirdLove."""
    return 6.90


@pytest.fixture
def sample_analysis_result(sample_ad, account_avg_roas) -> Dict[str, Any]:
    """Sample analysis result from AnalyzeAgent."""
    return {
        "ad_name": sample_ad["ad_name"],
        "metrics": {
            "spend": sample_ad["spend"],
            "roas": sample_ad["roas"],
            "days_active": sample_ad["days_active"],
            "account_avg_roas": account_avg_roas,
        },
        "chain_of_thought": {
            "data_extracted": {
                "spend": sample_ad["spend"],
                "roas": sample_ad["roas"],
                "days": sample_ad["days_active"],
            },
            "comparison": {
                "roas_ratio": f"{sample_ad['roas']} / {account_avg_roas} = {sample_ad['roas']/account_avg_roas:.2f}×"
            },
            "qualification": {
                "spend_ok": sample_ad["spend"] >= 1000,
                "days_ok": sample_ad["days_active"] >= 7,
            },
            "classification_logic": {
                "result": "GOOD",
                "reason": "ROAS exceeds 2× account average",
            },
            "confidence_rationale": {
                "level": "HIGH",
                "reason": "Strong signal with high spend",
            },
        },
        "classification": "GOOD",
        "recommended_action": "SCALE",
        "confidence": "HIGH",
        "user_explanation": f"ROAS of {sample_ad['roas']:.2f} is excellent. Scale budget.",
    }


@pytest.fixture
def sample_recommendation(sample_ad) -> Dict[str, Any]:
    """Sample recommendation from RecommendAgent."""
    return {
        "ad_name": sample_ad["ad_name"],
        "action": "SCALE",
        "current_spend": sample_ad["spend"],
        "change_percentage": 75,
        "proposed_new_spend": sample_ad["spend"] * 1.75,
        "expected_impact": {
            "calculation": f"${sample_ad['spend']*0.75:,.0f} increase × {sample_ad['roas']:.2f} ROAS",
            "estimated_revenue_change": sample_ad["spend"] * 0.75 * sample_ad["roas"],
        },
        "confidence": "HIGH",
        "rationale": "Strong ROAS performance",
    }


# Mock async functions for unit tests
class MockAsyncIterator:
    """Mock async iterator for ADK runner responses."""

    def __init__(self, responses):
        self.responses = responses
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.responses):
            raise StopAsyncIteration
        response = self.responses[self.index]
        self.index += 1
        return response
