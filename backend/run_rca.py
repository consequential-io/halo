#!/usr/bin/env python3
"""
Run the Agatha RCA (Root Cause Analysis) pipeline.

Usage:
    # Detect anomalies only:
    python run_rca.py --detect-only

    # Full RCA (detect + investigate):
    python run_rca.py

    # With custom parameters:
    python run_rca.py --tenant wh --baseline-days 30 --threshold 2.5

    # Investigate a specific ad:
    python run_rca.py --ad "Summer Sale Video" --metric roas
"""

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*MCP requires.*")

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def print_anomalies(detection_result: dict):
    """Pretty print detected anomalies."""
    print("\n" + "=" * 70)
    print("🔍 ANOMALY DETECTION RESULTS")
    print("=" * 70)
    print(f"Baseline Period: {detection_result.get('baseline_period', 'N/A')}")
    print(f"Current Period: {detection_result.get('current_period', 'N/A')}")
    print(f"Z-Score Threshold: {detection_result.get('z_threshold', 2.0)}")
    print(f"Anomalies Detected: {detection_result.get('anomalies_detected', 0)}")
    print("-" * 70)

    anomalies = detection_result.get("anomalies", [])
    if not anomalies:
        print("\n✅ No anomalies detected! All metrics within normal range.")
        return

    for i, anomaly in enumerate(anomalies, 1):
        severity = anomaly.get("severity", "UNKNOWN")
        severity_icon = {
            "CRITICAL": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢"
        }.get(severity, "⚪")

        direction = anomaly.get("direction", "CHANGED")
        direction_icon = "📉" if direction == "DROP" else "📈"

        print(f"\n{severity_icon} [{severity}] {anomaly.get('ad_name', 'Unknown')[:50]}")
        print(f"   {direction_icon} {anomaly.get('metric', 'N/A').upper()} {direction} {abs(anomaly.get('pct_change', 0)):.1f}%")
        print(f"   Value: {anomaly.get('baseline_mean', 0):.2f} → {anomaly.get('current_value', 0):.2f}")
        print(f"   Z-Score: {anomaly.get('z_score', 0):.2f}")
        print(f"   Provider: {anomaly.get('ad_provider', 'N/A')}")


def print_rca_result(result: dict):
    """Pretty print RCA investigation result."""
    anomaly = result.get("anomaly", {})
    investigation = result.get("investigation", {})

    print("\n" + "-" * 70)
    print(f"📋 RCA: {anomaly.get('ad_name', 'Unknown')[:50]}")
    print("-" * 70)

    # Anomaly summary
    print(f"Anomaly: {anomaly.get('metric', 'N/A').upper()} {anomaly.get('direction', '')} {abs(anomaly.get('pct_change', 0)):.1f}%")

    # Tools called
    tools = investigation.get("tools_called", investigation.get("checks_performed", []))
    if tools:
        print(f"Tools Used: {', '.join(tools) if isinstance(tools[0], str) else ', '.join([t.get('tool', '') for t in tools])}")

    # Root cause
    root_cause = investigation.get("root_cause", "UNKNOWN")
    confidence = investigation.get("confidence", "LOW")
    confidence_icon = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "❓"}.get(confidence, "❓")

    print(f"\n🎯 ROOT CAUSE: {root_cause}")
    print(f"   Confidence: {confidence_icon} {confidence}")

    # Evidence
    evidence = investigation.get("evidence", "")
    if evidence:
        print(f"   Evidence: {evidence[:100]}...")

    # Recommendation
    action = investigation.get("recommended_action", "")
    if action:
        print(f"\n💡 RECOMMENDED ACTION:")
        print(f"   {action}")


def print_full_rca(rca_result: dict):
    """Pretty print full RCA pipeline results."""
    summary = rca_result.get("detection_summary", {})

    print("\n" + "=" * 70)
    print("🔬 RCA PIPELINE RESULTS")
    print("=" * 70)
    print(f"Total Anomalies Detected: {summary.get('total_anomalies', 0)}")
    print(f"Anomalies Investigated: {summary.get('investigated', 0)}")
    print(f"Baseline: {summary.get('baseline_period', 'N/A')}")
    print(f"Current: {summary.get('current_period', 'N/A')}")

    results = rca_result.get("results", [])
    for result in results:
        print_rca_result(result)

    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)

    causes = {}
    for result in results:
        cause = result.get("investigation", {}).get("root_cause", "UNKNOWN")
        causes[cause] = causes.get(cause, 0) + 1

    for cause, count in sorted(causes.items(), key=lambda x: -x[1]):
        print(f"   {cause}: {count} anomal{'y' if count == 1 else 'ies'}")


async def run_detection_only(args):
    """Run anomaly detection only."""
    from models.anomaly_agent import detect_anomalies

    print(f"Detecting anomalies for tenant '{args.tenant}'...")
    print(f"Baseline: {args.baseline_days} days, Current: {args.current_days} days")

    result = await detect_anomalies(
        tenant=args.tenant,
        baseline_days=args.baseline_days,
        current_days=args.current_days,
        min_spend=args.min_spend,
        z_threshold=args.threshold
    )

    print_anomalies(result)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Results saved to {args.output}")

    return result


async def run_full_rca_pipeline(args):
    """Run full RCA pipeline (detect + investigate)."""
    from models.rca_agent import run_full_rca

    print(f"Running full RCA pipeline for tenant '{args.tenant}'...")
    print(f"Baseline: {args.baseline_days} days, Current: {args.current_days} days")
    print(f"Will investigate up to {args.max_anomalies} anomalies")

    result = await run_full_rca(
        tenant=args.tenant,
        baseline_days=args.baseline_days,
        current_days=args.current_days,
        min_spend=args.min_spend,
        z_threshold=args.threshold,
        max_anomalies=args.max_anomalies
    )

    print_full_rca(result)

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n✓ Results saved to {args.output}")

    return result


async def run_single_ad_rca(args):
    """Run RCA on a specific ad."""
    from models.rca_agent import investigate_anomaly

    print(f"Investigating {args.ad} ({args.metric})...")

    # Create mock anomaly for investigation
    anomaly = {
        "ad_name": args.ad,
        "ad_provider": "Unknown",
        "metric": args.metric,
        "direction": "DROP",
        "pct_change": -30,  # Assumed
        "current_value": 0,
        "baseline_mean": 0,
        "z_score": -2.5,
        "severity": "HIGH"
    }

    result = await investigate_anomaly(anomaly, tenant=args.tenant)

    print("\n" + "=" * 70)
    print(f"🔬 RCA RESULT: {args.ad}")
    print("=" * 70)
    print(json.dumps(result, indent=2, default=str))

    return result


def main():
    parser = argparse.ArgumentParser(description='Run the Agatha RCA pipeline')

    # Mode selection
    parser.add_argument('--detect-only', action='store_true',
                        help='Only detect anomalies, do not investigate')
    parser.add_argument('--ad', type=str,
                        help='Investigate a specific ad by name')
    parser.add_argument('--metric', type=str, default='roas',
                        choices=['roas', 'spend', 'ctr', 'cpm', 'cpa'],
                        help='Metric to investigate (used with --ad)')

    # Parameters
    parser.add_argument('--tenant', default='wh', choices=['tl', 'wh'],
                        help='Tenant: tl=ThirdLove, wh=WhisperingHomes (default: wh)')
    parser.add_argument('--baseline-days', type=int, default=30,
                        help='Days for baseline calculation (default: 30)')
    parser.add_argument('--current-days', type=int, default=3,
                        help='Recent days to analyze (default: 3)')
    parser.add_argument('--threshold', type=float, default=2.0,
                        help='Z-score threshold for anomaly detection (default: 2.0)')
    parser.add_argument('--min-spend', type=float, default=1000,
                        help='Minimum spend to consider an ad (default: 1000)')
    parser.add_argument('--max-anomalies', type=int, default=5,
                        help='Maximum anomalies to investigate (default: 5)')

    # Output
    parser.add_argument('--output', '-o', help='Output JSON file for results')

    args = parser.parse_args()

    # Run appropriate mode
    if args.ad:
        asyncio.run(run_single_ad_rca(args))
    elif args.detect_only:
        asyncio.run(run_detection_only(args))
    else:
        asyncio.run(run_full_rca_pipeline(args))


if __name__ == "__main__":
    main()
