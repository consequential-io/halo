"""Agatha Controller - Orchestrates the agent pipeline."""

import logging
import uuid
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

from models.analyze_agent import AnalyzeAgent
from models.recommend_agent import RecommendAgent
from models.execute_agent import ExecuteAgent


class SessionStore:
    """Simple in-memory session store for hackathon."""

    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self) -> str:
        """Create a new session and return its ID."""
        session_id = str(uuid.uuid4())[:8]
        self._sessions[session_id] = {
            "analysis": None,
            "recommendations": None,
            "execution": None,
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by ID."""
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, key: str, value: Any):
        """Update a session field."""
        if session_id in self._sessions:
            self._sessions[session_id][key] = value

    def delete_session(self, session_id: str):
        """Delete a session."""
        self._sessions.pop(session_id, None)


# Global session store
session_store = SessionStore()


class AgathaController:
    """Controller that orchestrates the Analyze → Recommend → Execute pipeline."""

    def __init__(self):
        self.analyze_agent = AnalyzeAgent()
        self.recommend_agent = RecommendAgent()
        self.execute_agent = ExecuteAgent(mock_mode=True)

    async def analyze(
        self,
        account_avg_roas: float,
        ads: List[Dict[str, Any]],
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run analysis on ads.

        Args:
            account_avg_roas: Account average ROAS
            ads: List of ad data
            session_id: Optional session ID to store results

        Returns:
            Analysis results with session ID
        """
        # Create session if not provided
        if not session_id:
            session_id = session_store.create_session()

        logger.info(f"[PIPELINE] Starting analysis for {len(ads)} ads, avg_roas={account_avg_roas}")

        # Run analysis
        input_data = {
            "account_avg_roas": account_avg_roas,
            "ads": ads
        }
        results = await self.analyze_agent.analyze(input_data)

        # Create summary
        summary = {}
        for result in results:
            cls = result.get("classification", "UNKNOWN")
            summary[cls] = summary.get(cls, 0) + 1

        logger.info(f"[PIPELINE] Analysis complete: {summary}")

        # Store in session
        session_store.update_session(session_id, "analysis", results)

        return {
            "session_id": session_id,
            "account_avg_roas": account_avg_roas,
            "total_ads": len(results),
            "results": results,
            "summary": summary,
        }

    async def recommend(
        self,
        session_id: Optional[str] = None,
        analysis_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate recommendations from analysis.

        Args:
            session_id: Session ID to retrieve cached analysis
            analysis_results: Direct analysis results (if not using session)

        Returns:
            Recommendations with session ID
        """
        # Get analysis results
        if analysis_results is None and session_id:
            session = session_store.get_session(session_id)
            if session:
                analysis_results = session.get("analysis")

        if not analysis_results:
            raise ValueError("No analysis results provided or found in session")

        # Create session if not provided
        if not session_id:
            session_id = session_store.create_session()

        logger.info(f"[PIPELINE] Generating recommendations for {len(analysis_results)} analyses")

        # Generate recommendations
        recommendations = await self.recommend_agent.recommend(analysis_results)

        # Calculate totals
        total_spend_change = 0
        total_expected_revenue = 0
        actionable_count = 0

        for rec in recommendations:
            action = rec.get("action")
            if action in ["SCALE", "REDUCE", "PAUSE"]:
                actionable_count += 1
                change = rec.get("proposed_new_spend", 0) - rec.get("current_spend", 0)
                total_spend_change += change
            total_expected_revenue += rec.get("expected_impact", {}).get("estimated_revenue_change", 0)

        logger.info(f"[PIPELINE] Recommendations: {actionable_count} actionable, total_spend_change=${total_spend_change:,.0f}")

        # Store in session
        session_store.update_session(session_id, "recommendations", recommendations)

        return {
            "session_id": session_id,
            "total_recommendations": len(recommendations),
            "actionable_count": actionable_count,
            "recommendations": recommendations,
            "total_spend_change": total_spend_change,
            "total_expected_revenue": total_expected_revenue,
        }

    async def execute(
        self,
        session_id: Optional[str] = None,
        recommendations: Optional[List[Dict[str, Any]]] = None,
        approved_ads: Optional[List[str]] = None,
        mock_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Execute approved recommendations.

        Args:
            session_id: Session ID to retrieve cached recommendations
            recommendations: Direct recommendations (if not using session)
            approved_ads: List of ad names to execute (if None, execute all actionable)
            mock_mode: If True, don't make real API calls

        Returns:
            Execution results
        """
        # Get recommendations
        if recommendations is None and session_id:
            session = session_store.get_session(session_id)
            if session:
                recommendations = session.get("recommendations")

        if not recommendations:
            raise ValueError("No recommendations provided or found in session")

        # Create session if not provided
        if not session_id:
            session_id = session_store.create_session()

        logger.info(f"[PIPELINE] Executing {len(recommendations)} recommendations, approved={approved_ads}")

        # Set mock mode
        self.execute_agent.mock_mode = mock_mode

        # Filter to actionable recommendations
        actionable = [
            r for r in recommendations
            if r.get("action") in ["SCALE", "REDUCE", "PAUSE"]
        ]

        # Execute
        result = await self.execute_agent.execute(actionable, approved_ads)

        logger.info(f"[PIPELINE] Execution complete: {result.get('summary')}")

        # Store in session
        session_store.update_session(session_id, "execution", result)

        return {
            "session_id": session_id,
            **result
        }

    async def run_full_pipeline(
        self,
        account_avg_roas: float,
        ads: List[Dict[str, Any]],
        approved_ads: Optional[List[str]] = None,
        mock_mode: bool = True
    ) -> Dict[str, Any]:
        """
        Run the full Analyze → Recommend → Execute pipeline.

        Args:
            account_avg_roas: Account average ROAS
            ads: List of ad data
            approved_ads: List of ad names to execute (if None, execute all)
            mock_mode: If True, don't make real API calls

        Returns:
            Full pipeline results
        """
        # Step 1: Analyze
        analysis = await self.analyze(account_avg_roas, ads)
        session_id = analysis["session_id"]

        # Step 2: Recommend
        recommendations = await self.recommend(session_id=session_id)

        # Step 3: Execute
        execution = await self.execute(
            session_id=session_id,
            approved_ads=approved_ads,
            mock_mode=mock_mode
        )

        return {
            "session_id": session_id,
            "analysis": analysis,
            "recommendations": recommendations,
            "execution": execution,
        }
