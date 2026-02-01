#!/usr/bin/env python3
"""
GATE 2 Test: Validate full Analyze → Recommend → Execute pipeline.

This test verifies:
1. Recommendations are grounded in analysis metrics
2. Recommendations include dollar impact calculations
3. Execute agent produces mock results

Run: python test_gate2.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.tools import get_fixture_with_expected
from models.analyze_agent import AnalyzeAgent
from models.recommend_agent import RecommendAgent
from models.execute_agent import ExecuteAgent


def print_recommendation(rec: dict):
    """Pretty print a recommendation."""
    action = rec.get("action", "?")
    ad_name = rec.get("ad_name", "?")
    current = rec.get("current_spend", 0)
    proposed = rec.get("proposed_new_spend", 0)
    change = rec.get("change_percentage", 0)
    impact = rec.get("expected_impact", {})

    print(f"\n  [{action}] {ad_name}")
    print(f"    Current: ${current:,.0f} → Proposed: ${proposed:,.0f} ({change:+.0f}%)")
    print(f"    Impact: {impact.get('calculation', 'N/A')}")
    print(f"    Rationale: {rec.get('rationale', 'N/A')[:80]}...")


def print_execution(result: dict):
    """Pretty print an execution result."""
    action = result.get("action_taken", "?")
    ad_name = result.get("ad_name", "?")
    status = result.get("status", "?")
    message = result.get("message", "")

    print(f"\n  [{status}] {action} - {ad_name}")
    print(f"    {message}")


async def run_gate2_test():
    """Run Gate 2 validation tests."""
    print("=" * 60)
    print("GATE 2: Full Pipeline Validation")
    print("=" * 60)

    # Load fixture data
    fixture_data = get_fixture_with_expected()
    account_avg = fixture_data["account_avg_roas"]

    print(f"\nAccount Average ROAS: {account_avg}")
    print(f"Total Ads: {len(fixture_data['ads'])}")

    # Prepare input data
    input_data = {
        "account_avg_roas": account_avg,
        "ads": [
            {
                "ad_name": ad["ad_name"],
                "ad_provider": ad["ad_provider"],
                "spend": ad["spend"],
                "roas": ad["roas"],
                "days_active": ad["days_active"],
            }
            for ad in fixture_data["ads"]
        ]
    }

    # Step 1: Analyze
    print("\n" + "-" * 60)
    print("STEP 1: Analyze Agent")
    print("-" * 60)

    analyze_agent = AnalyzeAgent()
    analysis_results = await analyze_agent.analyze(input_data)

    print(f"Analyzed {len(analysis_results)} ads")

    classifications = {}
    for result in analysis_results:
        cls = result.get("classification", "UNKNOWN")
        classifications[cls] = classifications.get(cls, 0) + 1

    print(f"Classifications: {json.dumps(classifications)}")

    # Step 2: Recommend
    print("\n" + "-" * 60)
    print("STEP 2: Recommend Agent")
    print("-" * 60)

    recommend_agent = RecommendAgent()
    recommendations = await recommend_agent.recommend(analysis_results)

    print(f"Generated {len(recommendations)} recommendations")

    # Validate recommendations
    valid_recs = 0
    for rec in recommendations:
        # Check required fields
        required = ["ad_name", "action", "current_spend", "proposed_new_spend",
                    "expected_impact", "rationale"]
        has_all = all(field in rec for field in required)

        # Check impact has calculation
        impact = rec.get("expected_impact", {})
        has_calc = "calculation" in impact and "estimated_revenue_change" in impact

        if has_all and has_calc:
            valid_recs += 1
            print_recommendation(rec)
        else:
            print(f"\n  [INVALID] {rec.get('ad_name', '?')} - missing fields")

    # Step 3: Execute (mock)
    print("\n" + "-" * 60)
    print("STEP 3: Execute Agent (Mock Mode)")
    print("-" * 60)

    execute_agent = ExecuteAgent(mock_mode=True)

    # Execute only actionable recommendations (SCALE, REDUCE, PAUSE)
    actionable = [r for r in recommendations if r.get("action") in ["SCALE", "REDUCE", "PAUSE"]]
    execution_result = await execute_agent.execute(actionable)

    print(f"\n{execution_result.get('summary', 'No summary')}")
    print(f"Timestamp: {execution_result.get('timestamp', 'N/A')}")

    for result in execution_result.get("executed", []):
        print_execution(result)

    # Summary
    print("\n" + "=" * 60)
    print("GATE 2 SUMMARY")
    print("=" * 60)

    total_recs = len(recommendations)
    print(f"Recommendations Generated: {total_recs}")
    print(f"Valid Recommendations: {valid_recs}/{total_recs}")
    print(f"Actionable (SCALE/REDUCE/PAUSE): {len(actionable)}")
    print(f"Executed: {len(execution_result.get('executed', []))}")

    # Gate pass criteria
    gate_passed = (
        valid_recs == total_recs and  # All recs are valid
        len(actionable) > 0 and       # At least one actionable
        len(execution_result.get("executed", [])) == len(actionable)  # All executed
    )

    if gate_passed:
        print("\n✓ GATE 2 PASSED")
    else:
        print("\n✗ GATE 2 FAILED")

    return gate_passed


if __name__ == "__main__":
    passed = asyncio.run(run_gate2_test())
    sys.exit(0 if passed else 1)
