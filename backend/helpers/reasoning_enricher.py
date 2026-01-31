"""
LLM-based reasoning enrichment for recommendations.
Implements hallucination prevention and validation.
"""

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, Field, field_validator, ValidationError

from helpers.llm_client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models for Structured Output
# =============================================================================

class EnrichedReasoning(BaseModel):
    """Single enriched reasoning with validation."""
    ad_name: str
    reasoning: str = Field(max_length=500)

    @field_validator('reasoning')
    @classmethod
    def validate_no_invented_data(cls, v: str) -> str:
        """Reject reasoning that contains hallucination indicators."""
        invented_patterns = [
            "studies show",
            "research indicates",
            "typically",
            "on average",
            "usually",
            "according to",
            "industry benchmark",
            "best practice suggests",
            "experts recommend",
            "data suggests",
        ]
        v_lower = v.lower()
        for pattern in invented_patterns:
            if pattern in v_lower:
                raise ValueError(f"Reasoning contains potentially invented context: '{pattern}'")
        return v


class EnrichedReasoningBatch(BaseModel):
    """Batch of enriched reasonings from LLM."""
    reasonings: list[EnrichedReasoning]


# =============================================================================
# Hallucination Prevention
# =============================================================================

class HallucinationValidator:
    """
    Validates LLM output against grounding data.
    Prevents hallucinated facts from reaching users.
    """

    def __init__(self, grounding_data: dict[str, Any]):
        """
        Args:
            grounding_data: Original recommendation data (source of truth)
        """
        self.grounding = grounding_data
        self.allowed_numbers = self._extract_numbers(grounding_data)

    def _extract_numbers(self, data: Any) -> set[float]:
        """Extract all numeric values from grounding data."""
        numbers = set()

        def extract(obj):
            if isinstance(obj, (int, float)) and obj != 0:
                numbers.add(round(abs(obj), 2))
                # Also add common transformations
                if obj > 1:
                    numbers.add(round(obj, 0))  # Whole number version
            elif isinstance(obj, dict):
                for v in obj.values():
                    extract(v)
            elif isinstance(obj, list):
                for item in obj:
                    extract(item)

        extract(data)
        return numbers

    def validate(self, reasoning: str) -> tuple[bool, str | None]:
        """
        Validate reasoning text against grounding data.

        Returns:
            (is_valid, error_message)
        """
        # Extract numbers from reasoning (integers and decimals)
        number_pattern = r'\b\d+\.?\d*\b'
        found_numbers = re.findall(number_pattern, reasoning)

        for num_str in found_numbers:
            try:
                num = float(num_str)
                # Skip small numbers (likely not invented stats)
                if num <= 10:
                    continue
                # Skip percentages that are simple (25, 50, 75, 100)
                if num in [25, 50, 75, 100, 30, 70]:
                    continue
                # Check if number appears in grounding data
                if not self._number_in_grounding(num):
                    return False, f"Number {num} not found in grounding data"
            except ValueError:
                continue

        return True, None

    def _number_in_grounding(self, num: float, tolerance: float = 0.1) -> bool:
        """Check if number appears in grounding data within tolerance."""
        for allowed in self.allowed_numbers:
            if allowed == 0:
                continue
            # Check with relative tolerance
            if abs(num - allowed) <= abs(allowed * tolerance):
                return True
            # Also check if it's close to the whole number version
            if abs(num - round(allowed, 0)) <= 1:
                return True
        return False


# =============================================================================
# Prompt Template
# =============================================================================

REASONING_ENRICHMENT_PROMPT = """You are a digital advertising analyst. Your task is to write clear, actionable reasoning for ad budget recommendations.

## CRITICAL RULES - YOU MUST FOLLOW THESE:
1. You can ONLY reference data provided in the context below
2. You CANNOT invent statistics, benchmarks, or external data
3. You CANNOT use phrases like "studies show", "research indicates", "typically", "on average", "industry benchmark"
4. Every number you mention MUST come from the provided data
5. Keep reasoning concise (2-3 sentences max)
6. Focus on explaining WHY this specific action is recommended

## Context Data (ONLY use data from here):
{context_json}

## Task:
For each recommendation, write an enhanced reasoning that:
- Explains WHY this action is recommended based on the specific metrics
- References the actual numbers from the data
- Suggests what to investigate or do next

## Output Format:
Return a JSON object with this exact structure:
{{
  "reasonings": [
    {{"ad_name": "exact ad name from input", "reasoning": "your enhanced reasoning (2-3 sentences)"}},
    ...
  ]
}}

IMPORTANT: Return ONLY the JSON, no other text. The ad_name must match exactly."""


# =============================================================================
# Reasoning Enricher
# =============================================================================

class ReasoningEnricher:
    """
    Enhances recommendation reasoning using LLM while preventing hallucinations.
    """

    def __init__(self, enable_llm: bool = True):
        self.enable_llm = enable_llm
        self.client = LLMClient() if enable_llm else None

    async def enrich_batch(
        self,
        recommendations: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Enrich reasoning for a batch of recommendations.

        Args:
            recommendations: List of recommendation dicts with template reasoning

        Returns:
            Same recommendations with enriched reasoning (or original on failure)
        """
        if not self.enable_llm:
            logger.info("LLM reasoning disabled via settings. Using template reasoning.")
            return self._mark_as_template(recommendations)

        if not recommendations:
            return recommendations

        if self.client and not self.client.api_key:
            logger.info("LLM reasoning disabled: GEMINI_API_KEY not configured. Using template reasoning.")
            return self._mark_as_template(recommendations)

        # Prepare grounding context (only what LLM needs to see)
        context = self._prepare_context(recommendations)

        # Call LLM
        prompt = REASONING_ENRICHMENT_PROMPT.format(
            context_json=json.dumps(context, indent=2)
        )

        response = await self.client.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=2048,
        )

        if response.error:
            logger.warning(f"LLM enrichment failed for batch: {response.error}. Using template reasoning.")
            return self._mark_as_template(recommendations)

        # Parse and validate LLM output
        enriched = self._parse_and_validate(response.content, recommendations)

        return enriched

    def _prepare_context(self, recommendations: list[dict]) -> list[dict]:
        """Prepare minimal grounding context for LLM."""
        context = []
        for rec in recommendations:
            ctx = {
                "ad_name": rec.get("ad_name"),
                "action": rec.get("action"),
                "priority": rec.get("priority"),
                "recommended_change": rec.get("recommended_change"),
                "root_causes": rec.get("root_causes", []),
                "original_reasoning": rec.get("reasoning"),
            }
            # Add relevant metrics based on action
            if rec.get("current_spend"):
                ctx["current_spend"] = rec.get("current_spend")
            if rec.get("current_roas"):
                ctx["current_roas"] = rec.get("current_roas")
            if rec.get("current_cpa"):
                ctx["current_cpa"] = rec.get("current_cpa")
            if rec.get("z_score"):
                ctx["z_score"] = rec.get("z_score")
            if rec.get("estimated_impact"):
                ctx["estimated_impact"] = rec.get("estimated_impact")
            if rec.get("creative_variants"):
                ctx["creative_variants"] = rec.get("creative_variants")
            if rec.get("days_active"):
                ctx["days_active"] = rec.get("days_active")

            context.append(ctx)
        return context

    def _parse_and_validate(
        self,
        llm_output: str,
        original_recs: list[dict],
    ) -> list[dict]:
        """Parse LLM JSON output and validate against grounding data."""
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_str = llm_output.strip()
            if json_str.startswith("```"):
                # Remove markdown code block
                json_str = re.sub(r'^```(?:json)?\s*', '', json_str)
                json_str = re.sub(r'\s*```$', '', json_str)

            # Find JSON object
            json_match = re.search(r'\{[\s\S]*\}', json_str)
            if not json_match:
                logger.warning("Failed to parse LLM JSON response: No JSON object found. Using template reasoning.")
                return self._mark_as_template(original_recs)

            parsed = json.loads(json_match.group())

            # Validate with Pydantic
            try:
                batch = EnrichedReasoningBatch.model_validate(parsed)
            except ValidationError as e:
                logger.warning(f"LLM output validation failed: {e}. Using template reasoning.")
                return self._mark_as_template(original_recs)

            # Build lookup by ad_name
            enriched_map = {er.ad_name: er.reasoning for er in batch.reasonings}

            # Merge enriched reasoning into original recommendations
            result = []
            for rec in original_recs:
                ad_name = rec.get("ad_name")
                rec_copy = rec.copy()

                if ad_name in enriched_map:
                    enriched_reasoning = enriched_map[ad_name]

                    # Validate against grounding data (hallucination check)
                    validator = HallucinationValidator(rec)
                    is_valid, error = validator.validate(enriched_reasoning)

                    if is_valid:
                        rec_copy["reasoning"] = enriched_reasoning
                        rec_copy["reasoning_source"] = "llm_enriched"
                    else:
                        logger.warning(f"Hallucination detected for '{ad_name}': {error}. Falling back to template.")
                        rec_copy["reasoning_source"] = "template_fallback"
                else:
                    rec_copy["reasoning_source"] = "template_fallback"

                result.append(rec_copy)

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {e}. Using template reasoning.")
            return self._mark_as_template(original_recs)

    def _mark_as_template(self, recommendations: list[dict]) -> list[dict]:
        """Mark all recommendations as using template reasoning."""
        result = []
        for rec in recommendations:
            rec_copy = rec.copy()
            rec_copy["reasoning_source"] = "template_fallback"
            result.append(rec_copy)
        return result
