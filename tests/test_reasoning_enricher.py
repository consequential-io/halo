"""
Tests for LLM reasoning enrichment with hallucination prevention.

Run with: python3 -m pytest tests/test_reasoning_enricher.py -v
Or standalone: python3 tests/test_reasoning_enricher.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import json

from helpers.reasoning_enricher import (
    ReasoningEnricher,
    HallucinationValidator,
    EnrichedReasoning,
    EnrichedReasoningBatch,
)
from pydantic import ValidationError


# =============================================================================
# HallucinationValidator Tests
# =============================================================================

def test_validator_accepts_grounded_numbers():
    """Numbers from grounding data should pass validation."""
    print("\n=== Test: Validator accepts grounded numbers ===")

    grounding = {"current_spend": 1000.0, "current_roas": 0.3, "estimated_impact": 500.0}
    validator = HallucinationValidator(grounding)

    reasoning = "With spend of $1000 and ROAS of 0.3, pausing saves $500."
    is_valid, error = validator.validate(reasoning)

    assert is_valid is True, f"Expected valid, got error: {error}"
    assert error is None

    print("✓ Grounded numbers pass validation")
    return True


def test_validator_rejects_invented_numbers():
    """Numbers not in grounding data should fail validation."""
    print("\n=== Test: Validator rejects invented numbers ===")

    grounding = {"current_spend": 1000.0, "current_roas": 0.3}
    validator = HallucinationValidator(grounding)

    # 88% and 2.5 are invented
    reasoning = "Industry benchmark of 2.5 ROAS suggests this ad is 88% below average."
    is_valid, error = validator.validate(reasoning)

    assert is_valid is False, "Expected validation to fail for invented numbers"
    assert "not found in grounding" in error

    print(f"✓ Invented numbers rejected: {error}")
    return True


def test_validator_allows_small_numbers():
    """Small numbers (<= 10) should be allowed as they're unlikely to be invented stats."""
    print("\n=== Test: Validator allows small numbers ===")

    grounding = {"current_spend": 1000.0}
    validator = HallucinationValidator(grounding)

    reasoning = "Consider testing 2-3 creative variants over the next 7 days."
    is_valid, error = validator.validate(reasoning)

    assert is_valid is True, f"Small numbers should be allowed, got: {error}"

    print("✓ Small numbers allowed")
    return True


def test_validator_allows_common_percentages():
    """Common percentages (25, 50, 75, 100) should be allowed."""
    print("\n=== Test: Validator allows common percentages ===")

    grounding = {"current_spend": 1000.0}
    validator = HallucinationValidator(grounding)

    reasoning = "Reduce budget by 50% to prevent 100% of projected waste."
    is_valid, error = validator.validate(reasoning)

    assert is_valid is True, f"Common percentages should be allowed, got: {error}"

    print("✓ Common percentages allowed")
    return True


# =============================================================================
# EnrichedReasoning Pydantic Model Tests
# =============================================================================

def test_pydantic_rejects_studies_show():
    """Phrases like 'studies show' should be rejected."""
    print("\n=== Test: Pydantic rejects 'studies show' ===")

    try:
        EnrichedReasoning(
            ad_name="Test Ad",
            reasoning="Studies show that ads with low ROAS should be paused."
        )
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "invented context" in str(e).lower()
        print(f"✓ 'studies show' rejected")

    return True


def test_pydantic_rejects_typically():
    """Phrases like 'typically' should be rejected."""
    print("\n=== Test: Pydantic rejects 'typically' ===")

    try:
        EnrichedReasoning(
            ad_name="Test Ad",
            reasoning="Ads typically perform better with multiple creatives."
        )
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "invented context" in str(e).lower()
        print(f"✓ 'typically' rejected")

    return True


def test_pydantic_rejects_industry_benchmark():
    """Phrases like 'industry benchmark' should be rejected."""
    print("\n=== Test: Pydantic rejects 'industry benchmark' ===")

    try:
        EnrichedReasoning(
            ad_name="Test Ad",
            reasoning="The industry benchmark suggests a 3.0 ROAS is healthy."
        )
        assert False, "Should have raised ValidationError"
    except ValidationError as e:
        assert "invented context" in str(e).lower()
        print(f"✓ 'industry benchmark' rejected")

    return True


def test_pydantic_accepts_factual_reasoning():
    """Factual reasoning without invented context should pass."""
    print("\n=== Test: Pydantic accepts factual reasoning ===")

    enriched = EnrichedReasoning(
        ad_name="Test Ad",
        reasoning="ROAS of 0.30 means losing $0.70 per dollar spent. Pausing prevents further waste."
    )
    assert enriched.reasoning is not None
    assert enriched.ad_name == "Test Ad"

    print("✓ Factual reasoning accepted")
    return True


def test_pydantic_batch_validation():
    """Batch validation should work correctly."""
    print("\n=== Test: Pydantic batch validation ===")

    batch_data = {
        "reasonings": [
            {"ad_name": "Ad 1", "reasoning": "Low ROAS of 0.3 indicates waste."},
            {"ad_name": "Ad 2", "reasoning": "High ROAS of 5.0 suggests scaling potential."},
        ]
    }

    batch = EnrichedReasoningBatch.model_validate(batch_data)
    assert len(batch.reasonings) == 2

    print("✓ Batch validation works")
    return True


# =============================================================================
# ReasoningEnricher Tests
# =============================================================================

def test_enricher_disabled_returns_template():
    """When LLM is disabled, original reasoning should be returned with marker."""
    print("\n=== Test: Enricher disabled returns template ===")

    enricher = ReasoningEnricher(enable_llm=False)

    recs = [{"ad_name": "Test", "reasoning": "Original reasoning"}]
    result = asyncio.run(enricher.enrich_batch(recs))

    assert result[0]["reasoning"] == "Original reasoning"
    assert result[0]["reasoning_source"] == "template_fallback"

    print("✓ Disabled enricher returns template with marker")
    return True


def test_enricher_empty_batch():
    """Empty batch should return empty list."""
    print("\n=== Test: Enricher handles empty batch ===")

    enricher = ReasoningEnricher(enable_llm=True)
    result = asyncio.run(enricher.enrich_batch([]))

    assert result == []

    print("✓ Empty batch handled")
    return True


def test_enricher_marks_all_as_template_on_error():
    """On LLM error, all recommendations should be marked as template fallback."""
    print("\n=== Test: Enricher marks as template on error ===")

    recs = [
        {"ad_name": "Ad 1", "reasoning": "Template 1"},
        {"ad_name": "Ad 2", "reasoning": "Template 2"},
    ]

    result = ReasoningEnricher(enable_llm=False)._mark_as_template(recs)

    assert all(r["reasoning_source"] == "template_fallback" for r in result)

    print("✓ All marked as template on fallback")
    return True


def test_enricher_prepares_context_correctly():
    """Context preparation should include relevant fields."""
    print("\n=== Test: Enricher prepares context correctly ===")

    enricher = ReasoningEnricher(enable_llm=False)

    recs = [{
        "ad_name": "Test Ad",
        "action": "pause",
        "current_spend": 1000.0,
        "current_roas": 0.3,
        "reasoning": "Template",
        "extra_field": "should not appear",
    }]

    context = enricher._prepare_context(recs)

    assert len(context) == 1
    assert context[0]["ad_name"] == "Test Ad"
    assert context[0]["action"] == "pause"
    assert context[0]["current_spend"] == 1000.0
    assert "extra_field" not in context[0]

    print("✓ Context prepared correctly")
    return True


# =============================================================================
# Integration Tests with Mocked LLM
# =============================================================================

def test_enricher_with_mocked_llm_success():
    """Test successful LLM enrichment with mocked response."""
    print("\n=== Test: Enricher with mocked LLM success ===")

    async def run_test():
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "reasonings": [
                {
                    "ad_name": "Test Ad",
                    "reasoning": "With ROAS at 0.30, this ad loses $0.70 per dollar. Pausing saves $1000 daily."
                }
            ]
        })
        mock_response.error = None

        with patch('helpers.reasoning_enricher.LLMClient') as MockClient:
            mock_instance = MagicMock()
            mock_instance.api_key = "test-key"
            mock_instance.generate = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_instance

            enricher = ReasoningEnricher(enable_llm=True)
            enricher.client = mock_instance

            recs = [{
                "ad_name": "Test Ad",
                "action": "pause",
                "current_spend": 1000.0,
                "current_roas": 0.3,
                "reasoning": "Template reasoning",
            }]

            result = await enricher.enrich_batch(recs)

            assert result[0]["reasoning_source"] == "llm_enriched"
            assert "0.30" in result[0]["reasoning"] or "0.70" in result[0]["reasoning"]

    asyncio.run(run_test())
    print("✓ Mocked LLM enrichment works")
    return True


def test_enricher_fallback_on_llm_error():
    """Test fallback when LLM returns error."""
    print("\n=== Test: Enricher fallback on LLM error ===")

    async def run_test():
        mock_response = MagicMock()
        mock_response.content = ""
        mock_response.error = "Rate limit exceeded"

        with patch('helpers.reasoning_enricher.LLMClient') as MockClient:
            mock_instance = MagicMock()
            mock_instance.api_key = "test-key"
            mock_instance.generate = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_instance

            enricher = ReasoningEnricher(enable_llm=True)
            enricher.client = mock_instance

            recs = [{
                "ad_name": "Test Ad",
                "reasoning": "Original template",
            }]

            result = await enricher.enrich_batch(recs)

            assert result[0]["reasoning"] == "Original template"
            assert result[0]["reasoning_source"] == "template_fallback"

    asyncio.run(run_test())
    print("✓ Fallback on LLM error works")
    return True


def test_enricher_rejects_hallucinated_response():
    """Test that hallucinated LLM responses are rejected."""
    print("\n=== Test: Enricher rejects hallucinated response ===")

    async def run_test():
        # LLM returns invented statistics
        mock_response = MagicMock()
        mock_response.content = json.dumps({
            "reasonings": [
                {
                    "ad_name": "Test Ad",
                    "reasoning": "With 88% below the industry average of 2.5 ROAS, this needs attention."
                }
            ]
        })
        mock_response.error = None

        with patch('helpers.reasoning_enricher.LLMClient') as MockClient:
            mock_instance = MagicMock()
            mock_instance.api_key = "test-key"
            mock_instance.generate = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_instance

            enricher = ReasoningEnricher(enable_llm=True)
            enricher.client = mock_instance

            recs = [{
                "ad_name": "Test Ad",
                "current_spend": 1000.0,
                "current_roas": 0.3,
                "reasoning": "Template reasoning",
            }]

            result = await enricher.enrich_batch(recs)

            # Should fallback due to invented numbers (88, 2.5)
            assert result[0]["reasoning_source"] == "template_fallback"
            assert result[0]["reasoning"] == "Template reasoning"

    asyncio.run(run_test())
    print("✓ Hallucinated response rejected")
    return True


# =============================================================================
# Test Runner
# =============================================================================

def run_enricher_tests():
    """Run all reasoning enricher tests."""
    print("=" * 60)
    print("REASONING ENRICHER UNIT TESTS")
    print("=" * 60)

    tests = [
        ("Validator accepts grounded numbers", test_validator_accepts_grounded_numbers),
        ("Validator rejects invented numbers", test_validator_rejects_invented_numbers),
        ("Validator allows small numbers", test_validator_allows_small_numbers),
        ("Validator allows common percentages", test_validator_allows_common_percentages),
        ("Pydantic rejects 'studies show'", test_pydantic_rejects_studies_show),
        ("Pydantic rejects 'typically'", test_pydantic_rejects_typically),
        ("Pydantic rejects 'industry benchmark'", test_pydantic_rejects_industry_benchmark),
        ("Pydantic accepts factual reasoning", test_pydantic_accepts_factual_reasoning),
        ("Pydantic batch validation", test_pydantic_batch_validation),
        ("Enricher disabled returns template", test_enricher_disabled_returns_template),
        ("Enricher handles empty batch", test_enricher_empty_batch),
        ("Enricher marks as template on error", test_enricher_marks_all_as_template_on_error),
        ("Enricher prepares context correctly", test_enricher_prepares_context_correctly),
        ("Enricher with mocked LLM success", test_enricher_with_mocked_llm_success),
        ("Enricher fallback on LLM error", test_enricher_fallback_on_llm_error),
        ("Enricher rejects hallucinated response", test_enricher_rejects_hallucinated_response),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"\n✗ FAILED: {name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗ ERROR: {name}")
            print(f"  Exception: {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"REASONING ENRICHER RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ ALL REASONING ENRICHER TESTS PASSED")
        return True
    else:
        print(f"\n❌ {failed} REASONING ENRICHER TESTS FAILED")
        return False


if __name__ == "__main__":
    success = run_enricher_tests()
    sys.exit(0 if success else 1)
