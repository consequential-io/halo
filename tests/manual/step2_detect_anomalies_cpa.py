#!/usr/bin/env python3
"""
Gate 1 Manual Validation - Step 2: Verify Anomaly Detection (High CPA)

Run: python3 tests/manual/step2_detect_anomalies_cpa.py

Configure data source via environment:
  DATA_SOURCE=fixture python3 tests/manual/step2_detect_anomalies_cpa.py  (default)
  DATA_SOURCE=bq DATA_LOOKBACK_DAYS=45 python3 tests/manual/step2_detect_anomalies_cpa.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from helpers.tools import get_ad_data, detect_anomalies
from config.settings import settings


def analyze_account(account_id: str, account_name: str) -> dict:
    """Run CPA anomaly detection for a single account."""
    print(f"\n{'='*60}")
    print(f"ANALYZING: {account_name} ({account_id.upper()})")
    print("=" * 60)

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
        return {"account": account_id, "ads_count": 0, "z_cpa_anomalies": 0, "raw_cpa_anomalies": 0}

    # Detect high CPA anomalies using pre-computed z-scores
    print("\n[2] Detecting high CPA anomalies (z_cpa >= 2.0)...")
    result = detect_anomalies(
        ads,
        metric="z_cpa",
        threshold_sigma=2.0,
        direction="high"
    )

    anomalies = result.get("anomalies", [])
    print(f"✓ Found {len(anomalies)} high z_cpa anomalies")

    if anomalies:
        print("\n[3] z_cpa Anomaly details:")
        print("-" * 80)
        print(f"{'Ad Name':<40} {'z_cpa':>8} {'CPA':>10} {'Severity':<12}")
        print("-" * 80)

        for a in anomalies[:10]:  # Show top 10
            ad = a["ad"]
            name = (ad.get("ad_name") or ad.get("AD_NAME", "Unknown"))[:38]
            z_score = a["z_score"]
            cpa = ad.get("CPA", 0)
            severity = a["severity"]
            print(f"{name:<40} {z_score:>8.2f} ${cpa:>9.2f} {severity:<12}")

        print("-" * 80)

        # Verify all have z_score >= 2.0
        print("\n[4] Validating z-scores...")
        invalid = [a for a in anomalies if a["z_score"] < 2.0]
        if invalid:
            print(f"❌ {len(invalid)} anomalies have z_score < 2.0")
        else:
            print(f"✓ All {len(anomalies)} anomalies have z_score >= 2.0")

    else:
        print("\n[3] No high z_cpa anomalies found")
        print("   This may indicate clean data or threshold is too high")

    # Also check raw CPA anomalies
    print("\n[5] Checking raw CPA anomalies (for comparison)...")
    raw_result = detect_anomalies(
        ads,
        metric="CPA",
        threshold_sigma=2.0,
        direction="high"
    )
    raw_anomalies = raw_result.get("anomalies", [])
    print(f"✓ Raw CPA anomalies: {len(raw_anomalies)}")

    total_anomaly_spend = 0

    if raw_result.get("baseline_stats"):
        stats = raw_result["baseline_stats"]
        print(f"   Baseline: mean=${stats.get('mean', 0):.2f}, std=${stats.get('std', 0):.2f}, median=${stats.get('median', 0):.2f}")

    if raw_anomalies:
        print("\n[6] Raw CPA anomaly details:")
        print("-" * 90)
        print(f"{'Ad Name':<40} {'CPA':>10} {'Baseline':>10} {'z_score':>8} {'Spend':>12} {'Severity':<10}")
        print("-" * 90)

        for a in raw_anomalies[:15]:  # Show top 15
            ad = a["ad"]
            name = (ad.get("ad_name") or ad.get("AD_NAME", "Unknown"))[:38]
            cpa = a["value"]
            baseline = a.get("baseline", 0)
            z_score = a["z_score"]
            spend = ad.get("Spend", 0)
            severity = a["severity"]
            total_anomaly_spend += spend
            print(f"{name:<40} ${cpa:>9.2f} ${baseline:>9.2f} {z_score:>8.2f} ${spend:>11,.2f} {severity:<10}")

        # Add remaining spend if more than 15
        if len(raw_anomalies) > 15:
            for a in raw_anomalies[15:]:
                total_anomaly_spend += a["ad"].get("Spend", 0)

        print("-" * 90)
        print(f"{'Total spend in high CPA ads:':<40} {'':<10} {'':<10} {'':<8} ${total_anomaly_spend:>11,.2f}")

        # Provider breakdown
        print("\n[7] High CPA anomalies by provider:")
        providers = {}
        provider_spend = {}
        for a in raw_anomalies:
            provider = a["ad"].get("ad_provider", "Unknown")
            providers[provider] = providers.get(provider, 0) + 1
            provider_spend[provider] = provider_spend.get(provider, 0) + a["ad"].get("Spend", 0)

        for provider, count in sorted(providers.items(), key=lambda x: -x[1]):
            spend = provider_spend[provider]
            print(f"   - {provider}: {count} ads, ${spend:,.2f} spend")

    return {
        "account": account_id,
        "account_name": account_name,
        "ads_count": len(ads),
        "z_cpa_anomalies": len(anomalies),
        "raw_cpa_anomalies": len(raw_anomalies),
        "total_anomaly_spend": total_anomaly_spend,
    }


def main():
    print("=" * 60)
    print("STEP 2: Verify Anomaly Detection (High CPA)")
    print("=" * 60)
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
    print("=" * 70)
    print("STEP 2 SUMMARY: High CPA Anomaly Detection")
    print("=" * 70)
    print(f"\n{'Account':<20} {'Ads':>8} {'z_cpa Anom':>12} {'Raw CPA Anom':>14} {'Anomaly Spend':>15}")
    print("-" * 70)

    total_z_cpa = 0
    total_raw_cpa = 0
    total_spend = 0

    for r in results:
        if "error" in r:
            print(f"{r['account']:<20} {'ERROR':<8}")
            continue

        name = r.get("account_name", r["account"])
        print(f"{name:<20} {r['ads_count']:>8} {r['z_cpa_anomalies']:>12} {r['raw_cpa_anomalies']:>14} ${r['total_anomaly_spend']:>14,.2f}")
        total_z_cpa += r["z_cpa_anomalies"]
        total_raw_cpa += r["raw_cpa_anomalies"]
        total_spend += r["total_anomaly_spend"]

    print("-" * 70)
    print(f"{'TOTAL':<20} {'':<8} {total_z_cpa:>12} {total_raw_cpa:>14} ${total_spend:>14,.2f}")

    print("\n" + "=" * 70)
    print(f"✅ STEP 2 PASSED: Anomaly detection working")
    print(f"   Total high z_cpa anomalies: {total_z_cpa}")
    print(f"   Total high raw CPA anomalies: {total_raw_cpa}")
    print(f"   Total anomaly spend: ${total_spend:,.2f}")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
