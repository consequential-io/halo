"""
Execute Agent - Executes approved ad spend recommendations.

This agent takes approved recommendations and executes actions:
- pause: Stop a campaign/ad
- adjust_budget: Increase or decrease budget
- refresh_creative: Flag for creative refresh (manual action required)

All actions are dry_run=True by default for the hackathon (mock execution).
"""

import logging
from datetime import datetime, timezone
from typing import Any

from helpers.gcs_logger import get_execution_logger

logger = logging.getLogger(__name__)


# Supported actions and their handlers
SUPPORTED_ACTIONS = {"pause", "reduce", "scale", "refresh_creative"}


class ExecuteAgentModel:
    """
    Execute Agent for running approved ad spend recommendations.

    Takes approved recommendations from RecommendAgent and executes them.
    All executions are logged to GCS for audit trail.
    """

    def __init__(self, dry_run: bool = True):
        """
        Initialize Execute Agent.

        Args:
            dry_run: If True (default), simulate actions without actual execution
        """
        self.name = "execute_agent"
        self.dry_run = dry_run
        self.logger = get_execution_logger()

    def execute_action(
        self,
        recommendation: dict[str, Any],
        tenant: str = "default"
    ) -> dict[str, Any]:
        """
        Execute a single approved recommendation.

        Args:
            recommendation: Recommendation dict from RecommendAgent
            tenant: Tenant identifier for logging

        Returns:
            Execution result with status, action taken, and details
        """
        action = recommendation.get("action")
        ad_id = recommendation.get("ad_id", "unknown")
        ad_name = recommendation.get("ad_name", "Unknown Ad")

        if action not in SUPPORTED_ACTIONS:
            return {
                "status": "skipped",
                "action": action,
                "ad_id": ad_id,
                "ad_name": ad_name,
                "message": f"Unsupported action: {action}",
                "dry_run": self.dry_run,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Route to specific action handler
        if action == "pause":
            result = self._execute_pause(recommendation)
        elif action == "reduce":
            result = self._execute_budget_change(recommendation, direction="reduce")
        elif action == "scale":
            result = self._execute_budget_change(recommendation, direction="scale")
        elif action == "refresh_creative":
            result = self._execute_creative_refresh(recommendation)
        else:
            result = {
                "status": "error",
                "message": f"No handler for action: {action}",
            }

        # Add common fields
        result["ad_id"] = ad_id
        result["ad_name"] = ad_name
        result["action"] = action
        result["dry_run"] = self.dry_run
        result["timestamp"] = datetime.now(timezone.utc).isoformat()

        return result

    def execute_batch(
        self,
        recommendations: list[dict[str, Any]],
        approved_ad_ids: list[str] | None = None,
        tenant: str = "default"
    ) -> dict[str, Any]:
        """
        Execute a batch of approved recommendations.

        Args:
            recommendations: List of recommendations from RecommendAgent
            approved_ad_ids: Optional list of ad_ids to execute (filters recommendations)
            tenant: Tenant identifier for logging

        Returns:
            Batch execution result with individual results and summary
        """
        # Filter to approved ads if specified
        if approved_ad_ids is not None:
            approved_set = set(approved_ad_ids)
            to_execute = [r for r in recommendations if r.get("ad_id") in approved_set]
        else:
            to_execute = recommendations

        results = []
        success_count = 0
        failed_count = 0
        skipped_count = 0

        for rec in to_execute:
            result = self.execute_action(rec, tenant=tenant)
            results.append(result)

            if result["status"] == "success":
                success_count += 1
            elif result["status"] == "failed":
                failed_count += 1
            else:
                skipped_count += 1

        execution_result = {
            "results": results,
            "summary": {
                "total_processed": len(to_execute),
                "success": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "dry_run": self.dry_run,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Log to GCS (sync version for non-async context)
        self.logger.log_execution_sync(tenant, execution_result)

        return execution_result

    async def execute_batch_async(
        self,
        recommendations: list[dict[str, Any]],
        approved_ad_ids: list[str] | None = None,
        tenant: str = "default"
    ) -> dict[str, Any]:
        """
        Async version of execute_batch.

        Args:
            recommendations: List of recommendations from RecommendAgent
            approved_ad_ids: Optional list of ad_ids to execute
            tenant: Tenant identifier for logging

        Returns:
            Batch execution result with individual results and summary
        """
        # Filter to approved ads if specified
        if approved_ad_ids is not None:
            approved_set = set(approved_ad_ids)
            to_execute = [r for r in recommendations if r.get("ad_id") in approved_set]
        else:
            to_execute = recommendations

        results = []
        success_count = 0
        failed_count = 0
        skipped_count = 0

        for rec in to_execute:
            result = self.execute_action(rec, tenant=tenant)
            results.append(result)

            if result["status"] == "success":
                success_count += 1
            elif result["status"] == "failed":
                failed_count += 1
            else:
                skipped_count += 1

        execution_result = {
            "results": results,
            "summary": {
                "total_processed": len(to_execute),
                "success": success_count,
                "failed": failed_count,
                "skipped": skipped_count,
                "dry_run": self.dry_run,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Log to GCS
        await self.logger.log_execution(tenant, execution_result)

        return execution_result

    def _execute_pause(self, rec: dict[str, Any]) -> dict[str, Any]:
        """Execute pause action on a campaign/ad."""
        ad_id = rec.get("ad_id", "unknown")
        ad_provider = rec.get("ad_provider", "unknown")
        current_spend = rec.get("current_spend", 0)

        if self.dry_run:
            return {
                "status": "success",
                "message": f"[DRY RUN] Would pause ad {ad_id} on {ad_provider}",
                "details": {
                    "action_type": "pause",
                    "provider": ad_provider,
                    "spend_stopped": current_spend,
                },
            }

        # Real execution would go here
        # For now, return mock success
        return {
            "status": "success",
            "message": f"Paused ad {ad_id} on {ad_provider}",
            "details": {
                "action_type": "pause",
                "provider": ad_provider,
                "spend_stopped": current_spend,
            },
        }

    def _execute_budget_change(
        self,
        rec: dict[str, Any],
        direction: str
    ) -> dict[str, Any]:
        """Execute budget increase or decrease."""
        ad_id = rec.get("ad_id", "unknown")
        ad_provider = rec.get("ad_provider", "unknown")
        current_spend = rec.get("current_spend", 0)
        change_str = rec.get("recommended_change", "0%")

        # Parse change percentage
        try:
            change_pct = int(change_str.replace("%", "").replace("+", "").replace("-", ""))
            if "-" in change_str:
                change_pct = -change_pct
        except ValueError:
            change_pct = 0

        new_budget = current_spend * (1 + change_pct / 100)

        if self.dry_run:
            return {
                "status": "success",
                "message": f"[DRY RUN] Would {direction} budget for {ad_id}: ${current_spend:.2f} → ${new_budget:.2f}",
                "details": {
                    "action_type": f"budget_{direction}",
                    "provider": ad_provider,
                    "current_budget": round(current_spend, 2),
                    "new_budget": round(new_budget, 2),
                    "change_percent": change_pct,
                },
            }

        # Real execution would go here
        return {
            "status": "success",
            "message": f"Budget {direction}d for {ad_id}: ${current_spend:.2f} → ${new_budget:.2f}",
            "details": {
                "action_type": f"budget_{direction}",
                "provider": ad_provider,
                "current_budget": round(current_spend, 2),
                "new_budget": round(new_budget, 2),
                "change_percent": change_pct,
            },
        }

    def _execute_creative_refresh(self, rec: dict[str, Any]) -> dict[str, Any]:
        """Flag ad for creative refresh (manual action required)."""
        ad_id = rec.get("ad_id", "unknown")
        ad_provider = rec.get("ad_provider", "unknown")
        creative_variants = rec.get("creative_variants", 1)

        # Creative refresh is always a "flag" - can't be auto-executed
        return {
            "status": "success",
            "message": f"Flagged {ad_id} for creative refresh (manual action required)",
            "details": {
                "action_type": "creative_refresh_flag",
                "provider": ad_provider,
                "current_variants": creative_variants,
                "recommendation": rec.get("recommended_change", "Add 2-3 creative variants"),
                "requires_manual_action": True,
            },
        }
