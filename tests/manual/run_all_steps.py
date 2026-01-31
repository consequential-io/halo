#!/usr/bin/env python3
"""
Gate 1 Manual Validation - Run All Steps

Run: python3 tests/manual/run_all_steps.py

Configure data source via environment:
  DATA_SOURCE=fixture python3 tests/manual/run_all_steps.py  (default)
  DATA_SOURCE=bq python3 tests/manual/run_all_steps.py
  DATA_SOURCE=bq DATA_LOOKBACK_DAYS=45 python3 tests/manual/run_all_steps.py
"""

import os
import subprocess
import sys
from pathlib import Path


def run_step(step_num: int, script_name: str) -> bool:
    """Run a single validation step."""
    script_path = Path(__file__).parent / script_name

    print(f"\n{'#' * 70}")
    print(f"# RUNNING STEP {step_num}")
    print(f"{'#' * 70}")

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=Path(__file__).parent.parent.parent
    )

    return result.returncode == 0


def main():
    print("=" * 70)
    print("GATE 1 MANUAL VALIDATION - ALL STEPS")
    print("=" * 70)

    # Show configuration
    data_source = os.getenv("DATA_SOURCE", "fixture")
    lookback_days = os.getenv("DATA_LOOKBACK_DAYS", "30")
    print(f"\n[Config] DATA_SOURCE={data_source}, DATA_LOOKBACK_DAYS={lookback_days}")
    print(f"         To change: DATA_SOURCE=bq DATA_LOOKBACK_DAYS=45 python3 tests/manual/run_all_steps.py")

    steps = [
        (1, "step1_verify_fixtures.py", "Verify Fixtures Loaded"),
        (2, "step2_detect_anomalies_cpa.py", "Detect High CPA Anomalies"),
        (3, "step3_detect_anomalies_roas.py", "Detect Low ROAS Anomalies"),
        (4, "step4_verify_ontology.py", "Verify Ontology Breakdown"),
        (5, "step5_verify_rca.py", "Verify RCA Analysis"),
    ]

    results = []

    for step_num, script, description in steps:
        success = run_step(step_num, script)
        results.append((step_num, description, success))

    # Summary
    print("\n")
    print("=" * 70)
    print("GATE 1 VALIDATION SUMMARY")
    print("=" * 70)
    print(f"\n{'Step':<6} {'Description':<40} {'Result':<10}")
    print("-" * 70)

    passed = 0
    failed = 0

    for step_num, description, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{step_num:<6} {description:<40} {status:<10}")
        if success:
            passed += 1
        else:
            failed += 1

    print("-" * 70)
    print(f"\nTotal: {passed}/{len(steps)} steps passed")

    if failed == 0:
        print("\n" + "🎉" * 20)
        print("GATE 1 VALIDATION COMPLETE - ALL STEPS PASSED")
        print("🎉" * 20)
        return True
    else:
        print(f"\n❌ {failed} step(s) failed - review output above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
