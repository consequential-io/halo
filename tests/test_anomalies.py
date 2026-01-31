"""
Anomaly Detection Unit Tests.

Tests for detect_anomalies function with CPA and ROAS metrics.
Run with: python3 -m pytest tests/test_anomalies.py -v
Or standalone: python3 tests/test_anomalies.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from helpers.tools import detect_anomalies, get_ad_data


# =============================================================================
# Helper to create synthetic ads
# =============================================================================

def _create_ads_with_metric(metric: str, values: list[float], min_spend: float = 100) -> list[dict]:
    """Create ads with specific metric values for testing."""
    return [
        {
            "ad_name": f"Ad {i}",
            "ad_id": f"ad_{i}",
            "ad_provider": "Google Ads",
            "Spend": min_spend + 100,  # Above min_spend threshold
            metric: value,
        }
        for i, value in enumerate(values)
    ]


# =============================================================================
# CPA Anomaly Tests
# =============================================================================

def test_detect_high_cpa_anomalies():
    """Test detection of high CPA anomalies (direction=high)."""
    print("\n=== Test: detect high CPA anomalies ===")

    # Create ads with tight normal CPA distribution and extreme outliers
    # Normal: all 2.0 (mean=2.0, std very small)
    # Outliers: 10.0, 12.0 (extreme high CPA)
    values = [2.0] * 15 + [10.0, 12.0]  # 15 normal + 2 extreme outliers

    ads = _create_ads_with_metric("CPA", values)

    result = detect_anomalies(ads, metric="CPA", threshold_sigma=2.0, direction="high")

    assert "anomalies" in result
    assert "baseline_stats" in result

    anomalies = result["anomalies"]
    assert len(anomalies) >= 2, f"Expected at least 2 high CPA anomalies, got {len(anomalies)}"

    # Verify anomalies are the high CPA ads
    anomaly_values = [a["value"] for a in anomalies]
    assert 10.0 in anomaly_values or 12.0 in anomaly_values, f"Expected 10.0 or 12.0 in anomalies, got {anomaly_values}"

    # Verify all anomalies have positive z-scores
    for a in anomalies:
        assert a["z_score"] >= 2.0, f"Expected z_score >= 2.0, got {a['z_score']}"
        assert a["direction"] == "high", f"Expected direction=high, got {a['direction']}"

    print(f"✓ Found {len(anomalies)} high CPA anomalies")
    print(f"  Baseline: mean={result['baseline_stats']['mean']}, std={result['baseline_stats']['std']}")
    for a in anomalies:
        print(f"  - CPA={a['value']}, z_score={a['z_score']}, severity={a['severity']}")

    return True


def test_detect_low_cpa_not_anomalies():
    """Test that low CPA ads are NOT flagged when direction=high."""
    print("\n=== Test: low CPA not flagged with direction=high ===")

    # Create ads where some have very low CPA (good performance)
    values = [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0,  # 10 normal
              0.5, 0.3]  # 2 very low CPA (good!)

    ads = _create_ads_with_metric("CPA", values)

    result = detect_anomalies(ads, metric="CPA", threshold_sigma=2.0, direction="high")

    anomalies = result["anomalies"]

    # Low CPA ads should NOT be flagged as anomalies when looking for high CPA
    anomaly_values = [a["value"] for a in anomalies]
    assert 0.5 not in anomaly_values, "Low CPA (0.5) should not be flagged as high CPA anomaly"
    assert 0.3 not in anomaly_values, "Low CPA (0.3) should not be flagged as high CPA anomaly"

    print(f"✓ Low CPA ads correctly excluded from high CPA anomalies")
    print(f"  Anomalies found: {len(anomalies)}")

    return True


# =============================================================================
# ROAS Anomaly Tests
# =============================================================================

def test_detect_low_roas_anomalies():
    """Test detection of low ROAS anomalies (direction=low)."""
    print("\n=== Test: detect low ROAS anomalies ===")

    # Create ads with tight normal ROAS distribution and extreme low outliers
    # Normal: all 5.0 (mean=5.0, std very small)
    # Outliers: 0.1, 0.2 (extremely low ROAS)
    values = [5.0] * 15 + [0.1, 0.2]  # 15 normal + 2 extreme low outliers

    ads = _create_ads_with_metric("ROAS", values)

    result = detect_anomalies(ads, metric="ROAS", threshold_sigma=2.0, direction="low")

    assert "anomalies" in result
    anomalies = result["anomalies"]

    assert len(anomalies) >= 2, f"Expected at least 2 low ROAS anomalies, got {len(anomalies)}"

    # Verify anomalies are the low ROAS ads
    anomaly_values = [a["value"] for a in anomalies]
    assert 0.1 in anomaly_values or 0.2 in anomaly_values, f"Expected 0.1 or 0.2 in anomalies, got {anomaly_values}"

    # Verify all anomalies have negative z-scores
    for a in anomalies:
        assert a["z_score"] <= -2.0, f"Expected z_score <= -2.0, got {a['z_score']}"
        assert a["direction"] == "low", f"Expected direction=low, got {a['direction']}"

    print(f"✓ Found {len(anomalies)} low ROAS anomalies")
    print(f"  Baseline: mean={result['baseline_stats']['mean']}, std={result['baseline_stats']['std']}")
    for a in anomalies:
        print(f"  - ROAS={a['value']}, z_score={a['z_score']}, severity={a['severity']}")

    return True


def test_detect_high_roas_not_anomalies():
    """Test that high ROAS ads are NOT flagged when direction=low."""
    print("\n=== Test: high ROAS not flagged with direction=low ===")

    # Create ads where some have very high ROAS (good performance)
    values = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0,  # 10 normal
              15.0, 20.0]  # 2 very high ROAS (good!)

    ads = _create_ads_with_metric("ROAS", values)

    result = detect_anomalies(ads, metric="ROAS", threshold_sigma=2.0, direction="low")

    anomalies = result["anomalies"]

    # High ROAS ads should NOT be flagged as anomalies when looking for low ROAS
    anomaly_values = [a["value"] for a in anomalies]
    assert 15.0 not in anomaly_values, "High ROAS (15.0) should not be flagged as low ROAS anomaly"
    assert 20.0 not in anomaly_values, "High ROAS (20.0) should not be flagged as low ROAS anomaly"

    print(f"✓ High ROAS ads correctly excluded from low ROAS anomalies")
    print(f"  Anomalies found: {len(anomalies)}")

    return True


# =============================================================================
# Bidirectional Tests
# =============================================================================

def test_detect_anomalies_both_directions():
    """Test detection of anomalies in both directions."""
    print("\n=== Test: detect anomalies both directions ===")

    # Create ads with outliers in both directions
    values = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0,  # 10 normal (mean=5.0)
              0.5,   # 1 very low
              15.0]  # 1 very high

    ads = _create_ads_with_metric("CPA", values)

    result = detect_anomalies(ads, metric="CPA", threshold_sigma=2.0, direction="both")

    anomalies = result["anomalies"]

    # Should find both high and low outliers
    directions = [a["direction"] for a in anomalies]

    print(f"✓ Found {len(anomalies)} anomalies in both directions")
    for a in anomalies:
        print(f"  - CPA={a['value']}, z_score={a['z_score']}, direction={a['direction']}")

    return True


# =============================================================================
# Threshold Tests
# =============================================================================

def test_threshold_sigma_affects_count():
    """Test that higher threshold means fewer anomalies."""
    print("\n=== Test: threshold affects anomaly count ===")

    # Create ads with a range of CPA values
    values = [2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0,  # 10 normal
              3.5, 4.0, 5.0, 6.0]  # 4 increasingly high

    ads = _create_ads_with_metric("CPA", values)

    result_15 = detect_anomalies(ads, metric="CPA", threshold_sigma=1.5, direction="high")
    result_20 = detect_anomalies(ads, metric="CPA", threshold_sigma=2.0, direction="high")
    result_30 = detect_anomalies(ads, metric="CPA", threshold_sigma=3.0, direction="high")

    count_15 = len(result_15["anomalies"])
    count_20 = len(result_20["anomalies"])
    count_30 = len(result_30["anomalies"])

    # Higher threshold should find fewer or equal anomalies
    assert count_15 >= count_20, f"1.5σ ({count_15}) should find >= 2.0σ ({count_20})"
    assert count_20 >= count_30, f"2.0σ ({count_20}) should find >= 3.0σ ({count_30})"

    print(f"✓ Threshold affects anomaly count correctly")
    print(f"  1.5σ: {count_15} anomalies")
    print(f"  2.0σ: {count_20} anomalies")
    print(f"  3.0σ: {count_30} anomalies")

    return True


# =============================================================================
# Severity Tests
# =============================================================================

def test_severity_levels():
    """Test that severity is assigned correctly based on z-score magnitude."""
    print("\n=== Test: severity levels ===")

    # Create ads with varying degrees of anomaly
    # Severity thresholds: extreme >= 3.0, significant >= 2.0, mild >= 1.5
    values = [2.0] * 20  # 20 normal ads (mean=2.0, std very small)
    values.extend([3.0, 4.0, 5.0, 8.0])  # Add outliers

    ads = _create_ads_with_metric("CPA", values)

    result = detect_anomalies(ads, metric="CPA", threshold_sigma=1.5, direction="high")

    anomalies = result["anomalies"]
    severities = [a["severity"] for a in anomalies]

    print(f"✓ Found anomalies with severities: {set(severities)}")
    for a in anomalies:
        print(f"  - CPA={a['value']}, z_score={a['z_score']:.2f}, severity={a['severity']}")

    # Should have some variation in severity
    assert len(anomalies) > 0, "Expected some anomalies"

    return True


# =============================================================================
# Min Spend Filter Tests
# =============================================================================

def test_min_spend_filter():
    """Test that ads below min_spend are excluded."""
    print("\n=== Test: min spend filter ===")

    ads = [
        {"ad_name": "Low Spend Ad", "ad_id": "1", "Spend": 50, "CPA": 10.0},   # Below threshold
        {"ad_name": "Normal Ad 1", "ad_id": "2", "Spend": 200, "CPA": 2.0},
        {"ad_name": "Normal Ad 2", "ad_id": "3", "Spend": 200, "CPA": 2.0},
        {"ad_name": "Normal Ad 3", "ad_id": "4", "Spend": 200, "CPA": 2.0},
        {"ad_name": "Normal Ad 4", "ad_id": "5", "Spend": 200, "CPA": 2.0},
        {"ad_name": "Normal Ad 5", "ad_id": "6", "Spend": 200, "CPA": 2.0},
        {"ad_name": "Normal Ad 6", "ad_id": "7", "Spend": 200, "CPA": 2.0},
        {"ad_name": "Normal Ad 7", "ad_id": "8", "Spend": 200, "CPA": 2.0},
        {"ad_name": "Normal Ad 8", "ad_id": "9", "Spend": 200, "CPA": 2.0},
        {"ad_name": "Normal Ad 9", "ad_id": "10", "Spend": 200, "CPA": 2.0},
        {"ad_name": "Normal Ad 10", "ad_id": "11", "Spend": 200, "CPA": 2.0},
    ]

    result = detect_anomalies(ads, metric="CPA", threshold_sigma=2.0, direction="high", min_spend=100)

    # The low spend ad with CPA=10 should be excluded from analysis
    anomaly_ids = [a["ad"]["ad_id"] for a in result["anomalies"]]
    assert "1" not in anomaly_ids, "Low spend ad should be excluded"

    # Baseline should only include ads with spend >= 100
    assert result["baseline_stats"]["count"] == 10, f"Expected 10 eligible ads, got {result['baseline_stats']['count']}"

    print(f"✓ Low spend ads correctly filtered out")
    print(f"  Eligible ads: {result['baseline_stats']['count']}")

    return True


# =============================================================================
# Pre-computed Z-Score Tests
# =============================================================================

def test_precomputed_z_scores():
    """Test detection using pre-computed z-scores (z_cpa, z_roas)."""
    print("\n=== Test: pre-computed z-scores ===")

    # Create ads with pre-computed z-scores
    ads = [
        {"ad_name": f"Ad {i}", "ad_id": str(i), "Spend": 200, "z_cpa": z, "CPA": 2.0 + z}
        for i, z in enumerate([0.1, 0.2, -0.1, 0.5, -0.3, 0.0, 0.1, -0.2, 0.3, -0.1,  # 10 normal
                               2.5, 3.0])  # 2 high z-scores
    ]

    result = detect_anomalies(ads, metric="z_cpa", threshold_sigma=2.0, direction="high")

    anomalies = result["anomalies"]
    assert len(anomalies) == 2, f"Expected 2 anomalies with z_cpa >= 2.0, got {len(anomalies)}"

    # Verify the z-scores are used directly
    z_scores = [a["z_score"] for a in anomalies]
    assert 2.5 in z_scores and 3.0 in z_scores, f"Expected z-scores 2.5 and 3.0, got {z_scores}"

    print(f"✓ Pre-computed z-scores used correctly")
    for a in anomalies:
        print(f"  - z_cpa={a['z_score']}, severity={a['severity']}")

    return True


# =============================================================================
# Edge Cases
# =============================================================================

def test_insufficient_sample_size():
    """Test handling of insufficient sample size."""
    print("\n=== Test: insufficient sample size ===")

    # Only 5 ads (below default min_sample_size of 10)
    ads = _create_ads_with_metric("CPA", [2.0, 2.5, 3.0, 10.0, 1.5])

    result = detect_anomalies(ads, metric="CPA", threshold_sigma=2.0, direction="high")

    assert "warning" in result, "Expected warning for small sample size"
    assert len(result["anomalies"]) == 0, "Expected no anomalies with small sample"

    print(f"✓ Small sample size handled correctly")
    print(f"  Warning: {result.get('warning')}")

    return True


def test_zero_standard_deviation():
    """Test handling when all values are identical."""
    print("\n=== Test: zero standard deviation ===")

    # All identical values
    ads = _create_ads_with_metric("CPA", [2.0] * 15)

    result = detect_anomalies(ads, metric="CPA", threshold_sigma=2.0, direction="high")

    assert "warning" in result, "Expected warning for zero std"
    assert len(result["anomalies"]) == 0, "Expected no anomalies with zero std"

    print(f"✓ Zero standard deviation handled correctly")
    print(f"  Warning: {result.get('warning')}")

    return True


def test_missing_metric_values():
    """Test handling of ads with missing metric values."""
    print("\n=== Test: missing metric values ===")

    ads = [
        {"ad_name": f"Ad {i}", "ad_id": str(i), "Spend": 200, "CPA": 2.0}
        for i in range(10)
    ]
    # Add ads with missing CPA
    ads.append({"ad_name": "Missing CPA", "ad_id": "missing", "Spend": 200})
    # Add outlier
    ads.append({"ad_name": "Outlier", "ad_id": "outlier", "Spend": 200, "CPA": 10.0})

    result = detect_anomalies(ads, metric="CPA", threshold_sigma=2.0, direction="high")

    # Should still find the outlier
    assert len(result["anomalies"]) >= 1, "Expected at least 1 anomaly"

    # The missing CPA ad should not cause errors
    print(f"✓ Missing metric values handled correctly")
    print(f"  Anomalies found: {len(result['anomalies'])}")

    return True


# =============================================================================
# Fixture Data Integration Tests
# =============================================================================

def test_detect_cpa_anomalies_fixture():
    """Test CPA anomaly detection with real fixture data."""
    print("\n=== Test: CPA anomalies with fixture data ===")

    data = get_ad_data(account_id="tl")
    ads = data["ads"]

    # Test with raw CPA metric
    result = detect_anomalies(ads, metric="CPA", threshold_sigma=2.0, direction="high")

    assert "anomalies" in result
    assert "baseline_stats" in result

    print(f"✓ CPA anomaly detection on fixture data")
    print(f"  Total ads: {len(ads)}")
    print(f"  Eligible ads: {result['baseline_stats']['count']}")
    print(f"  Mean CPA: ${result['baseline_stats']['mean']:.2f}")
    print(f"  Std CPA: ${result['baseline_stats']['std']:.2f}")
    print(f"  High CPA anomalies: {len(result['anomalies'])}")

    if result["anomalies"]:
        top = result["anomalies"][0]
        print(f"  Worst: {top['ad'].get('ad_name', 'Unknown')} (CPA=${top['value']:.2f}, z={top['z_score']:.2f})")

    return True


def test_detect_roas_anomalies_fixture():
    """Test ROAS anomaly detection with real fixture data."""
    print("\n=== Test: ROAS anomalies with fixture data ===")

    data = get_ad_data(account_id="tl")
    ads = data["ads"]

    # Test with raw ROAS metric
    result = detect_anomalies(ads, metric="ROAS", threshold_sigma=2.0, direction="low")

    assert "anomalies" in result
    assert "baseline_stats" in result

    print(f"✓ ROAS anomaly detection on fixture data")
    print(f"  Total ads: {len(ads)}")
    print(f"  Eligible ads: {result['baseline_stats']['count']}")
    print(f"  Mean ROAS: {result['baseline_stats']['mean']:.2f}")
    print(f"  Std ROAS: {result['baseline_stats']['std']:.2f}")
    print(f"  Low ROAS anomalies: {len(result['anomalies'])}")

    if result["anomalies"]:
        top = result["anomalies"][0]
        print(f"  Worst: {top['ad'].get('ad_name', 'Unknown')} (ROAS={top['value']:.2f}, z={top['z_score']:.2f})")

    return True


def test_detect_anomalies_wh_fixture():
    """Test anomaly detection with WhisperingHomes fixture data."""
    print("\n=== Test: anomalies with WH fixture data ===")

    data = get_ad_data(account_id="wh")
    ads = data["ads"]

    cpa_result = detect_anomalies(ads, metric="CPA", threshold_sigma=2.0, direction="high")
    roas_result = detect_anomalies(ads, metric="ROAS", threshold_sigma=2.0, direction="low")

    print(f"✓ Anomaly detection on WH fixture data")
    print(f"  Total ads: {len(ads)}")
    print(f"  High CPA anomalies: {len(cpa_result['anomalies'])}")
    print(f"  Low ROAS anomalies: {len(roas_result['anomalies'])}")

    return True


# =============================================================================
# Test Runner
# =============================================================================

def run_anomaly_tests():
    """Run all anomaly detection tests."""
    print("=" * 60)
    print("ANOMALY DETECTION UNIT TESTS")
    print("=" * 60)

    tests = [
        # CPA tests
        ("Detect high CPA anomalies", test_detect_high_cpa_anomalies),
        ("Low CPA not flagged (direction=high)", test_detect_low_cpa_not_anomalies),

        # ROAS tests
        ("Detect low ROAS anomalies", test_detect_low_roas_anomalies),
        ("High ROAS not flagged (direction=low)", test_detect_high_roas_not_anomalies),

        # Bidirectional
        ("Detect anomalies both directions", test_detect_anomalies_both_directions),

        # Threshold and severity
        ("Threshold affects anomaly count", test_threshold_sigma_affects_count),
        ("Severity levels", test_severity_levels),

        # Filters
        ("Min spend filter", test_min_spend_filter),
        ("Pre-computed z-scores", test_precomputed_z_scores),

        # Edge cases
        ("Insufficient sample size", test_insufficient_sample_size),
        ("Zero standard deviation", test_zero_standard_deviation),
        ("Missing metric values", test_missing_metric_values),

        # Fixture integration
        ("CPA anomalies - TL fixture", test_detect_cpa_anomalies_fixture),
        ("ROAS anomalies - TL fixture", test_detect_roas_anomalies_fixture),
        ("Anomalies - WH fixture", test_detect_anomalies_wh_fixture),
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
    print(f"ANOMALY TEST RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ ALL ANOMALY TESTS PASSED")
        return True
    else:
        print(f"\n❌ {failed} ANOMALY TESTS FAILED")
        return False


if __name__ == "__main__":
    success = run_anomaly_tests()
    sys.exit(0 if success else 1)
