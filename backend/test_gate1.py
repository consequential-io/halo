#!/usr/bin/env python3
"""
GATE 1 Test: Validate Analyze Agent output against fixtures.

This test verifies:
1. CoT chain is complete
2. Metrics are grounded (match source data)
3. Classifications are sensible

Run: python test_gate1.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from helpers.tools import get_fixture_with_expected
from helpers.validators import validate_analyze_output
from models.analyze_agent import AnalyzeAgent


def print_result(ad_name: str, expected: dict, actual: dict, valid: bool, violations: list):
    """Pretty print test results."""
    status = "✓" if valid else "✗"
    expected_class = expected.get("classification", "?")
    actual_class = actual.get("classification", "?")
    match = "✓" if expected_class == actual_class else "✗"

    print(f"\n{status} {ad_name}")
    print(f"  Expected: {expected_class} | Actual: {actual_class} {match}")
    print(f"  Confidence: {actual.get('confidence', '?')}")
    print(f"  Action: {actual.get('recommended_action', '?')}")

    if violations:
        print(f"  Violations: {', '.join(violations)}")

    if "user_explanation" in actual:
        print(f"  Explanation: {actual['user_explanation'][:100]}...")


async def run_gate1_test():
    """Run Gate 1 validation tests."""
    print("=" * 60)
    print("GATE 1: Analyze Agent Validation")
    print("=" * 60)

    # Load fixture data with expected classifications
    fixture_data = get_fixture_with_expected()
    account_avg = fixture_data["account_avg_roas"]

    print(f"\nAccount Average ROAS: {account_avg}")
    print(f"Total Ads to Test: {len(fixture_data['ads'])}")

    # Initialize agent
    agent = AnalyzeAgent()

    # Prepare input data (without _expected fields)
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

    # Run analysis
    print("\nRunning Analyze Agent...")
    results = await agent.analyze(input_data)

    # Validate results
    total = len(fixture_data["ads"])
    passed = 0
    classification_matches = 0

    for i, (ad, result) in enumerate(zip(fixture_data["ads"], results)):
        expected = ad.get("_expected", {})
        source_data = {
            "spend": ad["spend"],
            "roas": ad["roas"],
            "days_active": ad["days_active"],
        }

        # Validate structure and grounding
        is_valid, violations = validate_analyze_output(result, source_data, account_avg)

        if is_valid:
            passed += 1

        # Check classification match
        if result.get("classification") == expected.get("classification"):
            classification_matches += 1

        print_result(ad["ad_name"], expected, result, is_valid, violations)

    # Summary
    print("\n" + "=" * 60)
    print("GATE 1 SUMMARY")
    print("=" * 60)
    print(f"Validation Passed: {passed}/{total} ({passed/total*100:.0f}%)")
    print(f"Classification Match: {classification_matches}/{total} ({classification_matches/total*100:.0f}%)")

    # Gate pass criteria
    gate_passed = passed == total and classification_matches >= total * 0.8  # 80% classification match

    if gate_passed:
        print("\n✓ GATE 1 PASSED")
    else:
        print("\n✗ GATE 1 FAILED")
        if passed < total:
            print("  - Fix validation issues")
        if classification_matches < total * 0.8:
            print("  - Improve classification accuracy")

    return gate_passed


if __name__ == "__main__":
    passed = asyncio.run(run_gate1_test())
    sys.exit(0 if passed else 1)
