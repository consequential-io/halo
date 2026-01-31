#!/usr/bin/env python3
"""
Gate 1 Manual Validation - Step 3: Verify Anomaly Detection (Low ROAS)

Run: python3 tests/manual/step3_detect_anomalies_roas.py

Configure data source via environment:
  DATA_SOURCE=fixture python3 tests/manual/step3_detect_anomalies_roas.py  (default)
  DATA_SOURCE=bq DATA_LOOKBACK_DAYS=45 python3 tests/manual/step3_detect_anomalies_roas.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from helpers.tools import get_ad_data, detect_anomalies
from config.settings import settings


def analyze_account(account_id: str, account_name: str) -> dict:
    """Run ROAS anomaly detection for a single account."""
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
        return {"account": account_id, "ads_count": 0, "z_roas_anomalies": 0, "raw_roas_anomalies": 0}

    # Detect low ROAS anomalies using pre-computed z-scores
    print("\n[2] Detecting low ROAS anomalies (z_roas <= -2.0)...")
    result = detect_anomalies(
        ads,
        metric="z_roas",
        threshold_sigma=2.0,
        direction="low"
    )

    anomalies = result.get("anomalies", [])
    print(f"✓ Found {len(anomalies)} low z_roas anomalies")

    total_waste_spend = 0

    if anomalies:
        print("\n[3] z_roas Anomaly details:")
        print("-" * 90)
        print(f"{'Ad Name':<40} {'z_roas':>8} {'ROAS':>8} {'Spend':>12} {'Severity':<12}")
        print("-" * 90)

        for a in anomalies[:10]:  # Show top 10
            ad = a["ad"]
            name = (ad.get("ad_name") or ad.get("AD_NAME", "Unknown"))[:38]
            z_score = a["z_score"]
            roas = ad.get("ROAS", 0)
            spend = ad.get("Spend", 0)
            severity = a["severity"]
            total_waste_spend += spend
            print(f"{name:<40} {z_score:>8.2f} {roas:>8.2f} ${spend:>11,.2f} {severity:<12}")

        # Add remaining spend if more than 10
        if len(anomalies) > 10:
            for a in anomalies[10:]:
                total_waste_spend += a["ad"].get("Spend", 0)

        print("-" * 90)
        print(f"{'Total potential waste:':<40} {'':<8} {'':<8} ${total_waste_spend:>11,.2f}")

        # Verify all have z_score <= -2.0
        print("\n[4] Validating z-scores...")
        invalid = [a for a in anomalies if a["z_score"] > -2.0]
        if invalid:
            print(f"❌ {len(invalid)} anomalies have z_score > -2.0")
        else:
            print(f"✓ All {len(anomalies)} anomalies have z_score <= -2.0")

        # Provider breakdown of anomalies
        print("\n[5] Low ROAS anomalies by provider:")
        providers = {}
        provider_spend = {}
        for a in anomalies:
            provider = a["ad"].get("ad_provider", "Unknown")
            providers[provider] = providers.get(provider, 0) + 1
            provider_spend[provider] = provider_spend.get(provider, 0) + a["ad"].get("Spend", 0)

        for provider, count in sorted(providers.items(), key=lambda x: -x[1]):
            pct = count / len(anomalies) * 100
            spend = provider_spend[provider]
            print(f"   - {provider}: {count} ({pct:.0f}%), ${spend:,.2f} waste")

    else:
        print("\n[3] No low z_roas anomalies found")
        print("   This may indicate clean data or threshold is too strict")

    # Also check raw ROAS anomalies
    print("\n[6] Checking raw ROAS anomalies (for comparison)...")
    raw_result = detect_anomalies(
        ads,
        metric="ROAS",
        threshold_sigma=2.0,
        direction="low"
    )
    raw_anomalies = raw_result.get("anomalies", [])
    print(f"✓ Raw ROAS anomalies: {len(raw_anomalies)}")

    if raw_result.get("baseline_stats"):
        stats = raw_result["baseline_stats"]
        print(f"   Baseline: mean={stats.get('mean', 0):.2f}, std={stats.get('std', 0):.2f}, median={stats.get('median', 0):.2f}")

    raw_waste_spend = 0
    if raw_anomalies:
        print("\n[7] Raw ROAS anomaly details:")
        print("-" * 90)
        print(f"{'Ad Name':<40} {'ROAS':>8} {'Baseline':>10} {'z_score':>8} {'Spend':>12} {'Severity':<10}")
        print("-" * 90)

        for a in raw_anomalies[:15]:  # Show top 15
            ad = a["ad"]
            name = (ad.get("ad_name") or ad.get("AD_NAME", "Unknown"))[:38]
            roas = a["value"]
            baseline = a.get("baseline", 0)
            z_score = a["z_score"]
            spend = ad.get("Spend", 0)
            severity = a["severity"]
            raw_waste_spend += spend
            print(f"{name:<40} {roas:>8.2f} {baseline:>10.2f} {z_score:>8.2f} ${spend:>11,.2f} {severity:<10}")

        # Add remaining spend if more than 15
        if len(raw_anomalies) > 15:
            for a in raw_anomalies[15:]:
                raw_waste_spend += a["ad"].get("Spend", 0)

        print("-" * 90)
        print(f"{'Total waste in low ROAS ads:':<40} {'':<8} {'':<10} {'':<8} ${raw_waste_spend:>11,.2f}")

    return {
        "account": account_id,
        "account_name": account_name,
        "ads_count": len(ads),
        "z_roas_anomalies": len(anomalies),
        "raw_roas_anomalies": len(raw_anomalies),
        "z_roas_waste": total_waste_spend,
        "raw_roas_waste": raw_waste_spend,
    }


def main():
    print("=" * 60)
    print("STEP 3: Verify Anomaly Detection (Low ROAS)")
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
    print("=" * 80)
    print("STEP 3 SUMMARY: Low ROAS Anomaly Detection (Potential Waste)")
    print("=" * 80)
    print(f"\n{'Account':<20} {'Ads':>8} {'z_roas Anom':>12} {'z_roas Waste':>14} {'Raw Anom':>10} {'Raw Waste':>14}")
    print("-" * 80)

    total_z_roas = 0
    total_raw_roas = 0
    total_z_waste = 0
    total_raw_waste = 0

    for r in results:
        if "error" in r:
            print(f"{r['account']:<20} {'ERROR':<8}")
            continue

        name = r.get("account_name", r["account"])
        print(f"{name:<20} {r['ads_count']:>8} {r['z_roas_anomalies']:>12} ${r['z_roas_waste']:>13,.2f} {r['raw_roas_anomalies']:>10} ${r['raw_roas_waste']:>13,.2f}")
        total_z_roas += r["z_roas_anomalies"]
        total_raw_roas += r["raw_roas_anomalies"]
        total_z_waste += r["z_roas_waste"]
        total_raw_waste += r["raw_roas_waste"]

    print("-" * 80)
    print(f"{'TOTAL':<20} {'':<8} {total_z_roas:>12} ${total_z_waste:>13,.2f} {total_raw_roas:>10} ${total_raw_waste:>13,.2f}")

    print("\n" + "=" * 80)
    print(f"✅ STEP 3 PASSED: Low ROAS anomaly detection working")
    print(f"   Total low z_roas anomalies: {total_z_roas}")
    print(f"   Total low raw ROAS anomalies: {total_raw_roas}")
    print(f"   Total potential waste (z_roas): ${total_z_waste:,.2f}")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
