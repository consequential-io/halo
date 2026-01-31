"""Unit tests for recommendation logic."""

import pytest
from models.recommend_agent import RecommendAgent


class TestRecommendAgent:
    """Tests for RecommendAgent recommendation logic."""

    @pytest.fixture
    def agent(self):
        """Create RecommendAgent instance."""
        return RecommendAgent()

    def test_scale_recommendation_high_roas(self, agent, account_avg_roas):
        """Test SCALE recommendation for high ROAS ad."""
        analysis = {
            "ad_name": "High Performer",
            "classification": "GOOD",
            "recommended_action": "SCALE",
            "confidence": "HIGH",
            "metrics": {
                "spend": 100000,
                "roas": 30.0,
                "days_active": 30,
                "account_avg_roas": account_avg_roas,
            },
        }

        rec = agent._generate_recommendation(analysis)

        assert rec is not None
        assert rec["action"] == "SCALE"
        assert rec["change_percentage"] == 100  # 4.3× avg = 100% increase
        assert rec["proposed_new_spend"] == 200000

    def test_scale_recommendation_moderate_roas(self, agent, account_avg_roas):
        """Test SCALE recommendation for moderate ROAS ad."""
        analysis = {
            "ad_name": "Good Performer",
            "classification": "GOOD",
            "recommended_action": "SCALE",
            "confidence": "HIGH",
            "metrics": {
                "spend": 100000,
                "roas": 15.0,  # ~2.2× avg
                "days_active": 30,
                "account_avg_roas": account_avg_roas,
            },
        }

        rec = agent._generate_recommendation(analysis)

        assert rec is not None
        assert rec["action"] == "SCALE"
        assert rec["change_percentage"] == 50  # 2-3× avg = 50% increase

    def test_reduce_recommendation(self, agent, account_avg_roas):
        """Test REDUCE recommendation for underperforming ad."""
        analysis = {
            "ad_name": "Underperformer",
            "classification": "BAD",
            "recommended_action": "REDUCE",
            "confidence": "HIGH",
            "metrics": {
                "spend": 100000,
                "roas": 2.0,  # Below 0.5× avg
                "days_active": 30,
                "account_avg_roas": account_avg_roas,
            },
        }

        rec = agent._generate_recommendation(analysis)

        assert rec is not None
        assert rec["action"] == "REDUCE"
        assert rec["change_percentage"] == -50
        assert rec["proposed_new_spend"] == 50000

    def test_pause_recommendation(self, agent, account_avg_roas):
        """Test PAUSE recommendation for zero ROAS ad."""
        analysis = {
            "ad_name": "Zero Return",
            "classification": "BAD",
            "recommended_action": "PAUSE",
            "confidence": "HIGH",
            "metrics": {
                "spend": 50000,
                "roas": 0.0,
                "days_active": 30,
                "account_avg_roas": account_avg_roas,
            },
        }

        rec = agent._generate_recommendation(analysis)

        assert rec is not None
        assert rec["action"] == "PAUSE"
        assert rec["change_percentage"] == -100
        assert rec["proposed_new_spend"] == 0

    def test_monitor_recommendation(self, agent, account_avg_roas):
        """Test MONITOR recommendation for OK ad."""
        analysis = {
            "ad_name": "Average Performer",
            "classification": "OK",
            "recommended_action": "MONITOR",
            "confidence": "HIGH",
            "metrics": {
                "spend": 50000,
                "roas": 10.0,  # ~1.4× avg
                "days_active": 30,
                "account_avg_roas": account_avg_roas,
            },
        }

        rec = agent._generate_recommendation(analysis)

        assert rec is not None
        assert rec["action"] == "MONITOR"
        assert rec["change_percentage"] == 0
        assert rec["proposed_new_spend"] == 50000

    def test_skip_low_confidence(self, agent, account_avg_roas):
        """Test that LOW confidence ads are skipped."""
        analysis = {
            "ad_name": "Uncertain",
            "classification": "GOOD",
            "recommended_action": "SCALE",
            "confidence": "LOW",  # Should skip
            "metrics": {
                "spend": 50000,
                "roas": 15.0,
                "days_active": 30,
                "account_avg_roas": account_avg_roas,
            },
        }

        rec = agent._generate_recommendation(analysis)

        assert rec is None

    def test_skip_wait_classification(self, agent, account_avg_roas):
        """Test that WAIT classifications are skipped."""
        analysis = {
            "ad_name": "New Ad",
            "classification": "WAIT",
            "recommended_action": "WAIT",
            "confidence": "HIGH",
            "metrics": {
                "spend": 500,
                "roas": 10.0,
                "days_active": 3,
                "account_avg_roas": account_avg_roas,
            },
        }

        rec = agent._generate_recommendation(analysis)

        assert rec is None

    def test_expected_impact_calculation(self, agent, account_avg_roas):
        """Test that expected impact is calculated correctly."""
        analysis = {
            "ad_name": "High Performer",
            "classification": "GOOD",
            "recommended_action": "SCALE",
            "confidence": "HIGH",
            "metrics": {
                "spend": 100000,
                "roas": 20.0,
                "days_active": 30,
                "account_avg_roas": account_avg_roas,
            },
        }

        rec = agent._generate_recommendation(analysis)

        # 75% increase on 100k = 75k additional spend
        # 75k × 20.0 ROAS = 1.5M expected revenue
        assert rec["expected_impact"]["estimated_revenue_change"] == 75000 * 20.0
