"""Analyze Agent - Classifies ad performance with grounded reasoning using Google ADK."""

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

from helpers.validators import validate_analyze_output, handle_validation_failure
from helpers.tools import get_ad_data_tool


ANALYZE_AGENT_PROMPT = """
You are analyzing ad performance data. Your classifications MUST be grounded in actual metrics.

## RULES
1. NEVER invent metrics - only use values from provided data
2. ALWAYS cite specific numbers when making claims
3. ALWAYS compare to account average (provided in context)
4. If data insufficient, classify as WAIT

## CLASSIFICATION GUIDELINES (use judgment for edge cases)
- GOOD: ROAS >= 2× avg, spend >= $1k, days >= 7 → SCALE
- OK: ROAS 1-2× avg, spend >= $1k, days >= 7 → MONITOR
- WARNING: ROAS 0.5-1× avg, spend >= $10k, days >= 7 → REVIEW
- BAD: ROAS < 0.5× avg (spend >= $10k), days >= 7 → REDUCE
- BAD: ROAS = 0 (spend >= $5k), days >= 7 → PAUSE
- WAIT: spend < $1k OR days < 7 → WAIT

IMPORTANT: recommended_action must be exactly ONE of: SCALE, MONITOR, REVIEW, REDUCE, PAUSE, WAIT (never combine like "REDUCE/PAUSE")

## AVAILABLE TOOL

You have access to: get_ad_data(tenant, days, use_fixture)
- tenant: "tl" or "wh" (ThirdLove or WhisperingHomes)
- days: number of days of data (default 30)
- use_fixture: True for test data, False for BigQuery

Use this tool if you need to fetch additional ad data for deeper analysis.

These are GUIDELINES. You may deviate with clear reasoning (e.g., "1.95× avg with upward trend → GOOD").

## OUTPUT FORMAT
Return ONLY a valid JSON object with this exact structure (no markdown, no explanation):
{
  "ad_name": "<exact name from data>",
  "metrics": {
    "spend": <actual value>,
    "roas": <actual value>,
    "days_active": <actual value>,
    "account_avg_roas": <actual value>
  },
  "chain_of_thought": {
    "data_extracted": {"spend": <value>, "roas": <value>, "days": <value>},
    "comparison": {"roas_ratio": "<ad_roas> / <avg> = <ratio>×"},
    "qualification": {"spend_ok": true/false, "days_ok": true/false},
    "classification_logic": {"result": "<classification>", "reason": "<why>"},
    "confidence_rationale": {"level": "<level>", "reason": "<why>"}
  },
  "classification": "GOOD|OK|WARNING|BAD|WAIT",
  "recommended_action": "SCALE|MONITOR|REVIEW|REDUCE|PAUSE|WAIT",
  "confidence": "HIGH|MEDIUM|LOW",
  "user_explanation": "<1-2 sentences citing specific numbers>"
}

## EXAMPLES

Example 1 - GOOD SPEND:
Input: {"ad_name": "Thirdlove® Bras", "spend": 212297, "roas": 29.58, "days_active": 287}, account_avg_roas: 6.90
Output: {"ad_name": "Thirdlove® Bras", "metrics": {"spend": 212297, "roas": 29.58, "days_active": 287, "account_avg_roas": 6.90}, "chain_of_thought": {"data_extracted": {"spend": 212297, "roas": 29.58, "days": 287}, "comparison": {"roas_ratio": "29.58 / 6.90 = 4.3×"}, "qualification": {"spend_ok": true, "days_ok": true}, "classification_logic": {"result": "GOOD", "reason": "4.3× avg far exceeds 2× threshold"}, "confidence_rationale": {"level": "HIGH", "reason": "Strong signal with high spend and long duration"}}, "classification": "GOOD", "recommended_action": "SCALE", "confidence": "HIGH", "user_explanation": "ROAS of 29.58 is 4.3× your account average of 6.90. Scale budget by 50-100%."}

Example 2 - BAD SPEND (Zero ROAS):
Input: {"ad_name": "TikTok carousel", "spend": 32646, "roas": 0.0, "days_active": 107}, account_avg_roas: 6.90
Output: {"ad_name": "TikTok carousel", "metrics": {"spend": 32646, "roas": 0.0, "days_active": 107, "account_avg_roas": 6.90}, "chain_of_thought": {"data_extracted": {"spend": 32646, "roas": 0.0, "days": 107}, "comparison": {"roas_ratio": "0.0 / 6.90 = 0×"}, "qualification": {"spend_ok": true, "days_ok": true}, "classification_logic": {"result": "BAD", "reason": "Zero ROAS after $32k and 107 days"}, "confidence_rationale": {"level": "HIGH", "reason": "Zero ROAS is unambiguous"}}, "classification": "BAD", "recommended_action": "PAUSE", "confidence": "HIGH", "user_explanation": "Zero return on $32.6k spent over 107 days. Pause immediately."}

Example 3 - WAIT (Insufficient Data):
Input: {"ad_name": "July Sale", "spend": 14242, "roas": 19.71, "days_active": 6}, account_avg_roas: 6.90
Output: {"ad_name": "July Sale", "metrics": {"spend": 14242, "roas": 19.71, "days_active": 6, "account_avg_roas": 6.90}, "chain_of_thought": {"data_extracted": {"spend": 14242, "roas": 19.71, "days": 6}, "comparison": {"roas_ratio": "19.71 / 6.90 = 2.86×"}, "qualification": {"spend_ok": true, "days_ok": false}, "classification_logic": {"result": "WAIT", "reason": "Only 6 days active, need 7+"}, "confidence_rationale": {"level": "LOW", "reason": "Still in learning phase"}}, "classification": "WAIT", "recommended_action": "WAIT", "confidence": "LOW", "user_explanation": "Excellent ROAS but only 6 days active. Wait 1 more day before decisions."}
"""


class AnalyzeAgent:
    """Agent that analyzes ad performance using Google ADK LlmAgent."""

    def __init__(self):
        # API key is already set at module import time
        if not _api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY env var or "
                "ensure access to GCP Secret Manager."
            )

        # Create the ADK LlmAgent with tool access
        tools = [get_ad_data_tool] if get_ad_data_tool else []
        self.agent = LlmAgent(
            name="analyze_agent",
            model=settings.gemini_model,
            description="Analyzes ad performance data and classifies as GOOD/OK/WARNING/BAD/WAIT with chain-of-thought reasoning",
            instruction=ANALYZE_AGENT_PROMPT,
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

    async def analyze(
        self,
        ad_data: Dict[str, Any],
        max_retries: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Analyze ads and return classifications.

        Args:
            ad_data: Dict with account_avg_roas and list of ads
            max_retries: Maximum retry attempts on validation failure

        Returns:
            List of analysis results, one per ad
        """
        import asyncio

        # Build list of ad inputs
        ad_inputs = [
            {
                "account_avg_roas": ad_data["account_avg_roas"],
                "ad": ad
            }
            for ad in ad_data.get("ads", [])
        ]

        # Run all analyses in parallel
        results = await asyncio.gather(
            *[self._analyze_single_ad(ad_input, max_retries) for ad_input in ad_inputs]
        )

        return list(results)

    async def _analyze_single_ad(
        self,
        ad_input: Dict[str, Any],
        max_retries: int
    ) -> Dict[str, Any]:
        """Analyze a single ad with validation and retry logic."""
        retry_count = 0
        last_feedback = None
        ad_name = ad_input["ad"].get("ad_name", "unknown")

        while retry_count <= max_retries:
            try:
                # Call the LLM agent via ADK
                response = await self._call_agent(ad_input, last_feedback)

                # Validate the response
                is_valid, violations = validate_analyze_output(
                    response,
                    ad_input["ad"],
                    ad_input["account_avg_roas"]
                )

                # Log validation results
                logger.info(f"[VALIDATION] ad={ad_name} valid={is_valid} violations={len(violations)}")
                if not is_valid:
                    logger.warning(f"[VALIDATION-FAILED] ad={ad_name} violations={violations}")

                if is_valid:
                    return response

                # Handle validation failure
                failure_result = handle_validation_failure(
                    response, violations, retry_count
                )

                if failure_result["action"] == "degrade":
                    logger.warning(f"[FALLBACK] ad={ad_name} degraded to MANUAL_REVIEW after {retry_count} retries")
                    return failure_result["result"]

                # Log retry decision
                logger.info(f"[RETRY] ad={ad_name} attempt={retry_count+1} feedback={failure_result['feedback']}")

                # Retry with feedback
                last_feedback = failure_result["feedback"]
                retry_count += 1

            except Exception as e:
                # On error, try to degrade gracefully
                logger.error(f"[ERROR] ad={ad_name} error={str(e)}")
                return self._create_error_response(ad_input["ad"], str(e))

        # Should not reach here
        return self._create_error_response(
            ad_input["ad"],
            "Unable to classify after multiple attempts."
        )

    async def _call_agent(
        self,
        ad_input: Dict[str, Any],
        feedback: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Call the ADK LlmAgent to analyze a single ad."""
        ad = ad_input["ad"]
        account_avg = ad_input["account_avg_roas"]
        ad_name = ad.get("ad_name", "unknown")

        # Build the user message
        user_message_text = f"""Analyze this ad:
Input: {json.dumps(ad)}
Account average ROAS: {account_avg}

Return ONLY a valid JSON object following the output format specified."""

        if feedback:
            user_message_text += f"\n\nPrevious attempt had issues: {', '.join(feedback)}. Please fix these."

        # Log LLM input
        logger.info(f"[AI-INPUT] ad={ad_name} prompt_length={len(user_message_text)}")
        logger.debug(f"[AI-INPUT-FULL] ad={ad_name} prompt={user_message_text}")

        # Create a unique session for this analysis
        session_id = str(uuid.uuid4())

        # Create session first
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
        logger.info(f"[AI-OUTPUT] ad={ad_name} response_length={len(response_text)}")
        logger.debug(f"[AI-OUTPUT-FULL] ad={ad_name} response={response_text}")

        # Parse the response
        return self._parse_llm_response(response_text, ad, account_avg)

    def _parse_llm_response(
        self,
        response_text: str,
        ad: Dict[str, Any],
        account_avg: float
    ) -> Dict[str, Any]:
        """Parse the LLM response into a structured dict."""
        try:
            # Try to extract JSON from the response
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

            # Ensure required fields exist
            if "ad_name" not in result:
                result["ad_name"] = ad.get("ad_name", "unknown")
            if "metrics" not in result:
                result["metrics"] = {
                    "spend": ad["spend"],
                    "roas": ad["roas"],
                    "days_active": ad["days_active"],
                    "account_avg_roas": account_avg,
                }

            return result

        except json.JSONDecodeError:
            # If JSON parsing fails, use fallback extraction
            return self._extract_fields_fallback(response_text, ad, account_avg)

    def _extract_fields_fallback(
        self,
        response_text: str,
        ad: Dict[str, Any],
        account_avg: float
    ) -> Dict[str, Any]:
        """Fallback extraction when JSON parsing fails."""
        classification = "MANUAL_REVIEW"
        action = "REVIEW"
        confidence = "LOW"

        text_upper = response_text.upper()
        for cls in ["GOOD", "OK", "WARNING", "BAD", "WAIT"]:
            if f'"CLASSIFICATION": "{cls}"' in text_upper or f'"CLASSIFICATION":"{cls}"' in text_upper:
                classification = cls
                break
            if f"CLASSIFICATION: {cls}" in text_upper:
                classification = cls
                break

        action_map = {
            "GOOD": "SCALE",
            "OK": "MONITOR",
            "WARNING": "REVIEW",
            "BAD": "REDUCE",
            "WAIT": "WAIT",
        }
        action = action_map.get(classification, "REVIEW")

        if classification == "BAD" and ad["roas"] == 0:
            action = "PAUSE"

        roas_ratio = ad["roas"] / account_avg if account_avg > 0 else 0

        return {
            "ad_name": ad.get("ad_name", "unknown"),
            "metrics": {
                "spend": ad["spend"],
                "roas": ad["roas"],
                "days_active": ad["days_active"],
                "account_avg_roas": account_avg,
            },
            "chain_of_thought": {
                "data_extracted": {
                    "spend": ad["spend"],
                    "roas": ad["roas"],
                    "days": ad["days_active"]
                },
                "comparison": {
                    "roas_ratio": f"{ad['roas']} / {account_avg} = {roas_ratio:.2f}×"
                },
                "qualification": {
                    "spend_ok": ad["spend"] >= 1000,
                    "days_ok": ad["days_active"] >= 7
                },
                "classification_logic": {
                    "result": classification,
                    "reason": "Extracted from LLM response"
                },
                "confidence_rationale": {
                    "level": confidence,
                    "reason": "Fallback parsing used"
                }
            },
            "classification": classification,
            "recommended_action": action,
            "confidence": confidence,
            "user_explanation": f"Analysis of {ad['ad_name']}: ROAS {ad['roas']:.2f} vs avg {account_avg:.2f}.",
            "_parsing_note": "Fallback extraction used"
        }

    def _create_error_response(
        self,
        ad: Dict[str, Any],
        error_msg: str
    ) -> Dict[str, Any]:
        """Create an error response for graceful degradation."""
        return {
            "ad_name": ad.get("ad_name", "unknown"),
            "metrics": {
                "spend": ad.get("spend", 0),
                "roas": ad.get("roas", 0),
                "days_active": ad.get("days_active", 0),
                "account_avg_roas": 0,
            },
            "chain_of_thought": {
                "data_extracted": {},
                "comparison": {},
                "qualification": {},
                "classification_logic": {"result": "ERROR", "reason": error_msg},
                "confidence_rationale": {"level": "LOW", "reason": "Error occurred"}
            },
            "classification": "MANUAL_REVIEW",
            "recommended_action": "REVIEW",
            "confidence": "LOW",
            "user_explanation": f"Error during analysis: {error_msg}",
            "error": error_msg,
        }
