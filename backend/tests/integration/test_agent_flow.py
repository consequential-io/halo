"""Integration tests for agent execution flow."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from controllers.agatha_controller import AgathaController
from models.analyze_agent import AnalyzeAgent
from models.recommend_agent import RecommendAgent
from models.execute_agent import ExecuteAgent


class TestAgathaController:
    """Tests for AgathaController orchestration."""

    @pytest.fixture
    def controller(self):
        """Create controller instance."""
        return AgathaController()

    @pytest.mark.asyncio
    async def test_analyze_with_fixture(self, controller, thirdlove_ads):
        """Test analyze flow with fixture data."""
        result = await controller.analyze(tenant="tl", use_fixture=True)

        assert "results" in result
        assert len(result["results"]) > 0

        # Check that all expected classifications are present
        classifications = [r["classification"] for r in result["results"]]
        assert "GOOD" in classifications
        assert "BAD" in classifications

    @pytest.mark.asyncio
    async def test_recommend_flow(self, controller):
        """Test recommend flow after analysis."""
        # First analyze
        analysis = await controller.analyze(tenant="tl", use_fixture=True)

        # Then recommend
        result = await controller.recommend(analysis["results"])

        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    @pytest.mark.asyncio
    async def test_execute_mock_mode(self, controller):
        """Test execute flow in mock mode."""
        recommendations = [
            {
                "ad_name": "Test Ad",
                "action": "SCALE",
                "current_spend": 50000,
                "change_percentage": 50,
                "proposed_new_spend": 75000,
                "confidence": "HIGH",
                "rationale": "Test",
            }
        ]

        result = await controller.execute(
            recommendations=recommendations,
            approved_ids=["Test Ad"]
        )

        assert "result" in result
        assert result["result"]["mock_mode"] is True

    @pytest.mark.asyncio
    async def test_full_pipeline(self, controller):
        """Test complete pipeline flow."""
        result = await controller.run_pipeline(
            tenant="tl",
            use_fixture=True,
            auto_execute=False
        )

        assert "analysis" in result
        assert "recommendations" in result
        assert result["executed"] is False


class TestAnalyzeAgent:
    """Tests for AnalyzeAgent."""

    @pytest.mark.asyncio
    async def test_analyze_returns_valid_structure(self, thirdlove_ads):
        """Test that analysis returns valid structure."""
        # This test will use real LLM if available, otherwise mock
        try:
            agent = AnalyzeAgent()
            results = await agent.analyze(thirdlove_ads)

            assert isinstance(results, list)
            for result in results:
                assert "ad_name" in result
                assert "classification" in result
                assert "confidence" in result
        except ValueError:
            # API key not available
            pytest.skip("Google API key not configured")


class TestRecommendAgent:
    """Tests for RecommendAgent."""

    @pytest.mark.asyncio
    async def test_recommend_generates_actions(self, sample_analysis_result):
        """Test that recommendations are generated."""
        agent = RecommendAgent()
        results = await agent.recommend([sample_analysis_result])

        assert isinstance(results, list)
        # GOOD classification should generate a SCALE recommendation
        if results:
            assert results[0]["action"] == "SCALE"


class TestExecuteAgent:
    """Tests for ExecuteAgent."""

    @pytest.mark.asyncio
    async def test_execute_mock_mode(self, sample_recommendation):
        """Test execute in mock mode."""
        agent = ExecuteAgent(mock_mode=True)
        result = await agent.execute(
            recommendations=[sample_recommendation],
            approved_ids=[sample_recommendation["ad_name"]]
        )

        assert result["mock_mode"] is True
        assert len(result["executed"]) > 0
        assert result["executed"][0]["status"] == "MOCK"
