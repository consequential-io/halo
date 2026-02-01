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


def print_timeline(timeline_data: dict):
    """Print account-wide metric timeline with ASCII chart."""
    timeline = timeline_data.get("timeline", [])
    summary = timeline_data.get("summary", {})

    if not timeline:
        print("No timeline data available")
        return

    print("\n" + "=" * 70)
    print("📈 ACCOUNT METRICS TIMELINE (Last 30 Days)")
    print("=" * 70)

    # Week-over-week summary
    cpm_change = summary.get("cpm_wow_change", 0)
    roas_change = summary.get("roas_wow_change", 0)

    cpm_icon = "🔴" if cpm_change > 20 else "🟡" if cpm_change > 10 else "🟢"
    roas_icon = "🔴" if roas_change < -20 else "🟡" if roas_change < -10 else "🟢"

    print(f"\n{cpm_icon} CPM: ${summary.get('avg_cpm_prev_week', 0):.0f} → ${summary.get('avg_cpm_last_week', 0):.0f} ({cpm_change:+.0f}% WoW)")
    print(f"{roas_icon} ROAS: {summary.get('avg_roas_prev_week', 0):.2f} → {summary.get('avg_roas_last_week', 0):.2f} ({roas_change:+.0f}% WoW)")

    # ASCII CPM chart - show last 21 days for readability
    recent = timeline[-21:] if len(timeline) >= 21 else timeline

    if not recent:
        return

    # Get CPM values for chart
    cpms = [d["cpm"] for d in recent]
    max_cpm = max(cpms) if cpms else 1
    min_cpm = min(cpms) if cpms else 0
    range_cpm = max_cpm - min_cpm if max_cpm > min_cpm else 1

    print("\n" + "-" * 70)
    print("CPM Trend (last 21 days):")
    print("-" * 70)

    # Simple ASCII chart - 5 rows
    chart_height = 5
    for row in range(chart_height, 0, -1):
        threshold = min_cpm + (range_cpm * row / chart_height)
        line = f"${threshold:5.0f} |"
        for cpm in cpms:
            if cpm >= threshold:
                line += "█"
            elif cpm >= threshold - (range_cpm / chart_height / 2):
                line += "▄"
            else:
                line += " "
        print(line)

    # X-axis with dates
    print("       +" + "-" * len(cpms))
    dates = [d["date"][-5:] for d in recent]  # MM-DD format
    print(f"        {dates[0]}{'':>{len(cpms)-10}}{dates[-1]}")

    # Identify when the spike started
    if len(cpms) >= 7:
        baseline_avg = sum(cpms[:7]) / 7
        for i, cpm in enumerate(cpms):
            if cpm > baseline_avg * 1.3:  # 30% above baseline
                spike_date = recent[i]["date"]
                print(f"\n⚠️  CPM spike detected starting ~{spike_date}")
                break

    print("")


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


def normalize_root_cause(cause: str, anomaly: dict = None) -> str:
    """Normalize root cause to a standard category."""
    cause_lower = cause.lower()

    # CPM/Auction competition patterns
    if any(term in cause_lower for term in ["cpm", "auction", "competition", "bidding", "bid"]):
        return "CPM_SPIKE"
    # Also check if it's a CPM anomaly and mentions cost/increase
    if anomaly and anomaly.get("metric") == "cpm" and any(term in cause_lower for term in ["increase", "spike", "high", "cost"]):
        return "CPM_SPIKE"
    # CPA issues often caused by CPM
    if anomaly and anomaly.get("metric") == "cpa" and any(term in cause_lower for term in ["cost", "increase", "spike", "competition"]):
        return "CPM_SPIKE"

    if "creative" in cause_lower and "fatigue" in cause_lower:
        return "CREATIVE_FATIGUE"
    if any(term in cause_lower for term in ["ctr", "engagement"]) and any(term in cause_lower for term in ["drop", "declin", "fatigue"]):
        return "CREATIVE_FATIGUE"

    if "budget" in cause_lower and any(term in cause_lower for term in ["exhaust", "cap", "limit", "spent"]):
        return "BUDGET_EXHAUSTION"

    if any(term in cause_lower for term in ["landing", "funnel", "conversion", "checkout", "cart"]):
        return "LANDING_PAGE_ISSUE"

    if any(term in cause_lower for term in ["tracking", "pixel", "attribution"]):
        return "TRACKING_ISSUE"

    if "season" in cause_lower:
        return "SEASONALITY"

    if "audience" in cause_lower and any(term in cause_lower for term in ["exhaust", "saturat", "frequen"]):
        return "AUDIENCE_EXHAUSTION"

    if "unknown" in cause_lower or cause == "UNKNOWN":
        return "UNKNOWN"

    return "OTHER"


def get_cause_display(cause_key: str) -> tuple:
    """Get display name and icon for a root cause category."""
    cause_info = {
        "CPM_SPIKE": ("💰 CPM Spike (Increased Auction Competition)", "Adjust bids or targeting to reduce costs"),
        "CREATIVE_FATIGUE": ("🎨 Creative Fatigue", "Refresh creatives with new variants"),
        "BUDGET_EXHAUSTION": ("💸 Budget Exhaustion", "Review and increase budget caps"),
        "LANDING_PAGE_ISSUE": ("🌐 Landing Page Issue", "Check landing page load time and UX"),
        "TRACKING_ISSUE": ("🔧 Tracking Issue", "Verify pixel/conversion tracking setup"),
        "SEASONALITY": ("📅 Seasonality", "Expected fluctuation - monitor trends"),
        "AUDIENCE_EXHAUSTION": ("👥 Audience Exhaustion", "Expand targeting or find new audiences"),
        "UNKNOWN": ("❓ Unknown", "Manual investigation required"),
        "OTHER": ("📋 Other", "Review individual cases"),
    }
    return cause_info.get(cause_key, ("📋 " + cause_key, "Review details"))


def print_full_rca(rca_result: dict):
    """Pretty print full RCA pipeline results - grouped by root cause."""
    summary = rca_result.get("detection_summary", {})

    print("\n" + "=" * 70)
    print("🔬 RCA PIPELINE RESULTS")
    print("=" * 70)
    print(f"Total Bad Anomalies Detected: {summary.get('total_anomalies', 0)}")
    print(f"Anomalies Investigated: {summary.get('investigated', 0)}")
    print(f"Baseline: {summary.get('baseline_period', 'N/A')}")
    print(f"Current: {summary.get('current_period', 'N/A')}")

    results = rca_result.get("results", [])

    # Group by normalized root cause
    grouped = {}
    for result in results:
        raw_cause = result.get("investigation", {}).get("root_cause", "UNKNOWN")
        anomaly = result.get("anomaly", {})
        cause_key = normalize_root_cause(raw_cause, anomaly)
        if cause_key not in grouped:
            grouped[cause_key] = []
        grouped[cause_key].append(result)

    # Print grouped results
    print("\n" + "=" * 70)
    print("📊 ROOT CAUSES (Grouped)")
    print("=" * 70)

    for cause_key, items in sorted(grouped.items(), key=lambda x: -len(x[1])):
        display_name, recommendation = get_cause_display(cause_key)

        print(f"\n{display_name}")
        print(f"   Affected Ads: {len(items)}")
        print(f"   💡 Action: {recommendation}")
        print("   " + "-" * 50)

        for item in items:
            anomaly = item.get("anomaly", {})
            investigation = item.get("investigation", {})
            ad_name = anomaly.get("ad_name", "Unknown")[:40]
            metric = anomaly.get("metric", "N/A").upper()
            direction = anomaly.get("direction", "")
            pct = abs(anomaly.get("pct_change", 0))
            confidence = investigation.get("confidence", "LOW")
            conf_icon = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "❓"}.get(confidence, "❓")

            print(f"   • {ad_name}")
            print(f"     {metric} {direction} {pct:.0f}% | Confidence: {conf_icon} {confidence}")

    # Quick summary
    print("\n" + "=" * 70)
    print("📈 QUICK SUMMARY")
    print("=" * 70)
    for cause_key, items in sorted(grouped.items(), key=lambda x: -len(x[1])):
        display_name, _ = get_cause_display(cause_key)
        print(f"   {len(items)} anomal{'y' if len(items) == 1 else 'ies'} → {display_name.split(' ', 1)[1] if ' ' in display_name else display_name}")


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
    from helpers.rca_checks import get_metric_timeline

    print(f"Running full RCA pipeline for tenant '{args.tenant}'...")
    print(f"Baseline: {args.baseline_days} days, Current: {args.current_days} days")

    # First, show the timeline to give context
    print("\nFetching account metrics timeline...")
    timeline_data = await get_metric_timeline(days=args.baseline_days, tenant=args.tenant)
    print_timeline(timeline_data)

    print(f"\nInvestigating up to {args.max_anomalies} anomalies...")

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
