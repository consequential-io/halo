"""
Agatha Controller - Orchestrates the analysis → recommend → execute workflow.
"""

from typing import Any

from config.session_manager import get_session_manager, Session
from config.settings import settings
from models.analyze_agent import AnalyzeAgentModel
from models.recommend_agent import RecommendAgentModel
from models.execute_agent import ExecuteAgentModel
from helpers.tools import get_ad_data


class AgathaController:
    """
    Controller for Agatha ad spend optimization workflow.

    Orchestrates: Analyze → Recommend → Execute
    """

    def __init__(self):
        self.session_manager = get_session_manager()

    def run_analysis(
        self,
        tenant: str,
        days: int = 30,
        source: str = "fixture"
    ) -> dict[str, Any]:
        """
        Run anomaly analysis on ad data.

        Args:
            tenant: Tenant identifier (e.g., 'TL', 'WH')
            days: Days of data to analyze
            source: Data source ('fixture' or 'bq')

        Returns:
            Analysis result with session_id
        """
        # Create session
        session = self.session_manager.create_session(tenant)

        # Get ad data
        ad_data = get_ad_data(tenant, source=source)
        if "error" in ad_data:
            return {
                "error": ad_data["error"],
                "session_id": session.session_id,
            }

        ads = ad_data.get("ads", [])

        # Run analysis
        analyze_agent = AnalyzeAgentModel()
        analysis_result = analyze_agent.run_analysis(tenant, days=days, source=source)

        # Store in session
        self.session_manager.update_session(
            session.session_id,
            analysis_result=analysis_result,
            all_ads=ads,
        )

        return {
            "session_id": session.session_id,
            "tenant": tenant,
            "summary": analysis_result.get("summary", {}),
            "anomalies_found": len(analysis_result.get("detailed_anomalies", [])),
            "total_ads": len(ads),
        }

    async def run_recommendations(
        self,
        session_id: str,
        enable_llm_reasoning: bool = True
    ) -> dict[str, Any]:
        """
        Generate recommendations from analysis results.

        Args:
            session_id: Session ID from analyze step
            enable_llm_reasoning: Enable LLM-enhanced reasoning

        Returns:
            Recommendations result
        """
        # Get session
        session = self.session_manager.get_session(session_id)
        if session is None:
            return {"error": "Session not found or expired"}

        if session.analysis_result is None:
            return {"error": "No analysis result in session. Run analysis first."}

        # Run recommendations
        recommend_agent = RecommendAgentModel(enable_llm_reasoning=enable_llm_reasoning)
        rec_result = await recommend_agent.generate_recommendations_async(
            session.analysis_result,
            all_ads=session.all_ads,
        )

        # Store in session
        self.session_manager.update_session(
            session_id,
            recommendations=rec_result,
        )

        return {
            "session_id": session_id,
            "recommendations": rec_result.get("recommendations", []),
            "summary": rec_result.get("summary", {}),
        }

    def run_recommendations_sync(
        self,
        session_id: str,
        enable_llm_reasoning: bool = False
    ) -> dict[str, Any]:
        """
        Synchronous version of run_recommendations (without LLM enrichment).

        Args:
            session_id: Session ID from analyze step
            enable_llm_reasoning: Must be False for sync version

        Returns:
            Recommendations result
        """
        session = self.session_manager.get_session(session_id)
        if session is None:
            return {"error": "Session not found or expired"}

        if session.analysis_result is None:
            return {"error": "No analysis result in session. Run analysis first."}

        recommend_agent = RecommendAgentModel(enable_llm_reasoning=False)
        rec_result = recommend_agent.generate_recommendations(
            session.analysis_result,
            all_ads=session.all_ads,
        )

        self.session_manager.update_session(
            session_id,
            recommendations=rec_result,
        )

        return {
            "session_id": session_id,
            "recommendations": rec_result.get("recommendations", []),
            "summary": rec_result.get("summary", {}),
        }

    async def run_execution(
        self,
        session_id: str,
        approved_ad_ids: list[str] | None = None,
        dry_run: bool = True
    ) -> dict[str, Any]:
        """
        Execute approved recommendations.

        Args:
            session_id: Session ID from analyze/recommend steps
            approved_ad_ids: List of ad IDs to execute. If None, executes all.
            dry_run: If True, simulate execution

        Returns:
            Execution result
        """
        session = self.session_manager.get_session(session_id)
        if session is None:
            return {"error": "Session not found or expired"}

        if session.recommendations is None:
            return {"error": "No recommendations in session. Run recommendations first."}

        recommendations = session.recommendations.get("recommendations", [])
        if not recommendations:
            return {"error": "No recommendations to execute"}

        # Run execution
        execute_agent = ExecuteAgentModel(dry_run=dry_run)
        exec_result = await execute_agent.execute_batch_async(
            recommendations,
            approved_ad_ids=approved_ad_ids,
            tenant=session.tenant,
        )

        # Store in session
        self.session_manager.update_session(
            session_id,
            execution_result=exec_result,
        )

        return {
            "session_id": session_id,
            "results": exec_result.get("results", []),
            "summary": exec_result.get("summary", {}),
            "timestamp": exec_result.get("timestamp", ""),
        }

    def get_session_state(self, session_id: str) -> dict[str, Any] | None:
        """
        Get current session state.

        Args:
            session_id: Session identifier

        Returns:
            Session state dict or None if not found
        """
        session = self.session_manager.get_session(session_id)
        if session is None:
            return None

        return {
            "session_id": session.session_id,
            "tenant": session.tenant,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "has_analysis": session.analysis_result is not None,
            "has_recommendations": session.recommendations is not None,
            "has_execution": session.execution_result is not None,
        }


# Singleton accessor
_controller_instance: AgathaController | None = None


def get_controller() -> AgathaController:
    """Get the singleton controller instance."""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = AgathaController()
    return _controller_instance
