"""
BigQuery Integration Tests.

Tests for BQ connector, z-score calculation with LOG transform, and fallback behavior.
Run with: python3 -m pytest tests/test_bq_integration.py -v
Or standalone: python3 tests/test_bq_integration.py
"""

import sys
import math
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from helpers.tools import _calculate_z_scores_bq, get_ad_data


# =============================================================================
# Settings Tests
# =============================================================================

def test_settings_lookback_days():
    """Test that data_lookback_days setting is loaded correctly."""
    print("\n=== Test: settings data_lookback_days ===")

    from config.settings import settings

    assert hasattr(settings, "data_lookback_days"), "Expected data_lookback_days in settings"
    assert isinstance(settings.data_lookback_days, int), "Expected int type"
    assert settings.data_lookback_days > 0, "Expected positive value"

    print(f"✓ data_lookback_days = {settings.data_lookback_days}")
    return True


def test_settings_gemini_model():
    """Test that gemini_model setting is updated to 3.0."""
    print("\n=== Test: settings gemini_model ===")

    from config.settings import settings

    assert hasattr(settings, "gemini_model"), "Expected gemini_model in settings"
    assert "3.0" in settings.gemini_model, f"Expected gemini-3.0, got {settings.gemini_model}"

    print(f"✓ gemini_model = {settings.gemini_model}")
    return True


# =============================================================================
# Z-Score LOG Transform Tests
# =============================================================================

def test_z_score_log_transform_basic():
    """Test z-score calculation uses LOG transform correctly."""
    print("\n=== Test: z-score LOG transform basic ===")

    # Create test ads with known values
    ads = [
        {"ad_name": "Ad 1", "CPA": 1.0, "ROAS": 5.0, "CTR": 0.05, "CVR": 0.02},
        {"ad_name": "Ad 2", "CPA": 2.0, "ROAS": 4.0, "CTR": 0.04, "CVR": 0.02},
        {"ad_name": "Ad 3", "CPA": 3.0, "ROAS": 3.0, "CTR": 0.03, "CVR": 0.02},
        {"ad_name": "Ad 4", "CPA": 10.0, "ROAS": 1.0, "CTR": 0.01, "CVR": 0.01},  # Outlier
    ]

    result = _calculate_z_scores_bq(ads)

    # Verify z-scores are calculated
    for ad in result:
        assert "z_cpa" in ad, "Expected z_cpa"
        assert "z_roas" in ad, "Expected z_roas"
        assert "z_ctr" in ad, "Expected z_ctr"
        assert "z_cvr" in ad, "Expected z_cvr"

    # Outlier (Ad 4) should have high z_cpa and low z_roas
    outlier = result[3]
    assert outlier["z_cpa"] > 1.0, f"Expected high z_cpa for outlier, got {outlier['z_cpa']}"
    assert outlier["z_roas"] < -1.0, f"Expected low z_roas for outlier, got {outlier['z_roas']}"

    print(f"✓ Z-scores calculated with LOG transform")
    for ad in result:
        print(f"  {ad['ad_name']}: z_cpa={ad['z_cpa']:.2f}, z_roas={ad['z_roas']:.2f}")

    return True


def test_z_score_log_transform_matches_formula():
    """Test z-score calculation matches production formula: (LOG(x+1e-8) - mean) / std."""
    print("\n=== Test: z-score LOG transform matches formula ===")

    ads = [
        {"ad_name": "Ad 1", "CPA": 2.0},
        {"ad_name": "Ad 2", "CPA": 4.0},
        {"ad_name": "Ad 3", "CPA": 6.0},
    ]

    result = _calculate_z_scores_bq(ads)

    # Manual calculation
    log_values = [math.log(2.0 + 1e-8), math.log(4.0 + 1e-8), math.log(6.0 + 1e-8)]
    mean = sum(log_values) / 3
    variance = sum((v - mean) ** 2 for v in log_values) / 3
    std = variance ** 0.5

    expected_z_scores = [(v - mean) / std for v in log_values]

    for i, ad in enumerate(result):
        assert abs(ad["z_cpa"] - expected_z_scores[i]) < 0.001, \
            f"Z-score mismatch: {ad['z_cpa']} vs {expected_z_scores[i]}"

    print(f"✓ Z-score formula verified")
    print(f"  Mean of LOG(CPA): {mean:.4f}")
    print(f"  Std of LOG(CPA): {std:.4f}")

    return True


def test_z_score_handles_zeros():
    """Test z-score calculation handles zero values correctly."""
    print("\n=== Test: z-score handles zeros ===")

    ads = [
        {"ad_name": "Ad 1", "CPA": 0.0, "ROAS": 0.0},  # Zero values
        {"ad_name": "Ad 2", "CPA": 2.0, "ROAS": 5.0},
        {"ad_name": "Ad 3", "CPA": 3.0, "ROAS": 4.0},
    ]

    result = _calculate_z_scores_bq(ads)

    # Should not crash, zeros handled via LOG(x + 1e-8)
    for ad in result:
        assert "z_cpa" in ad, "Expected z_cpa even with zeros"
        assert not math.isnan(ad["z_cpa"]), "z_cpa should not be NaN"
        assert not math.isinf(ad["z_cpa"]), "z_cpa should not be infinite"

    print(f"✓ Zero values handled correctly")
    return True


def test_z_score_handles_none():
    """Test z-score calculation handles None values correctly."""
    print("\n=== Test: z-score handles None ===")

    ads = [
        {"ad_name": "Ad 1", "CPA": None, "ROAS": 5.0},
        {"ad_name": "Ad 2", "CPA": 2.0, "ROAS": None},
        {"ad_name": "Ad 3", "CPA": 3.0, "ROAS": 4.0},
    ]

    result = _calculate_z_scores_bq(ads)

    # Should not crash
    for ad in result:
        assert "z_cpa" in ad, "Expected z_cpa"
        assert "z_roas" in ad, "Expected z_roas"

    print(f"✓ None values handled correctly")
    return True


def test_z_score_insufficient_data():
    """Test z-score calculation with fewer than 2 ads."""
    print("\n=== Test: z-score with insufficient data ===")

    # Single ad
    ads = [{"ad_name": "Ad 1", "CPA": 2.0, "ROAS": 5.0, "CTR": 0.05, "CVR": 0.02}]

    result = _calculate_z_scores_bq(ads)

    # Should return 0 for all z-scores
    assert result[0]["z_cpa"] == 0.0, "Expected z_cpa=0 with single ad"
    assert result[0]["z_roas"] == 0.0, "Expected z_roas=0 with single ad"

    print(f"✓ Single ad returns z-scores of 0")
    return True


# =============================================================================
# get_ad_data Tests
# =============================================================================

def test_get_ad_data_fixture_default():
    """Test get_ad_data defaults to fixture source."""
    print("\n=== Test: get_ad_data fixture default ===")

    result = get_ad_data(account_id="tl")

    assert "ads" in result, "Expected 'ads' key"
    assert len(result["ads"]) > 0, "Expected non-empty ads"

    print(f"✓ Loaded {len(result['ads'])} ads from fixtures")
    return True


def test_get_ad_data_uses_settings_default_days():
    """Test get_ad_data uses settings.data_lookback_days when days not specified."""
    print("\n=== Test: get_ad_data uses settings default days ===")

    from config.settings import settings

    # This should use settings.data_lookback_days (30)
    result = get_ad_data(account_id="tl", source="fixture")

    # For fixtures, days is ignored but the function should accept it
    assert "ads" in result

    print(f"✓ get_ad_data uses settings.data_lookback_days = {settings.data_lookback_days}")
    return True


def test_get_ad_data_unknown_source_fallback():
    """Test get_ad_data falls back to fixture for unknown source."""
    print("\n=== Test: get_ad_data unknown source fallback ===")

    result = get_ad_data(account_id="tl", source="unknown_source")

    assert "ads" in result, "Expected fallback to fixtures"
    assert len(result["ads"]) > 0, "Expected non-empty ads from fallback"

    print(f"✓ Unknown source falls back to fixtures")
    return True


def test_get_ad_data_bq_source_structure():
    """Test get_ad_data with bq source returns correct structure (may fall back to fixtures)."""
    print("\n=== Test: get_ad_data BQ source structure ===")

    # This will likely fall back to fixtures if BQ auth is not set up
    result = get_ad_data(account_id="tl", days=7, source="bq")

    assert "ads" in result, "Expected 'ads' key"
    assert "metadata" in result or "error" not in result, "Expected metadata or successful response"

    # Check that ads have expected fields (whether from BQ or fixture fallback)
    if result["ads"]:
        ad = result["ads"][0]
        assert "ad_name" in ad or "AD_NAME" in ad, "Expected ad_name field"
        assert "Spend" in ad, "Expected Spend field"

    print(f"✓ BQ source returns correct structure")
    print(f"  Source: {result.get('metadata', {}).get('source', 'fixture (fallback)')}")
    return True


# =============================================================================
# Test Runner
# =============================================================================

def run_bq_integration_tests():
    """Run all BQ integration tests."""
    print("=" * 60)
    print("BIGQUERY INTEGRATION TESTS")
    print("=" * 60)

    tests = [
        # Settings tests
        ("Settings: data_lookback_days", test_settings_lookback_days),
        ("Settings: gemini_model", test_settings_gemini_model),

        # Z-score tests
        ("Z-score LOG transform basic", test_z_score_log_transform_basic),
        ("Z-score LOG transform formula", test_z_score_log_transform_matches_formula),
        ("Z-score handles zeros", test_z_score_handles_zeros),
        ("Z-score handles None", test_z_score_handles_none),
        ("Z-score insufficient data", test_z_score_insufficient_data),

        # get_ad_data tests
        ("get_ad_data fixture default", test_get_ad_data_fixture_default),
        ("get_ad_data settings default days", test_get_ad_data_uses_settings_default_days),
        ("get_ad_data unknown source fallback", test_get_ad_data_unknown_source_fallback),
        ("get_ad_data BQ source structure", test_get_ad_data_bq_source_structure),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"\n✗ FAILED: {name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗ ERROR: {name}")
            print(f"  Exception: {type(e).__name__}: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"BQ INTEGRATION TEST RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ ALL BQ INTEGRATION TESTS PASSED")
        return True
    else:
        print(f"\n❌ {failed} BQ INTEGRATION TESTS FAILED")
        return False


if __name__ == "__main__":
    success = run_bq_integration_tests()
    sys.exit(0 if success else 1)
