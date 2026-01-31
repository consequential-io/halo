"""Recommend Agent - Generates actionable budget recommendations using Google ADK."""

import json
import logging
import uuid
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# IMPORTANT: Set API key before importing ADK
from config.settings import settings, get_google_api_key
_api_key = get_google_api_key()  # This sets GOOGLE_API_KEY env var

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from helpers.tools import get_top_performers_tool, get_underperformers_tool


RECOMMEND_AGENT_PROMPT = """
Generate actionable budget recommendations from ad analysis results.

## RULES
1. Only recommend actions for ads with HIGH or MEDIUM confidence
2. Always cite the source metrics in your recommendation
3. Always show the calculation for expected impact
4. Be specific about dollar amounts
5. Return ONLY valid JSON - no markdown, no explanation

## ACTION RULES
- SCALE: For GOOD ads → increase budget by 50-100% (higher ROAS ratio = higher %)
- REDUCE: For BAD ads (low ROAS) → decrease budget by 50%
- PAUSE: For BAD ads (zero ROAS) → stop spending entirely
- MONITOR: For OK ads → no budget change needed
- REVIEW: For WARNING ads → suggest optimization, not budget change

## SCALING GUIDELINES
- ROAS >= 4× avg: Scale by 100% (double budget)
- ROAS >= 3× avg: Scale by 75%
- ROAS >= 2× avg: Scale by 50%
- ROAS >= 1.5× avg: Scale by 30%

## AVAILABLE TOOLS

You have access to these tools for deeper analysis:

1. get_top_performers(tenant, days, limit, min_spend, use_fixture)
   - Returns top performing ads sorted by ROAS descending
   - Use to find candidates for SCALE recommendations
   - Use to understand what "good" looks like in this account

2. get_underperformers(tenant, days, limit, min_spend, use_fixture)
   - Returns underperforming ads (ROAS below account average)
   - Use to find candidates for PAUSE/REDUCE recommendations
   - Shows total_underperformer_spend to quantify waste

Parameters:
- tenant: "tl" or "wh" (ThirdLove or WhisperingHomes)
- days: number of days (default 30)
- limit: max ads to return (default 10)
- min_spend: minimum spend threshold (default 1000)
- use_fixture: True for test data, False for BigQuery

## OUTPUT FORMAT
For each ad in the analysis, return a JSON object with this structure:
{
  "ad_name": "<exact name from analysis>",
  "action": "SCALE|REDUCE|PAUSE|MONITOR|REVIEW",
  "current_spend": <number>,
  "change_percentage": <number>,
  "proposed_new_spend": <number>,
  "expected_impact": {
    "calculation": "<show the math>",
    "estimated_revenue_change": <number>
  },
  "confidence": "HIGH|MEDIUM|LOW",
  "rationale": "<cite specific metrics from analysis>"
}

Return a JSON array of recommendations. Skip WAIT classifications and LOW confidence ads.

## EXAMPLE

Analysis Input:
{
  "ad_name": "Thirdlove® Bras",
  "classification": "GOOD",
  "recommended_action": "SCALE",
  "confidence": "HIGH",
  "metrics": {"spend": 212297, "roas": 29.58, "account_avg_roas": 6.90}
}

Output:
{
  "ad_name": "Thirdlove® Bras",
  "action": "SCALE",
  "current_spend": 212297,
  "change_percentage": 100,
  "proposed_new_spend": 424594,
  "expected_impact": {
    "calculation": "$212,297 increase × 29.58 ROAS = $6,279,745 expected revenue",
    "estimated_revenue_change": 6279745
  },
  "confidence": "HIGH",
  "rationale": "ROAS of 29.58 is 4.3× account average (6.90). Strong performer with proven returns."
}
"""


class RecommendAgent:
    """Agent that generates budget recommendations using Google ADK LlmAgent."""

    def __init__(self):
        # API key is already set at module import time
        if not _api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY env var or "
                "ensure access to GCP Secret Manager."
            )

        # Create the ADK LlmAgent with tool access
        tools = []
        if get_top_performers_tool:
            tools.append(get_top_performers_tool)
        if get_underperformers_tool:
            tools.append(get_underperformers_tool)

        self.agent = LlmAgent(
            name="recommend_agent",
            model=settings.gemini_model,
            description="Generates actionable budget recommendations from ad analysis",
            instruction=RECOMMEND_AGENT_PROMPT,
            tools=tools,
        )

        # Session service for ADK
        self.session_service = InMemorySessionService()

        # Runner for executing the agent
        self.runner = Runner(
            agent=self.agent,
            app_name="agatha",
            session_service=self.session_service,
        )

    async def recommend(
        self,
        analysis_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations from analysis results using LLM.

        Args:
            analysis_results: List of analysis outputs from AnalyzeAgent

        Returns:
            List of recommendations with budget changes and expected impact
        """
        # Filter out WAIT and LOW confidence results
        actionable = [
            r for r in analysis_results
            if r.get("classification") != "WAIT" and r.get("confidence") != "LOW"
        ]

        if not actionable:
            return []

        # Call LLM for recommendations
        recommendations = await self._call_agent(actionable)
        return recommendations

    async def _call_agent(
        self,
        analysis_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Call the ADK LlmAgent to generate recommendations."""
        # Build the user message
        user_message_text = f"""Generate budget recommendations for these analyzed ads:

{json.dumps(analysis_results, indent=2)}

Return ONLY a valid JSON array of recommendations. No markdown, no explanation."""

        # Log LLM input
        logger.info(f"[AI-INPUT] recommend for {len(analysis_results)} ads")
        logger.debug(f"[AI-INPUT-FULL] analysis_results={json.dumps(analysis_results, indent=2)}")

        # Create a unique session for this analysis
        session = await self.session_service.create_session(
            app_name="agatha",
            user_id="agatha_user"
        )

        # Create Content object for the message
        user_message = types.Content(
            role="user",
            parts=[types.Part(text=user_message_text)]
        )

        # Run the agent using ADK Runner
        response_text = ""
        async for event in self.runner.run_async(
            user_id="agatha_user",
            session_id=session.id,
            new_message=user_message,
        ):
            # Collect the response text from events
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts'):
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text

        # Log LLM output
        logger.info(f"[AI-OUTPUT] recommendations response_length={len(response_text)}")
        logger.debug(f"[AI-OUTPUT-FULL] response={response_text}")

        # Parse the response
        return self._parse_llm_response(response_text, analysis_results)

    def _parse_llm_response(
        self,
        response_text: str,
        analysis_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Parse the LLM response into a list of recommendations."""
        try:
            text = response_text.strip()

            # Remove markdown code blocks if present
            if text.startswith("```"):
                lines = text.split("\n")
                json_lines = []
                in_block = False
                for line in lines:
                    if line.startswith("```") and not in_block:
                        in_block = True
                        continue
                    elif line.startswith("```") and in_block:
                        break
                    elif in_block:
                        json_lines.append(line)
                text = "\n".join(json_lines)

            # Parse JSON
            result = json.loads(text)

            # Ensure it's a list
            if isinstance(result, dict):
                result = [result]

            logger.info(f"[PARSE-SUCCESS] parsed {len(result)} recommendations from LLM")
            return result

        except json.JSONDecodeError as e:
            # Fallback to rule-based recommendations
            logger.warning(f"[PARSE-FAILED] JSON parsing failed: {e}, using rule-based fallback")
            return self._generate_fallback_recommendations(analysis_results)

    def _generate_fallback_recommendations(
        self,
        analysis_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate rule-based recommendations as fallback."""
        recommendations = []

        for analysis in analysis_results:
            classification = analysis.get("classification")
            confidence = analysis.get("confidence")
            action = analysis.get("recommended_action")
            metrics = analysis.get("metrics", {})

            if confidence == "LOW" or classification == "WAIT":
                continue

            ad_name = analysis.get("ad_name", "unknown")
            spend = metrics.get("spend", 0)
            roas = metrics.get("roas", 0)
            account_avg = metrics.get("account_avg_roas", 1)

            rec = None
            if action == "SCALE":
                rec = self._create_scale_recommendation(
                    ad_name, spend, roas, account_avg, confidence
                )
            elif action == "REDUCE":
                rec = self._create_reduce_recommendation(
                    ad_name, spend, roas, account_avg, confidence
                )
            elif action == "PAUSE":
                rec = self._create_pause_recommendation(
                    ad_name, spend, roas, confidence
                )
            elif action == "MONITOR":
                rec = self._create_monitor_recommendation(
                    ad_name, spend, roas, account_avg, confidence
                )
            elif action == "REVIEW":
                rec = self._create_review_recommendation(
                    ad_name, spend, roas, account_avg, confidence
                )

            if rec:
                recommendations.append(rec)

        return recommendations

    def _create_scale_recommendation(
        self,
        ad_name: str,
        spend: float,
        roas: float,
        account_avg: float,
        confidence: str
    ) -> Dict[str, Any]:
        """Create a SCALE recommendation."""
        roas_ratio = roas / account_avg if account_avg > 0 else 0

        if roas_ratio >= 4:
            change_pct = 100
        elif roas_ratio >= 3:
            change_pct = 75
        elif roas_ratio >= 2:
            change_pct = 50
        else:
            change_pct = 30

        increase = spend * (change_pct / 100)
        new_spend = spend + increase
        expected_revenue = increase * roas

        return {
            "ad_name": ad_name,
            "action": "SCALE",
            "current_spend": spend,
            "change_percentage": change_pct,
            "proposed_new_spend": new_spend,
            "expected_impact": {
                "calculation": f"${increase:,.0f} increase × {roas:.2f} ROAS = ${expected_revenue:,.0f}",
                "estimated_revenue_change": expected_revenue,
            },
            "confidence": confidence,
            "rationale": (
                f"ROAS of {roas:.2f} is {roas_ratio:.1f}× account average ({account_avg:.2f}). "
                f"Strong performer with proven returns."
            ),
        }

    def _create_reduce_recommendation(
        self,
        ad_name: str,
        spend: float,
        roas: float,
        account_avg: float,
        confidence: str
    ) -> Dict[str, Any]:
        """Create a REDUCE recommendation."""
        change_pct = -50
        reduction = spend * 0.5
        new_spend = spend - reduction

        roas_ratio = roas / account_avg if account_avg > 0 else 0
        opportunity_cost = reduction * (account_avg - roas)

        return {
            "ad_name": ad_name,
            "action": "REDUCE",
            "current_spend": spend,
            "change_percentage": change_pct,
            "proposed_new_spend": new_spend,
            "expected_impact": {
                "calculation": (
                    f"Reduce ${spend:,.0f} by 50% = ${reduction:,.0f} saved. "
                    f"Reallocating could yield ${opportunity_cost:,.0f} more at avg ROAS."
                ),
                "estimated_revenue_change": opportunity_cost,
            },
            "confidence": confidence,
            "rationale": (
                f"ROAS of {roas:.2f} is {roas_ratio:.2f}× account average ({account_avg:.2f}). "
                f"Significantly underperforming."
            ),
        }

    def _create_pause_recommendation(
        self,
        ad_name: str,
        spend: float,
        roas: float,
        confidence: str
    ) -> Dict[str, Any]:
        """Create a PAUSE recommendation."""
        return {
            "ad_name": ad_name,
            "action": "PAUSE",
            "current_spend": spend,
            "change_percentage": -100,
            "proposed_new_spend": 0,
            "expected_impact": {
                "calculation": f"Stop ${spend:,.0f} waste with zero returns",
                "estimated_revenue_change": 0,
            },
            "confidence": confidence,
            "rationale": f"Zero ROAS after ${spend:,.0f} spent. No revenue generated.",
        }

    def _create_monitor_recommendation(
        self,
        ad_name: str,
        spend: float,
        roas: float,
        account_avg: float,
        confidence: str
    ) -> Dict[str, Any]:
        """Create a MONITOR recommendation (no budget change)."""
        roas_ratio = roas / account_avg if account_avg > 0 else 0

        return {
            "ad_name": ad_name,
            "action": "MONITOR",
            "current_spend": spend,
            "change_percentage": 0,
            "proposed_new_spend": spend,
            "expected_impact": {
                "calculation": "No budget change. Continue current spend.",
                "estimated_revenue_change": 0,
            },
            "confidence": confidence,
            "rationale": (
                f"ROAS of {roas:.2f} is {roas_ratio:.1f}× account average. "
                f"Performance is solid. Maintain current budget."
            ),
        }

    def _create_review_recommendation(
        self,
        ad_name: str,
        spend: float,
        roas: float,
        account_avg: float,
        confidence: str
    ) -> Dict[str, Any]:
        """Create a REVIEW recommendation (optimization needed)."""
        roas_ratio = roas / account_avg if account_avg > 0 else 0
        pct_below = (1 - roas_ratio) * 100

        return {
            "ad_name": ad_name,
            "action": "REVIEW",
            "current_spend": spend,
            "change_percentage": 0,
            "proposed_new_spend": spend,
            "expected_impact": {
                "calculation": (
                    f"If optimized to avg ROAS, additional revenue = "
                    f"${spend:,.0f} × ({account_avg:.2f} - {roas:.2f}) = "
                    f"${spend * (account_avg - roas):,.0f}"
                ),
                "estimated_revenue_change": spend * (account_avg - roas),
            },
            "confidence": confidence,
            "rationale": (
                f"ROAS of {roas:.2f} is {pct_below:.0f}% below account average. "
                f"Review creative and targeting for optimization."
            ),
        }
