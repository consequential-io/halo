#!/usr/bin/env python3
"""
Gate 1 Manual Validation - Step 5: Verify RCA (Root Cause Analysis)

Run: python3 tests/manual/step5_verify_rca.py

Configure data source via environment:
  DATA_SOURCE=fixture python3 tests/manual/step5_verify_rca.py  (default)
  DATA_SOURCE=bq DATA_LOOKBACK_DAYS=45 python3 tests/manual/step5_verify_rca.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from helpers.tools import get_ad_data, detect_anomalies, run_rca
from config.settings import settings


def run_rca_for_metric(ads: list, metric: str, metric_label: str, direction: str, threshold: float = 1.5) -> dict:
    """Run RCA analysis for a specific metric."""
    print(f"\n[RCA] Analyzing {metric_label} anomalies...")

    # Find anomalies
    anomaly_result = detect_anomalies(
        ads,
        metric=metric,
        threshold_sigma=threshold,
        direction=direction
    )

    anomalies = anomaly_result.get("anomalies", [])
    print(f"✓ Found {len(anomalies)} {metric_label} anomalies to analyze")

    if not anomalies:
        return {"metric": metric_label, "anomalies_found": 0, "rca_results": []}

    rca_results = []

    # Run RCA on all anomalies
    for i, anomaly in enumerate(anomalies):
        ad = anomaly["ad"]
        ad_name = ad.get("ad_name") or ad.get("AD_NAME", "Unknown")
        # Handle both raw metrics (CPA, ROAS) and z-score metrics (z_cpa, z_roas)
        base_metric = metric.replace("z_", "").upper() if metric.startswith("z_") else metric.upper()

        print(f"\n--- {metric_label} Anomaly {i+1}: {ad_name[:50]} ---")
        print(f"    z_score: {anomaly['z_score']:.2f} | {base_metric}: {ad.get(base_metric, 0):.2f} | Spend: ${ad.get('Spend', 0):,.2f}")

        # Run RCA
        rca = run_rca(ad, ads, base_metric)

        # Display summary
        print(f"\n    Root Causes Found: {len(rca['root_causes'])}")

        if rca["root_causes"]:
            for rc in rca["root_causes"]:
                impact_icon = "🔴" if rc["impact"] == "high" else "🟡" if rc["impact"] == "medium" else "🟢"
                print(f"      {impact_icon} [{rc['impact'].upper()}] {rc['factor']}")
                print(f"         {rc['finding'][:70]}")

        # Display recommendations
        print(f"\n    Recommendations:")
        for j, rec in enumerate(rca["recommended_actions"][:3], 1):
            print(f"      {j}. {rec}")

        rca_results.append({
            "ad_name": ad_name,
            "z_score": anomaly["z_score"],
            "root_causes": len(rca["root_causes"]),
            "high_impact": rca["impact_summary"]["high_impact_factors"],
            "recommendations": len(rca["recommended_actions"]),
        })

    return {
        "metric": metric_label,
        "anomalies_found": len(anomalies),
        "rca_results": rca_results,
    }


def analyze_account(account_id: str, account_name: str) -> dict:
    """Run RCA analysis for a single account."""
    print(f"\n{'='*70}")
    print(f"ANALYZING: {account_name} ({account_id.upper()})")
    print("=" * 70)

    # Load data
    source_label = "BigQuery" if settings.data_source == "bq" else "fixtures"
    print(f"\n[1] Loading ad data from {source_label}...")
    data = get_ad_data(account_id, source=settings.data_source)

    if "error" in data:
        print(f"❌ Error loading data: {data['error']}")
        return {"error": data["error"], "account": account_id}

    ads = data["ads"]
    print(f"✓ Loaded {len(ads)} ads")

    if not ads:
        print("⚠️  No ads found")
        return {"account": account_id, "ads_count": 0}

    # Run RCA for Low ROAS (using raw ROAS, not pre-computed z_roas)
    # This ensures consistency with step 3 which uses raw metrics
    roas_results = run_rca_for_metric(
        ads,
        metric="ROAS",
        metric_label="Low ROAS",
        direction="low",
        threshold=2.0
    )

    # Run RCA for High CPA (using raw CPA, not pre-computed z_cpa)
    # This ensures consistency with step 2 which uses raw metrics
    cpa_results = run_rca_for_metric(
        ads,
        metric="CPA",
        metric_label="High CPA",
        direction="high",
        threshold=2.0
    )

    # Validate RCA output structure
    print("\n[2] Validating RCA output structure...")
    required_keys = ["anomaly_summary", "root_causes", "comparison_to_similar", "recommended_actions", "impact_summary"]

    # Get a sample RCA for validation (use raw ROAS for consistency)
    sample_anomalies = detect_anomalies(ads, metric="ROAS", threshold_sigma=1.5, direction="low").get("anomalies", [])
    if sample_anomalies:
        sample_rca = run_rca(sample_anomalies[0]["ad"], ads, "ROAS")
        all_present = True
        for key in required_keys:
            if key in sample_rca:
                print(f"  ✓ {key}")
            else:
                print(f"  ✗ {key} MISSING")
                all_present = False
    else:
        all_present = True
        print("  ⚠️  No anomalies to validate structure (data may be clean)")

    return {
        "account": account_id,
        "account_name": account_name,
        "ads_count": len(ads),
        "roas_analysis": roas_results,
        "cpa_analysis": cpa_results,
        "structure_valid": all_present,
    }


def main():
    print("=" * 70)
    print("STEP 5: Verify RCA (Root Cause Analysis)")
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
    print("STEP 5 SUMMARY: RCA (Root Cause Analysis)")
    print("=" * 80)

    print(f"\n{'Account':<20} {'Ads':>6} {'ROAS Anom':>10} {'ROAS RCAs':>10} {'CPA Anom':>10} {'CPA RCAs':>10}")
    print("-" * 80)

    total_roas_anomalies = 0
    total_cpa_anomalies = 0
    total_roas_rcas = 0
    total_cpa_rcas = 0

    for r in results:
        if "error" in r:
            print(f"{r['account']:<20} {'ERROR':<6}")
            continue

        name = r.get("account_name", r["account"])
        roas = r.get("roas_analysis", {})
        cpa = r.get("cpa_analysis", {})

        roas_anom = roas.get("anomalies_found", 0)
        roas_rca = len(roas.get("rca_results", []))
        cpa_anom = cpa.get("anomalies_found", 0)
        cpa_rca = len(cpa.get("rca_results", []))

        print(f"{name:<20} {r['ads_count']:>6} {roas_anom:>10} {roas_rca:>10} {cpa_anom:>10} {cpa_rca:>10}")

        total_roas_anomalies += roas_anom
        total_cpa_anomalies += cpa_anom
        total_roas_rcas += roas_rca
        total_cpa_rcas += cpa_rca

    print("-" * 80)
    print(f"{'TOTAL':<20} {'':<6} {total_roas_anomalies:>10} {total_roas_rcas:>10} {total_cpa_anomalies:>10} {total_cpa_rcas:>10}")

    # Root cause summary
    print("\n" + "-" * 80)
    print("Root Causes Identified:")

    for r in results:
        if "error" in r:
            continue

        name = r.get("account_name", r["account"])
        print(f"\n  {name}:")

        for analysis in [r.get("roas_analysis", {}), r.get("cpa_analysis", {})]:
            metric = analysis.get("metric", "Unknown")
            for rca in analysis.get("rca_results", []):
                high = rca.get("high_impact", 0)
                total = rca.get("root_causes", 0)
                if total > 0:
                    print(f"    - {rca['ad_name'][:40]}: {total} factors ({high} high impact)")

    print("\n" + "=" * 80)
    all_valid = all(r.get("structure_valid", True) for r in results if "error" not in r)

    if all_valid:
        print("✅ STEP 5 PASSED: RCA working correctly for both metrics")
        print(f"   Low ROAS anomalies analyzed: {total_roas_rcas}")
        print(f"   High CPA anomalies analyzed: {total_cpa_rcas}")
    else:
        print("❌ STEP 5 FAILED: RCA output structure incomplete")

    return all_valid


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
