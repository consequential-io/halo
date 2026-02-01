"""RCA Agent - Agentic Root Cause Analysis for ad performance issues."""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional, Literal

logger = logging.getLogger(__name__)

# IMPORTANT: Set API key before importing ADK
from config.settings import settings, get_google_api_key
_api_key = get_google_api_key()

try:
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools import FunctionTool
    from google.genai import types
    HAS_ADK = True
except ImportError:
    HAS_ADK = False
    LlmAgent = None
    Runner = None
    FunctionTool = None

from helpers.rca_checks import (
    check_budget_exhaustion,
    check_creative_fatigue,
    check_cpm_spike,
    check_landing_page,
    check_tracking,
    check_seasonality,
    check_bid_cap_too_low,
    check_audience_exhaustion,
    check_recent_changes,
)


RCA_AGENT_PROMPT = """
You are an RCA (Root Cause Analysis) agent for ad performance issues.

## YOUR TASK
Given an anomaly (e.g., "ROAS dropped 60%"), determine the root cause by calling diagnostic tools.
Think step-by-step, call tools to gather evidence, and identify the most likely root cause.

## AVAILABLE TOOLS (Use these to investigate)

### Implemented Tools (will return real data):

1. check_budget_exhaustion(ad_name, days, tenant)
   - Use when: Spend or impressions dropped suddenly
   - Returns: budget utilization %, daily budget, campaign cap

2. check_creative_fatigue(ad_name, days, tenant)
   - Use when: CTR or engagement declining over time
   - Returns: CTR trend %, days running

3. check_cpm_spike(ad_name, days, tenant)
   - Use when: Costs increased, ROAS dropped but engagement stable
   - Returns: CPM change %, current vs baseline CPM

4. check_landing_page(ad_name, days, tenant)
   - Use when: CTR stable but conversions dropped
   - Returns: funnel metrics (add-to-cart rate, checkout rate changes)

5. check_tracking(ad_name, days, tenant)
   - Use when: Getting clicks but zero conversions for extended period
   - Returns: clicks, orders, add-to-cart counts

6. check_seasonality(ad_name, tenant)
   - Use when: Multiple ads/channels dropped together
   - Returns: comparison to 7d and 30d ago, whether all channels affected

### Future Tools (will return "not implemented"):

7. check_bid_cap_too_low - Needs bid_cap from Ads API
8. check_audience_exhaustion - Needs frequency/reach from Ads API
9. check_recent_changes - Needs change logs from Ads API

## REASONING APPROACH

1. Analyze the anomaly type (which metric dropped/spiked)
2. Form hypotheses about likely causes
3. Call the MOST RELEVANT tool first
4. Interpret the result - does it explain the anomaly?
5. If not conclusive, call another tool
6. STOP when you find a clear root cause
7. If no clear cause found after 3-4 checks, conclude "UNKNOWN" with suggestions

## ANOMALY TYPE → LIKELY CAUSES

| Anomaly | Check First | Then Check |
|---------|-------------|------------|
| ROAS dropped | check_cpm_spike | check_creative_fatigue, check_landing_page |
| Spend dropped | check_budget_exhaustion | check_cpm_spike |
| CTR dropped | check_creative_fatigue | check_seasonality |
| CPA spiked | check_landing_page | check_cpm_spike |
| CPM spiked | check_cpm_spike | check_seasonality |

## OUTPUT FORMAT

After your investigation, provide a JSON summary:
{
  "anomaly_summary": "<what was detected>",
  "checks_performed": [
    {"tool": "check_cpm_spike", "result_summary": "CPM normal (+5%)", "conclusive": false},
    {"tool": "check_creative_fatigue", "result_summary": "CTR dropped 28%", "conclusive": true}
  ],
  "root_cause": "<the identified cause or UNKNOWN>",
  "confidence": "HIGH|MEDIUM|LOW",
  "evidence": "<specific numbers that support this conclusion>",
  "recommended_action": "<what to do about it>",
  "impact_estimate": "<estimated cost/revenue impact if known>"
}

## IMPORTANT
- Call tools with: ad_name="<exact ad name>", days=7, tenant="wh" (or "tl")
- Don't guess - use the tools to get real data
- One tool call at a time, interpret before calling the next
- Be specific in your conclusions - cite actual numbers
"""


class RCAAgent:
    """
    Agentic RCA system that investigates anomalies using diagnostic tools.

    The agent decides which diagnostic checks to run based on the anomaly type,
    interprets results, and determines root cause.
    """

    def __init__(self, tenant: Literal["tl", "wh"] = "wh"):
        self.tenant = tenant

        if not HAS_ADK:
            raise ImportError("Google ADK not installed")

        if not _api_key:
            raise ValueError("Google API key not found")

        # Create tools for the agent
        self.tools = [
            FunctionTool(func=check_budget_exhaustion),
            FunctionTool(func=check_creative_fatigue),
            FunctionTool(func=check_cpm_spike),
            FunctionTool(func=check_landing_page),
            FunctionTool(func=check_tracking),
            FunctionTool(func=check_seasonality),
            # Future tools (return "not implemented")
            FunctionTool(func=check_bid_cap_too_low),
            FunctionTool(func=check_audience_exhaustion),
            FunctionTool(func=check_recent_changes),
        ]

        # Create the ADK LlmAgent
        self.agent = LlmAgent(
            name="rca_agent",
            model=settings.gemini_model,
            description="Investigates ad performance anomalies to find root causes",
            instruction=RCA_AGENT_PROMPT,
            tools=self.tools,
        )

        # Session service for ADK
        self.session_service = InMemorySessionService()

        # Runner for executing the agent
        self.runner = Runner(
            agent=self.agent,
            app_name="agatha_rca",
            session_service=self.session_service,
        )

    async def investigate(
        self,
        anomaly: Dict[str, Any],
        max_turns: int = 10
    ) -> Dict[str, Any]:
        """
        Investigate an anomaly to find root cause.

        Args:
            anomaly: Dict describing the anomaly (from AnomalyDetector)
            max_turns: Maximum number of agent turns (tool calls)

        Returns:
            Dict with root cause analysis results
        """
        ad_name = anomaly.get("ad_name", "Unknown")
        metric = anomaly.get("metric", "unknown")
        direction = anomaly.get("direction", "changed")
        pct_change = anomaly.get("pct_change", 0)
        z_score = anomaly.get("z_score", 0)

        # Build the investigation prompt
        prompt = f"""
Investigate this anomaly:

Ad Name: {ad_name}
Provider: {anomaly.get("ad_provider", "Unknown")}
Metric: {metric.upper()}
Change: {direction} {abs(pct_change):.1f}%
Current Value: {anomaly.get("current_value", 0):.2f}
Baseline Mean: {anomaly.get("baseline_mean", 0):.2f}
Z-Score: {z_score:.2f}
Severity: {anomaly.get("severity", "UNKNOWN")}

Use the diagnostic tools to determine the ROOT CAUSE of this anomaly.
The tenant is "{self.tenant}".

Start by analyzing what could cause a {metric.upper()} {direction.lower()} and call the most relevant tool.
"""

        logger.info(f"[RCA] Investigating anomaly: {ad_name} - {metric} {direction} {pct_change:.1f}%")

        # Create session
        session = await self.session_service.create_session(
            app_name="agatha_rca",
            user_id="rca_user"
        )

        # Create message
        user_message = types.Content(
            role="user",
            parts=[types.Part(text=prompt)]
        )

        # Run the agent
        response_text = ""
        tool_calls = []

        try:
            async for event in self.runner.run_async(
                user_id="rca_user",
                session_id=session.id,
                new_message=user_message,
            ):
                # Collect response
                if hasattr(event, 'content') and event.content:
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text += part.text
                            # Track tool calls
                            if hasattr(part, 'function_call') and part.function_call:
                                tool_calls.append(part.function_call.name)

        except Exception as e:
            logger.error(f"[RCA] Investigation failed: {e}")
            return {
                "anomaly_summary": f"{ad_name}: {metric} {direction} {pct_change:.1f}%",
                "error": str(e),
                "root_cause": "ERROR",
                "confidence": "LOW"
            }

        logger.info(f"[RCA] Investigation complete. Tools called: {tool_calls}")

        # Parse the response
        return self._parse_rca_response(response_text, anomaly, tool_calls)

    def _parse_rca_response(
        self,
        response_text: str,
        anomaly: Dict[str, Any],
        tool_calls: List[str]
    ) -> Dict[str, Any]:
        """Parse the agent's response into structured output."""
        # Try to extract JSON from response
        try:
            # Find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                result = json.loads(json_str)
                result["tools_called"] = tool_calls
                result["raw_response"] = response_text
                return result
        except json.JSONDecodeError:
            pass

        # Fallback: extract key information from text
        return {
            "anomaly_summary": f"{anomaly.get('ad_name')}: {anomaly.get('metric')} {anomaly.get('direction')} {anomaly.get('pct_change', 0):.1f}%",
            "checks_performed": [{"tool": t, "result_summary": "See raw response"} for t in tool_calls],
            "root_cause": self._extract_root_cause(response_text),
            "confidence": "MEDIUM",
            "evidence": "See raw response for details",
            "recommended_action": self._extract_recommendation(response_text),
            "tools_called": tool_calls,
            "raw_response": response_text
        }

    def _extract_root_cause(self, text: str) -> str:
        """Try to extract root cause from text."""
        text_lower = text.lower()

        causes = {
            "creative fatigue": "Creative Fatigue",
            "cpm spike": "CPM Spike",
            "budget exhaust": "Budget Exhaustion",
            "landing page": "Landing Page Issue",
            "tracking": "Tracking Issue",
            "seasonal": "Seasonality",
            "audience exhaust": "Audience Exhaustion",
        }

        for keyword, cause in causes.items():
            if keyword in text_lower:
                return cause

        return "UNKNOWN"

    def _extract_recommendation(self, text: str) -> str:
        """Try to extract recommendation from text."""
        # Look for action keywords
        if "pause" in text.lower():
            return "Consider pausing underperforming creative"
        if "refresh" in text.lower() or "new creative" in text.lower():
            return "Refresh creative with new variants"
        if "budget" in text.lower():
            return "Review and adjust budget settings"
        if "landing page" in text.lower():
            return "Check landing page for issues"

        return "Manual review recommended"


async def investigate_anomaly(
    anomaly: Dict[str, Any],
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """
    Convenience function to investigate a single anomaly.

    Args:
        anomaly: Anomaly dict from AnomalyDetector
        tenant: Tenant identifier

    Returns:
        RCA results dict
    """
    agent = RCAAgent(tenant=tenant)
    return await agent.investigate(anomaly)


async def run_full_rca(
    tenant: Literal["tl", "wh"] = "wh",
    baseline_days: int = 30,
    current_days: int = 3,
    min_spend: float = 1000,
    z_threshold: float = 2.0,
    max_anomalies: int = 5
) -> Dict[str, Any]:
    """
    Run full RCA pipeline: detect anomalies then investigate each.

    Args:
        tenant: Tenant identifier
        baseline_days: Days for baseline calculation
        current_days: Recent days to analyze
        min_spend: Minimum spend threshold
        z_threshold: Z-score threshold for anomaly detection
        max_anomalies: Maximum anomalies to investigate

    Returns:
        Dict with all anomalies and their RCA results
    """
    from models.anomaly_agent import detect_anomalies

    # Step 1: Detect anomalies
    logger.info("[RCA] Step 1: Detecting anomalies...")
    detection_result = await detect_anomalies(
        tenant=tenant,
        baseline_days=baseline_days,
        current_days=current_days,
        min_spend=min_spend,
        z_threshold=z_threshold
    )

    anomalies = detection_result.get("anomalies", [])[:max_anomalies]
    logger.info(f"[RCA] Found {len(anomalies)} anomalies to investigate")

    # Step 2: Investigate each anomaly
    rca_results = []
    agent = RCAAgent(tenant=tenant)

    for i, anomaly in enumerate(anomalies):
        logger.info(f"[RCA] Investigating anomaly {i+1}/{len(anomalies)}: {anomaly.get('ad_name')}")
        result = await agent.investigate(anomaly)
        rca_results.append({
            "anomaly": anomaly,
            "investigation": result
        })

    return {
        "detection_summary": {
            "total_anomalies": detection_result.get("anomalies_detected", 0),
            "investigated": len(rca_results),
            "baseline_period": detection_result.get("baseline_period"),
            "current_period": detection_result.get("current_period"),
        },
        "results": rca_results
    }
