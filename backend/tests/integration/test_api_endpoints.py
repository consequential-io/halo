"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns healthy status."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "agatha"

    def test_health_endpoint(self, client):
        """Test health endpoint returns model info."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "ai_provider" in data
        assert "model" in data


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_auth_status(self, client):
        """Test auth status endpoint."""
        response = client.get("/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert "meta_configured" in data


class TestAgentEndpoints:
    """Tests for agent API endpoints."""

    def test_analyze_endpoint_with_fixture(self, client):
        """Test analyze endpoint with fixture data."""
        response = client.post(
            "/api/analyze",
            json={
                "tenant": "tl",
                "use_fixture": True,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_recommend_endpoint(self, client):
        """Test recommend endpoint."""
        # First run analyze to get results
        analyze_response = client.post(
            "/api/analyze",
            json={"tenant": "tl", "use_fixture": True}
        )
        analysis_results = analyze_response.json()["results"]

        # Then get recommendations
        response = client.post(
            "/api/recommend",
            json={"analysis_results": analysis_results}
        )

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data

    def test_execute_endpoint_mock(self, client):
        """Test execute endpoint in mock mode."""
        recommendations = [
            {
                "ad_name": "Test Ad",
                "action": "SCALE",
                "current_spend": 50000,
                "change_percentage": 50,
                "proposed_new_spend": 75000,
                "confidence": "HIGH",
                "rationale": "Test recommendation",
            }
        ]

        response = client.post(
            "/api/execute",
            json={
                "recommendations": recommendations,
                "approved_ids": ["Test Ad"],
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert data["result"]["mock_mode"] is True

    def test_pipeline_endpoint(self, client):
        """Test full pipeline endpoint."""
        response = client.post(
            "/api/pipeline",
            json={
                "tenant": "tl",
                "use_fixture": True,
                "auto_execute": False,
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "analysis" in data
        assert "recommendations" in data
