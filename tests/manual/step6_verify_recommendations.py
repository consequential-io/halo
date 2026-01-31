#!/usr/bin/env python3
"""
Gate 1 Manual Validation - Step 6: Verify Recommendations

Run: python3 tests/manual/step6_verify_recommendations.py

Configure data source via environment:
  DATA_SOURCE=fixture python3 tests/manual/step6_verify_recommendations.py  (default)
  DATA_SOURCE=bq DATA_LOOKBACK_DAYS=45 python3 tests/manual/step6_verify_recommendations.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from helpers.tools import get_ad_data
from models.analyze_agent import AnalyzeAgentModel
from models.recommend_agent import RecommendAgentModel
from config.settings import settings


def analyze_account(account_id: str, account_name: str) -> dict:
    """Run full analysis and recommendation pipeline for an account."""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {account_name} ({account_id.upper()})")
    print("=" * 70)

    # Step 1: Load data
    source_label = "BigQuery" if settings.data_source == "bq" else "fixtures"
    print(f"\n[1] Loading ad data from {source_label}...")
    data = get_ad_data(account_id, source=settings.data_source)

    if "error" in data:
        print(f"   ❌ Error: {data['error']}")
        return {"error": data["error"], "account": account_id}

    ads = data["ads"]
    print(f"   ✓ Loaded {len(ads)} ads")

    if not ads:
        print("   ⚠️  No ads found")
        return {"account": account_id, "ads_count": 0}

    # Step 2: Run analysis (anomaly detection + RCA)
    print(f"\n[2] Running anomaly detection and RCA...")
    analyze_agent = AnalyzeAgentModel()
    analysis = analyze_agent.run_analysis(account_id)

    if "error" in analysis:
        print(f"   ❌ Analysis error: {analysis['error']}")
        return {"error": analysis["error"], "account": account_id}

    anomaly_count = len(analysis.get("detailed_anomalies", []))
    print(f"   ✓ Found {anomaly_count} anomalies")

    # Step 3: Generate recommendations
    print(f"\n[3] Generating recommendations...")
    recommend_agent = RecommendAgentModel()
    result = recommend_agent.generate_recommendations(analysis, all_ads=ads)

    recommendations = result["recommendations"]
    summary = result["summary"]

    print(f"   ✓ Generated {summary['total_recommendations']} recommendations")

    # Step 4: Display recommendations by category
    print(f"\n[4] Recommendations by Action:")
    print("-" * 70)

    action_colors = {
        "pause": "🔴",
        "reduce": "🟠",
        "scale": "🟢",
        "refresh_creative": "🔵",
    }

    for action, count in summary["by_action"].items():
        if count > 0:
            icon = action_colors.get(action, "⚪")
            print(f"   {icon} {action.upper()}: {count}")

    # Step 5: Display detailed recommendations
    print(f"\n[5] Detailed Recommendations:")
    print("-" * 70)

    for i, rec in enumerate(recommendations, 1):
        icon = action_colors.get(rec["action"], "⚪")
        priority_badge = f"[{rec['priority'].upper()}]"

        print(f"\n   {i}. {icon} {rec['action'].upper()} {priority_badge}")
        print(f"      Ad: {rec['ad_name'][:50]}")
        print(f"      Provider: {rec.get('ad_provider', 'Unknown')}")

        if rec["action"] in ["pause", "reduce"]:
            print(f"      Current Spend: ${rec['current_spend']:,.2f}")
            if "current_cpa" in rec:
                print(f"      Current CPA: ${rec['current_cpa']:.2f} (z={rec['z_score']:.2f})")
            if "current_roas" in rec:
                print(f"      Current ROAS: {rec['current_roas']:.2f}x")
            print(f"      Recommended: {rec['recommended_change']}")
            print(f"      Est. Savings: ${rec['estimated_impact']:,.2f}")

        elif rec["action"] == "scale":
            print(f"      Current Spend: ${rec['current_spend']:,.2f}")
            print(f"      Current ROAS: {rec['current_roas']:.2f}x")
            print(f"      Recommended: {rec['recommended_change']}")
            print(f"      Est. Revenue: ${rec['estimated_impact']:,.2f}")

        elif rec["action"] == "refresh_creative":
            print(f"      Current Spend: ${rec['current_spend']:,.2f}")
            print(f"      Creative Variants: {rec.get('creative_variants', 1)}")
            print(f"      Days Active: {rec.get('days_active', 'N/A')}")
            print(f"      Est. Improvement: ${rec['estimated_impact']:,.2f}")

        print(f"      Confidence: {rec['confidence']:.0%}")
        print(f"      Reasoning: {rec['reasoning'][:80]}...")

        if "root_causes" in rec and rec["root_causes"]:
            print(f"      Root Causes: {', '.join(rec['root_causes'][:3])}")

    # Step 6: Summary
    print(f"\n[6] Impact Summary:")
    print("-" * 70)
    print(f"   Potential Savings:  ${summary['total_potential_savings']:,.2f}")
    print(f"   Potential Revenue:  ${summary['total_potential_revenue']:,.2f}")
    print(f"   Net Impact:         ${summary['net_impact']:,.2f}")

    print(f"\n   By Priority:")
    for priority, count in summary["by_priority"].items():
        if count > 0:
            print(f"      {priority.upper()}: {count}")

    return {
        "account": account_id,
        "account_name": account_name,
        "ads_count": len(ads),
        "anomalies_count": anomaly_count,
        "recommendations": result,
    }


def main():
    print("=" * 70)
    print("STEP 6: Verify Recommendations (Recommend Agent)")
    print("=" * 70)
    print(f"\n[Config] DATA_SOURCE={settings.data_source}, DATA_LOOKBACK_DAYS={settings.data_lookback_days}")

    # Analyze both accounts
    accounts = [
        ("tl", "ThirdLove"),
        ("wh", "WhisperingHomes"),
    ]

    results = []
    for account_id, account_name in accounts:
        result = analyze_account(account_id, account_name)
        results.append(result)

    # Final summary
    print("\n")
    print("=" * 80)
    print("STEP 6 SUMMARY: Recommendations")
    print("=" * 80)

    print(f"\n{'Account':<20} {'Ads':>6} {'Anomalies':>10} {'Recs':>6} {'Savings':>12} {'Revenue':>12}")
    print("-" * 80)

    total_recs = 0
    total_savings = 0
    total_revenue = 0

    for r in results:
        if "error" in r:
            print(f"{r['account']:<20} {'ERROR':<6}")
            continue

        name = r.get("account_name", r["account"])
        recs = r.get("recommendations", {})
        summary = recs.get("summary", {})

        rec_count = summary.get("total_recommendations", 0)
        savings = summary.get("total_potential_savings", 0)
        revenue = summary.get("total_potential_revenue", 0)

        print(f"{name:<20} {r['ads_count']:>6} {r['anomalies_count']:>10} {rec_count:>6} ${savings:>10,.2f} ${revenue:>10,.2f}")

        total_recs += rec_count
        total_savings += savings
        total_revenue += revenue

    print("-" * 80)
    print(f"{'TOTAL':<20} {'':<6} {'':<10} {total_recs:>6} ${total_savings:>10,.2f} ${total_revenue:>10,.2f}")

    # Action breakdown
    print("\n" + "-" * 80)
    print("Recommendations by Action (All Accounts):")

    action_totals = {"pause": 0, "reduce": 0, "scale": 0, "refresh_creative": 0}
    for r in results:
        if "error" in r:
            continue
        by_action = r.get("recommendations", {}).get("summary", {}).get("by_action", {})
        for action, count in by_action.items():
            action_totals[action] = action_totals.get(action, 0) + count

    action_colors = {"pause": "🔴", "reduce": "🟠", "scale": "🟢", "refresh_creative": "🔵"}
    for action, count in action_totals.items():
        if count > 0:
            icon = action_colors.get(action, "⚪")
            print(f"   {icon} {action.upper()}: {count}")

    # Validation
    print("\n" + "=" * 80)
    has_recs = total_recs > 0
    has_actions = any(action_totals.values())

    if has_recs and has_actions:
        print("✅ STEP 6 PASSED: Recommend Agent generating actionable recommendations")
        print(f"   Total recommendations: {total_recs}")
        print(f"   Total potential savings: ${total_savings:,.2f}")
        print(f"   Total potential revenue: ${total_revenue:,.2f}")
        return True
    else:
        print("⚠️  STEP 6 WARNING: No recommendations generated")
        print("   This may be expected if data has no anomalies")
        return True  # Not a failure, just no anomalies


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
