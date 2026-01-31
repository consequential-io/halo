"""Execute Agent - Executes approved recommendations (mock for hackathon)."""

from typing import Dict, Any, List
from datetime import datetime

try:
    from google.adk.agents import LlmAgent
    HAS_ADK = True
except ImportError:
    HAS_ADK = False
    LlmAgent = None  # type: ignore

from config.settings import get_model_name


EXECUTE_AGENT_PROMPT = """
Execute approved budget recommendations. For hackathon, this is MOCK ONLY.

## INPUT
List of approved recommendations from Recommend Agent

## OUTPUT
{
  "executed": [
    {
      "ad_name": "...",
      "action_taken": "SCALED|REDUCED|PAUSED",
      "old_budget": <number>,
      "new_budget": <number>,
      "status": "SUCCESS|MOCK",
      "message": "Budget updated from $X to $Y"
    }
  ],
  "summary": "Executed N actions affecting $X in spend"
}

## MOCK MODE
Return success with "[MOCK]" prefix in messages. No actual API calls.
"""


class ExecuteAgent:
    """Agent that executes approved budget recommendations."""

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode

        if HAS_ADK and LlmAgent:
            self.agent = LlmAgent(
                name="execute_agent",
                model=get_model_name(),
                description="Executes approved budget recommendations",
                instruction=EXECUTE_AGENT_PROMPT,
            )
        else:
            self.agent = None

    async def execute(
        self,
        recommendations: List[Dict[str, Any]],
        approved_ids: List[str] = None
    ) -> Dict[str, Any]:
        """
        Execute approved recommendations.

        Args:
            recommendations: List of recommendations from RecommendAgent
            approved_ids: List of ad_names to execute. If None, execute all.

        Returns:
            Execution results with status for each action
        """
        executed = []
        total_spend_change = 0

        for rec in recommendations:
            ad_name = rec.get("ad_name", "")

            # Skip if not in approved list (when provided)
            if approved_ids is not None and ad_name not in approved_ids:
                continue

            # Skip non-actionable recommendations
            action = rec.get("action")
            if action in ["MONITOR", "REVIEW", "WAIT"]:
                continue

            result = await self._execute_single(rec)
            executed.append(result)

            # Track spend changes
            change = rec.get("proposed_new_spend", 0) - rec.get("current_spend", 0)
            total_spend_change += change

        return {
            "executed": executed,
            "summary": self._create_summary(executed, total_spend_change),
            "timestamp": datetime.utcnow().isoformat(),
            "mock_mode": self.mock_mode,
        }

    async def _execute_single(
        self,
        recommendation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single recommendation."""
        ad_name = recommendation.get("ad_name", "unknown")
        action = recommendation.get("action", "UNKNOWN")
        old_budget = recommendation.get("current_spend", 0)
        new_budget = recommendation.get("proposed_new_spend", 0)

        # Map action to past tense
        action_taken = {
            "SCALE": "SCALED",
            "REDUCE": "REDUCED",
            "PAUSE": "PAUSED",
        }.get(action, action)

        # Create message
        if action == "PAUSE":
            message = f"Budget paused. Was ${old_budget:,.0f}"
        elif action == "SCALE":
            change = new_budget - old_budget
            message = f"Budget increased by ${change:,.0f} (${old_budget:,.0f} → ${new_budget:,.0f})"
        elif action == "REDUCE":
            change = old_budget - new_budget
            message = f"Budget reduced by ${change:,.0f} (${old_budget:,.0f} → ${new_budget:,.0f})"
        else:
            message = f"Budget updated: ${old_budget:,.0f} → ${new_budget:,.0f}"

        # Add mock prefix if in mock mode
        if self.mock_mode:
            message = f"[MOCK] {message}"
            status = "MOCK"
        else:
            # TODO: Implement actual API calls to ad platforms
            status = "SUCCESS"

        return {
            "ad_name": ad_name,
            "action_taken": action_taken,
            "old_budget": old_budget,
            "new_budget": new_budget,
            "status": status,
            "message": message,
            "rationale": recommendation.get("rationale", ""),
        }

    def _create_summary(
        self,
        executed: List[Dict[str, Any]],
        total_spend_change: float
    ) -> str:
        """Create a summary of executed actions."""
        if not executed:
            return "No actions executed"

        action_counts = {}
        for result in executed:
            action = result.get("action_taken", "UNKNOWN")
            action_counts[action] = action_counts.get(action, 0) + 1

        parts = []
        for action, count in action_counts.items():
            parts.append(f"{count} {action.lower()}")

        action_summary = ", ".join(parts)

        if total_spend_change > 0:
            spend_summary = f"+${total_spend_change:,.0f} in spend"
        elif total_spend_change < 0:
            spend_summary = f"-${abs(total_spend_change):,.0f} in spend"
        else:
            spend_summary = "no net spend change"

        prefix = "[MOCK] " if self.mock_mode else ""
        return f"{prefix}Executed {len(executed)} actions ({action_summary}). Net effect: {spend_summary}"
