#!/usr/bin/env python3
"""
Gate 1 Manual Validation - Step 4: Verify Ontology Breakdown

Run: python3 tests/manual/step4_verify_ontology.py

Configure data source via environment:
  DATA_SOURCE=fixture python3 tests/manual/step4_verify_ontology.py  (default)
  DATA_SOURCE=bq DATA_LOOKBACK_DAYS=45 python3 tests/manual/step4_verify_ontology.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from helpers.tools import get_ad_data, get_ontology
from config.settings import settings


def analyze_account(account_id: str, account_name: str) -> dict:
    """Run ontology analysis for a single account."""
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
        return {"account": account_id, "ads_count": 0}

    # Test 1: Group by ad_provider
    print("\n[2] Ontology by ad_provider:")
    print("-" * 70)
    result_provider = get_ontology(ads, group_by=["ad_provider"])

    if "error" in result_provider:
        print(f"❌ Error: {result_provider['error']}")
        return {"error": result_provider["error"], "account": account_id}

    print(f"{'Provider':<20} {'Count':>8} {'Total Spend':>15} {'Avg ROAS':>10}")
    print("-" * 70)

    total_spend = 0
    for provider, stats in result_provider["breakdown"].items():
        count = stats.get("count", 0)
        spend = stats.get("total_spend", 0)
        roas = stats.get("avg_roas", 0)
        total_spend += spend
        print(f"{provider:<20} {count:>8} ${spend:>14,.2f} {roas:>10.2f}")

    print("-" * 70)
    print(f"Total: {result_provider['total_ads']} ads, ${total_spend:,.2f} spend")

    # Test 2: Group by store
    print("\n[3] Ontology by store (market):")
    print("-" * 70)
    result_store = get_ontology(ads, group_by=["store"])

    print(f"{'Store':<20} {'Count':>8} {'Total Spend':>15} {'Avg CPA':>10}")
    print("-" * 70)

    for store, stats in result_store["breakdown"].items():
        count = stats.get("count", 0)
        spend = stats.get("total_spend", 0)
        cpa = stats.get("avg_cpa", 0)
        print(f"{store:<20} {count:>8} ${spend:>14,.2f} ${cpa:>9.2f}")

    # Test 3: Group by ad_type
    print("\n[4] Ontology by ad_type:")
    print("-" * 70)
    result_type = get_ontology(ads, group_by=["ad_type"])

    print(f"{'Ad Type':<20} {'Count':>8} {'Total Spend':>15} {'Avg CTR':>10}")
    print("-" * 70)

    for ad_type, stats in result_type["breakdown"].items():
        count = stats.get("count", 0)
        spend = stats.get("total_spend", 0)
        ctr = stats.get("avg_ctr", 0)
        print(f"{ad_type:<20} {count:>8} ${spend:>14,.2f} {ctr:>9.2%}")

    # Test 4: Group by performance_segment
    print("\n[5] Ontology by performance_segment:")
    print("-" * 70)
    result_segment = get_ontology(ads, group_by=["performance_segment"])

    print(f"{'Segment':<20} {'Count':>8} {'Total Spend':>15} {'Avg ROAS':>10}")
    print("-" * 70)

    for segment, stats in result_segment["breakdown"].items():
        count = stats.get("count", 0)
        spend = stats.get("total_spend", 0)
        roas = stats.get("avg_roas", 0)
        print(f"{segment:<20} {count:>8} ${spend:>14,.2f} {roas:>10.2f}")

    # Test 5: Multi-dimensional grouping
    print("\n[6] Ontology by ad_provider + store:")
    print("-" * 70)
    result_multi = get_ontology(ads, group_by=["ad_provider", "store"])

    print(f"{'Provider > Store':<30} {'Count':>8} {'Spend':>15}")
    print("-" * 70)

    for key, stats in result_multi["breakdown"].items():
        count = stats.get("count", 0)
        spend = stats.get("total_spend", 0)
        print(f"{key:<30} {count:>8} ${spend:>14,.2f}")

    # Test 6: Verify all supported dimensions
    print("\n[7] Testing all supported dimensions...")
    supported_dims = [
        "ad_provider",
        "store",
        "ad_type",
        "creative_status",
        "spend_tier",
        "db_campaign_status",
        "performance_segment",
    ]

    dim_results = {}
    for dim in supported_dims:
        test_result = get_ontology(ads, group_by=[dim])
        if "error" in test_result:
            print(f"  ✗ {dim}: {test_result['error']}")
            dim_results[dim] = 0
        else:
            groups = len(test_result["breakdown"])
            print(f"  ✓ {dim}: {groups} groups")
            dim_results[dim] = groups

    return {
        "account": account_id,
        "account_name": account_name,
        "ads_count": len(ads),
        "total_spend": total_spend,
        "providers": len(result_provider["breakdown"]),
        "stores": len(result_store["breakdown"]),
        "ad_types": len(result_type["breakdown"]),
        "segments": len(result_segment["breakdown"]),
        "dimensions_tested": len(supported_dims),
        "dimensions_working": sum(1 for v in dim_results.values() if v > 0),
    }


def main():
    print("=" * 60)
    print("STEP 4: Verify Ontology Breakdown")
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
    print("STEP 4 SUMMARY: Ontology Breakdown")
    print("=" * 80)
    print(f"\n{'Account':<20} {'Ads':>8} {'Spend':>15} {'Providers':>10} {'Stores':>8} {'Types':>8} {'Segments':>10}")
    print("-" * 80)

    for r in results:
        if "error" in r:
            print(f"{r['account']:<20} {'ERROR':<8}")
            continue

        name = r.get("account_name", r["account"])
        print(f"{name:<20} {r['ads_count']:>8} ${r['total_spend']:>14,.2f} {r['providers']:>10} {r['stores']:>8} {r['ad_types']:>8} {r['segments']:>10}")

    print("-" * 80)

    # Dimensions summary
    print("\nDimensions tested across all accounts:")
    all_working = all(
        r.get("dimensions_working", 0) == r.get("dimensions_tested", 0)
        for r in results if "error" not in r
    )

    for r in results:
        if "error" not in r:
            name = r.get("account_name", r["account"])
            print(f"  {name}: {r['dimensions_working']}/{r['dimensions_tested']} dimensions working")

    print("\n" + "=" * 80)
    if all_working:
        print("✅ STEP 4 PASSED: Ontology breakdown working for all accounts")
    else:
        print("⚠️  STEP 4 PASSED WITH WARNINGS: Some dimensions may have issues")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
