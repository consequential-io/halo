#!/usr/bin/env python3
"""
Gate 1 Manual Validation - Step 1: Verify Data Loaded

Run: python3 tests/manual/step1_verify_fixtures.py

Configure data source via environment:
  DATA_SOURCE=fixture python3 tests/manual/step1_verify_fixtures.py  (default)
  DATA_SOURCE=bq python3 tests/manual/step1_verify_fixtures.py
  DATA_SOURCE=bq DATA_LOOKBACK_DAYS=45 python3 tests/manual/step1_verify_fixtures.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from helpers.tools import get_ad_data
from config.settings import settings


def main():
    print("=" * 60)
    print("STEP 1: Verify Data Loaded")
    print("=" * 60)

    # Show configuration
    print(f"\n[Config] DATA_SOURCE={settings.data_source}, DATA_LOOKBACK_DAYS={settings.data_lookback_days}")

    # Load ThirdLove data
    source_label = "BigQuery" if settings.data_source == "bq" else "fixtures"
    print(f"\n[1] Loading ThirdLove (TL) from {source_label}...")
    tl_data = get_ad_data("tl", source=settings.data_source)

    if "error" in tl_data:
        print(f"❌ Error loading TL data: {tl_data['error']}")
        return False

    tl_ads = tl_data["ads"]
    tl_source = tl_data.get("metadata", {}).get("source", "fixture")
    print(f"✓ TL ads loaded: {len(tl_ads)} (source: {tl_source})")

    # Load WhisperingHomes data
    print(f"\n[2] Loading WhisperingHomes (WH) from {source_label}...")
    wh_data = get_ad_data("wh", source=settings.data_source)

    if "error" in wh_data:
        print(f"❌ Error loading WH data: {wh_data['error']}")
        return False

    wh_ads = wh_data["ads"]
    wh_source = wh_data.get("metadata", {}).get("source", "fixture")
    print(f"✓ WH ads loaded: {len(wh_ads)} (source: {wh_source})")

    # Check first ad structure
    print("\n[3] Checking TL ad structure...")
    first_ad = tl_ads[0]
    print(f"✓ First ad name: {first_ad.get('ad_name') or first_ad.get('AD_NAME')}")
    print(f"✓ Provider: {first_ad.get('ad_provider')}")
    print(f"✓ Spend: ${first_ad.get('Spend', 0):,.2f}")
    print(f"✓ ROAS: {first_ad.get('ROAS', 0):.2f}")

    # Check required fields
    print("\n[4] Verifying required fields...")
    required_fields = [
        "ad_name", "ad_provider", "Spend", "ROAS", "CPA", "CTR",
        "z_cpa", "z_roas", "z_ctr", "days_active"
    ]
    # Optional fields (only in fixtures, not BQ)
    optional_fields = ["Composite_Score"]

    missing = []
    for field in required_fields:
        # Check both cases
        has_field = field in first_ad or field.upper() in first_ad or field.lower() in first_ad
        if has_field:
            print(f"  ✓ {field}")
        else:
            print(f"  ✗ {field} MISSING")
            missing.append(field)

    # Check optional fields (informational only)
    for field in optional_fields:
        has_field = field in first_ad or field.upper() in first_ad or field.lower() in first_ad
        if has_field:
            print(f"  ✓ {field} (optional)")
        else:
            print(f"  ○ {field} (optional, not in BQ)")

    # Summary of providers
    print("\n[5] Provider breakdown (TL)...")
    providers = {}
    for ad in tl_ads:
        provider = ad.get("ad_provider", "Unknown")
        providers[provider] = providers.get(provider, 0) + 1

    for provider, count in sorted(providers.items(), key=lambda x: -x[1]):
        print(f"  - {provider}: {count} ads")

    # Final result
    print("\n" + "=" * 60)
    if not missing:
        print(f"✅ STEP 1 PASSED: Data loaded successfully (source: {settings.data_source})")
        print(f"   TL: {len(tl_ads)} ads | WH: {len(wh_ads)} ads")
        if settings.data_source == "bq":
            print(f"   Lookback: {settings.data_lookback_days} days")
        return True
    else:
        print(f"❌ STEP 1 FAILED: Missing fields: {missing}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
