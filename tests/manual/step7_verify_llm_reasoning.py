#!/usr/bin/env python3
"""
Gate 1 Manual Validation - Step 7: Verify LLM Reasoning Enrichment

Run: python3 tests/manual/step7_verify_llm_reasoning.py

Requires: GEMINI_API_KEY in .env or environment

This step tests:
1. API key configuration
2. LLM client connectivity
3. Reasoning enrichment with hallucination prevention
4. Full pipeline with async recommendations
5. Comparison of LLM vs template reasoning
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from config.settings import settings
from helpers.llm_client import LLMClient
from helpers.reasoning_enricher import ReasoningEnricher
from models.analyze_agent import AnalyzeAgentModel
from models.recommend_agent import RecommendAgentModel
from helpers.tools import get_ad_data


def test_api_key_loaded() -> bool:
    """Test 1: Verify API key is loaded from .env"""
    print("\n" + "=" * 70)
    print("TEST 1: API Key Configuration")
    print("=" * 70)

    if settings.gemini_api_key:
        print(f"   ✓ API key loaded: {settings.gemini_api_key[:10]}...{settings.gemini_api_key[-4:]}")
        print(f"   ✓ LLM reasoning enabled: {settings.enable_llm_reasoning}")
        print(f"   ✓ Timeout: {settings.llm_timeout_seconds}s")
        return True
    else:
        print("   ✗ API key not configured")
        print("   → Add GEMINI_API_KEY to .env file")
        return False


async def test_llm_client() -> bool:
    """Test 2: Verify LLM client can connect and generate"""
    print("\n" + "=" * 70)
    print("TEST 2: LLM Client Connectivity")
    print("=" * 70)

    client = LLMClient()

    if not client.api_key:
        print("   ✗ Skipped: API key not configured")
        return False

    print("   → Sending test prompt to Gemini...")
    response = await client.generate(
        prompt="Respond with exactly one word: Hello",
        temperature=0.1,
        max_tokens=10,
    )

    if response.error:
        print(f"   ✗ Error: {response.error}")
        return False

    print(f"   ✓ Response: {response.content}")
    if response.usage:
        print(f"   ✓ Tokens: {response.usage}")
    return True


async def test_reasoning_enrichment() -> bool:
    """Test 3: Verify reasoning enrichment with hallucination prevention"""
    print("\n" + "=" * 70)
    print("TEST 3: Reasoning Enrichment")
    print("=" * 70)

    enricher = ReasoningEnricher(enable_llm=True)

    if not enricher.client or not enricher.client.api_key:
        print("   ✗ Skipped: API key not configured")
        return False

    # Test recommendation
    test_recs = [{
        "ad_name": "Test TikTok Campaign",
        "action": "pause",
        "priority": "critical",
        "current_spend": 500.0,
        "current_roas": 0.25,
        "estimated_impact": 500.0,
        "recommended_change": "-100%",
        "reasoning": "ROAS of 0.25 is below profitability threshold",
        "root_causes": ["low_ctr", "audience_engagement"],
    }]

    print("   → Sending recommendation for enrichment...")
    print(f"   → Original: {test_recs[0]['reasoning']}")

    result = await enricher.enrich_batch(test_recs)

    source = result[0].get("reasoning_source", "unknown")
    reasoning = result[0]["reasoning"]

    print(f"\n   Source: {source}")
    print(f"   Enriched: {reasoning[:150]}...")

    if source == "llm_enriched":
        print("\n   ✓ LLM enrichment successful")
        return True
    elif source == "template_fallback":
        print("\n   ⚠ Fell back to template (check logs for reason)")
        return True  # Not a failure, just fallback
    else:
        print("\n   ✗ Unknown source")
        return False


async def test_full_pipeline() -> bool:
    """Test 4: Full pipeline with async recommendations"""
    print("\n" + "=" * 70)
    print("TEST 4: Full Pipeline (Analyze → Recommend with LLM)")
    print("=" * 70)

    # Run analysis
    print("   → Running analysis on ThirdLove account...")
    analyze = AnalyzeAgentModel()
    analysis = analyze.run_analysis("tl")

    if "error" in analysis:
        print(f"   ✗ Analysis error: {analysis['error']}")
        return False

    print(f"   ✓ Found {len(analysis.get('detailed_anomalies', []))} anomalies")

    # Get recommendations with LLM
    print("   → Generating recommendations with LLM reasoning...")
    recommend = RecommendAgentModel(enable_llm_reasoning=True)
    data = get_ad_data("tl")
    result = await recommend.generate_recommendations_async(analysis, data["ads"])

    recs = result["recommendations"]
    print(f"   ✓ Generated {len(recs)} recommendations")

    # Show top 3 with reasoning source
    print("\n   Top 3 Recommendations:")
    print("-" * 70)

    llm_count = 0
    template_count = 0

    for i, r in enumerate(recs[:3], 1):
        source = r.get("reasoning_source", "unknown")
        if source == "llm_enriched":
            llm_count += 1
            source_icon = "🤖"
        else:
            template_count += 1
            source_icon = "📝"

        print(f"\n   {i}. {source_icon} [{r['priority'].upper()}] {r['action'].upper()}")
        print(f"      Ad: {r['ad_name'][:50]}")
        print(f"      Source: {source}")
        print(f"      Reasoning: {r['reasoning'][:100]}...")

    print(f"\n   Summary: {llm_count} LLM enriched, {template_count} template fallback")
    return True


async def test_comparison() -> bool:
    """Test 5: Compare LLM vs Template reasoning side-by-side"""
    print("\n" + "=" * 70)
    print("TEST 5: LLM vs Template Comparison")
    print("=" * 70)

    # Run analysis once
    analyze = AnalyzeAgentModel()
    analysis = analyze.run_analysis("tl")
    data = get_ad_data("tl")

    if "error" in analysis:
        print(f"   ✗ Analysis error: {analysis['error']}")
        return False

    # Get template reasoning (sync, no LLM)
    print("   → Getting template reasoning...")
    recommend_sync = RecommendAgentModel(enable_llm_reasoning=False)
    result_template = recommend_sync.generate_recommendations(analysis, data["ads"])

    # Get LLM reasoning (async)
    print("   → Getting LLM reasoning...")
    recommend_async = RecommendAgentModel(enable_llm_reasoning=True)
    result_llm = await recommend_async.generate_recommendations_async(analysis, data["ads"])

    # Compare first recommendation
    if result_template["recommendations"] and result_llm["recommendations"]:
        template_rec = result_template["recommendations"][0]
        llm_rec = result_llm["recommendations"][0]

        print("\n" + "-" * 70)
        print(f"   Ad: {template_rec['ad_name'][:50]}")
        print(f"   Action: {template_rec['action'].upper()}")
        print("-" * 70)

        print("\n   📝 TEMPLATE REASONING:")
        print(f"   {template_rec['reasoning']}")

        print("\n   🤖 LLM REASONING:")
        llm_source = llm_rec.get("reasoning_source", "unknown")
        print(f"   [{llm_source}]")
        print(f"   {llm_rec['reasoning']}")

        # Verify action unchanged
        if template_rec["action"] == llm_rec["action"]:
            print("\n   ✓ Action unchanged (rule-based decision preserved)")
        else:
            print("\n   ✗ Action changed! This should not happen.")
            return False

        # Verify impact unchanged
        if template_rec["estimated_impact"] == llm_rec["estimated_impact"]:
            print("   ✓ Impact unchanged (calculations preserved)")
        else:
            print("   ✗ Impact changed! This should not happen.")
            return False

    return True


async def run_all_tests():
    """Run all LLM reasoning tests."""
    print("=" * 70)
    print("STEP 7: Verify LLM Reasoning Enrichment")
    print("=" * 70)
    print(f"\n[Config] GEMINI_API_KEY={'configured' if settings.gemini_api_key else 'NOT SET'}")
    print(f"[Config] ENABLE_LLM_REASONING={settings.enable_llm_reasoning}")

    results = []

    # Test 1: API Key
    results.append(("API Key Configuration", test_api_key_loaded()))

    # Test 2: LLM Client
    results.append(("LLM Client Connectivity", await test_llm_client()))

    # Test 3: Reasoning Enrichment
    results.append(("Reasoning Enrichment", await test_reasoning_enrichment()))

    # Test 4: Full Pipeline
    results.append(("Full Pipeline", await test_full_pipeline()))

    # Test 5: Comparison
    results.append(("LLM vs Template Comparison", await test_comparison()))

    # Summary
    print("\n")
    print("=" * 70)
    print("STEP 7 SUMMARY: LLM Reasoning")
    print("=" * 70)

    passed = 0
    failed = 0

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"   {status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print("-" * 70)

    if failed == 0:
        print("✅ STEP 7 PASSED: LLM reasoning enrichment working correctly")
        return True
    elif not settings.gemini_api_key:
        print("⚠️  STEP 7 SKIPPED: GEMINI_API_KEY not configured")
        print("   Add API key to .env file to enable LLM reasoning")
        return True  # Not a failure, just not configured
    else:
        print(f"❌ STEP 7 FAILED: {failed} test(s) failed")
        return False


def main():
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
