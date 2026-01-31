"""
RCA (Root Cause Analysis) Unit Tests.

Tests for data-driven thresholds and factor detection.
Run with: python3 -m pytest tests/test_rca.py -v
Or standalone: python3 tests/test_rca.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from helpers.tools import run_rca, _percentile


# =============================================================================
# Helper function tests
# =============================================================================

def test_percentile_basic():
    """Test percentile calculation with simple values."""
    print("\n=== Test: _percentile basic ===")

    values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    p25 = _percentile(values, 25)
    p50 = _percentile(values, 50)
    p75 = _percentile(values, 75)

    assert 2.0 <= p25 <= 3.5, f"Expected p25 ~2.75, got {p25}"
    assert 5.0 <= p50 <= 6.0, f"Expected p50 ~5.5, got {p50}"
    assert 7.0 <= p75 <= 8.5, f"Expected p75 ~7.75, got {p75}"

    print(f"✓ p25={p25}, p50={p50}, p75={p75}")
    return True


def test_percentile_empty():
    """Test percentile with empty list."""
    print("\n=== Test: _percentile empty ===")

    result = _percentile([], 50)
    assert result == 0, f"Expected 0 for empty list, got {result}"

    print("✓ Empty list returns 0")
    return True


# =============================================================================
# RCA Factor Tests - Synthetic Data
# =============================================================================

def _create_baseline_ads(n: int = 20) -> list[dict]:
    """Create baseline ads with normal values for comparison."""
    return [
        {
            "ad_name": f"Baseline Ad {i}",
            "ad_id": f"base_{i}",
            "ad_provider": "Google Ads",
            "Spend": 500,
            "CPA": 2.0,
            "ROAS": 5.0,
            "CTR": 0.05,  # 5% CTR
            "audience_engagement_score": 50,
            "competitive_pressure": 0.3,
            "budget_utilization": 50,
            "creative_variants": 3,
            "creative_status": "active",
            "days_active": 30,
        }
        for i in range(n)
    ]


def test_rca_low_audience_engagement():
    """Test RCA triggers on low audience engagement (below 25th percentile)."""
    print("\n=== Test: RCA low audience engagement ===")

    baseline_ads = _create_baseline_ads(20)

    # Anomaly ad with very low engagement
    anomaly_ad = {
        "ad_name": "Low Engagement Ad",
        "ad_id": "anomaly_1",
        "ad_provider": "Google Ads",
        "Spend": 500,
        "CPA": 5.0,
        "audience_engagement_score": 5,  # Very low vs baseline of 50
        "competitive_pressure": 0.3,
        "budget_utilization": 50,
        "creative_variants": 3,
        "creative_status": "active",
        "days_active": 30,
        "CTR": 0.05,
    }

    all_ads = baseline_ads + [anomaly_ad]
    result = run_rca(anomaly_ad, all_ads, "CPA")

    factors = [rc["factor"] for rc in result["root_causes"]]
    assert "audience_engagement" in factors, f"Expected 'audience_engagement' in factors, got: {factors}"

    engagement_rc = next(rc for rc in result["root_causes"] if rc["factor"] == "audience_engagement")
    assert engagement_rc["impact"] == "high", f"Expected high impact, got: {engagement_rc['impact']}"

    print(f"✓ Found audience_engagement factor with HIGH impact")
    print(f"  Finding: {engagement_rc['finding']}")
    return True


def test_rca_high_competitive_pressure():
    """Test RCA triggers on high competitive pressure (above 75th percentile)."""
    print("\n=== Test: RCA high competitive pressure ===")

    baseline_ads = _create_baseline_ads(20)

    # Anomaly ad with high competitive pressure
    anomaly_ad = {
        "ad_name": "High Pressure Ad",
        "ad_id": "anomaly_2",
        "ad_provider": "Google Ads",
        "Spend": 500,
        "CPA": 5.0,
        "audience_engagement_score": 50,
        "competitive_pressure": 0.9,  # Very high vs baseline of 0.3
        "budget_utilization": 50,
        "creative_variants": 3,
        "creative_status": "active",
        "days_active": 30,
        "CTR": 0.05,
    }

    all_ads = baseline_ads + [anomaly_ad]
    result = run_rca(anomaly_ad, all_ads, "CPA")

    factors = [rc["factor"] for rc in result["root_causes"]]
    assert "competitive_pressure" in factors, f"Expected 'competitive_pressure' in factors, got: {factors}"

    pressure_rc = next(rc for rc in result["root_causes"] if rc["factor"] == "competitive_pressure")
    assert pressure_rc["impact"] == "medium", f"Expected medium impact, got: {pressure_rc['impact']}"

    print(f"✓ Found competitive_pressure factor with MEDIUM impact")
    print(f"  Finding: {pressure_rc['finding']}")
    return True


def test_rca_low_ctr():
    """Test RCA triggers on low CTR (below 25th percentile)."""
    print("\n=== Test: RCA low CTR ===")

    baseline_ads = _create_baseline_ads(20)

    # Anomaly ad with very low CTR
    anomaly_ad = {
        "ad_name": "Low CTR Ad",
        "ad_id": "anomaly_3",
        "ad_provider": "Google Ads",
        "Spend": 500,
        "CPA": 5.0,
        "audience_engagement_score": 50,
        "competitive_pressure": 0.3,
        "budget_utilization": 50,
        "creative_variants": 3,
        "creative_status": "active",
        "days_active": 30,
        "CTR": 0.001,  # Very low vs baseline of 0.05 (5%)
    }

    all_ads = baseline_ads + [anomaly_ad]
    result = run_rca(anomaly_ad, all_ads, "CPA")

    factors = [rc["factor"] for rc in result["root_causes"]]
    assert "low_ctr" in factors, f"Expected 'low_ctr' in factors, got: {factors}"

    ctr_rc = next(rc for rc in result["root_causes"] if rc["factor"] == "low_ctr")
    assert ctr_rc["impact"] == "high", f"Expected high impact, got: {ctr_rc['impact']}"

    print(f"✓ Found low_ctr factor with HIGH impact")
    print(f"  Finding: {ctr_rc['finding']}")
    return True


def test_rca_high_budget_utilization():
    """Test RCA triggers on high budget utilization (above 75th percentile)."""
    print("\n=== Test: RCA high budget utilization ===")

    baseline_ads = _create_baseline_ads(20)

    # Anomaly ad with high budget utilization
    anomaly_ad = {
        "ad_name": "High Budget Ad",
        "ad_id": "anomaly_4",
        "ad_provider": "Google Ads",
        "Spend": 500,
        "CPA": 5.0,
        "audience_engagement_score": 50,
        "competitive_pressure": 0.3,
        "budget_utilization": 150,  # Very high vs baseline of 50
        "creative_variants": 3,
        "creative_status": "active",
        "days_active": 30,
        "CTR": 0.05,
    }

    all_ads = baseline_ads + [anomaly_ad]
    result = run_rca(anomaly_ad, all_ads, "CPA")

    factors = [rc["factor"] for rc in result["root_causes"]]
    assert "budget_overutilization" in factors, f"Expected 'budget_overutilization' in factors, got: {factors}"

    budget_rc = next(rc for rc in result["root_causes"] if rc["factor"] == "budget_overutilization")
    assert budget_rc["impact"] == "medium", f"Expected medium impact, got: {budget_rc['impact']}"

    print(f"✓ Found budget_overutilization factor with MEDIUM impact")
    print(f"  Finding: {budget_rc['finding']}")
    return True


def test_rca_single_creative_variant():
    """Test RCA triggers on single creative variant."""
    print("\n=== Test: RCA single creative variant ===")

    baseline_ads = _create_baseline_ads(20)

    # Anomaly ad with single creative
    anomaly_ad = {
        "ad_name": "Single Creative Ad",
        "ad_id": "anomaly_5",
        "ad_provider": "Google Ads",
        "Spend": 500,
        "CPA": 5.0,
        "audience_engagement_score": 50,
        "competitive_pressure": 0.3,
        "budget_utilization": 50,
        "creative_variants": 1,  # Single variant
        "creative_status": "active",
        "days_active": 30,
        "CTR": 0.05,
    }

    all_ads = baseline_ads + [anomaly_ad]
    result = run_rca(anomaly_ad, all_ads, "CPA")

    factors = [rc["factor"] for rc in result["root_causes"]]
    assert "creative_variants" in factors, f"Expected 'creative_variants' in factors, got: {factors}"

    creative_rc = next(rc for rc in result["root_causes"] if rc["factor"] == "creative_variants")
    assert creative_rc["impact"] == "medium", f"Expected medium impact, got: {creative_rc['impact']}"

    print(f"✓ Found creative_variants factor with MEDIUM impact")
    print(f"  Finding: {creative_rc['finding']}")
    return True


def test_rca_creative_fatigue():
    """Test RCA triggers on fatigued creative."""
    print("\n=== Test: RCA creative fatigue ===")

    baseline_ads = _create_baseline_ads(20)

    # Anomaly ad with fatigued creative
    anomaly_ad = {
        "ad_name": "Fatigued Ad",
        "ad_id": "anomaly_6",
        "ad_provider": "Google Ads",
        "Spend": 500,
        "CPA": 5.0,
        "audience_engagement_score": 50,
        "competitive_pressure": 0.3,
        "budget_utilization": 50,
        "creative_variants": 3,
        "creative_status": "fatigued",  # Fatigued status
        "recency": 90,
        "days_active": 90,
        "CTR": 0.05,
    }

    all_ads = baseline_ads + [anomaly_ad]
    result = run_rca(anomaly_ad, all_ads, "CPA")

    factors = [rc["factor"] for rc in result["root_causes"]]
    assert "creative_fatigue" in factors, f"Expected 'creative_fatigue' in factors, got: {factors}"

    fatigue_rc = next(rc for rc in result["root_causes"] if rc["factor"] == "creative_fatigue")
    assert fatigue_rc["impact"] == "high", f"Expected high impact, got: {fatigue_rc['impact']}"

    print(f"✓ Found creative_fatigue factor with HIGH impact")
    print(f"  Finding: {fatigue_rc['finding']}")
    return True


def test_rca_learning_phase():
    """Test RCA triggers on learning phase (< 7 days active)."""
    print("\n=== Test: RCA learning phase ===")

    baseline_ads = _create_baseline_ads(20)

    # Anomaly ad in learning phase
    anomaly_ad = {
        "ad_name": "New Ad",
        "ad_id": "anomaly_7",
        "ad_provider": "Google Ads",
        "Spend": 500,
        "CPA": 5.0,
        "audience_engagement_score": 50,
        "competitive_pressure": 0.3,
        "budget_utilization": 50,
        "creative_variants": 3,
        "creative_status": "active",
        "days_active": 3,  # Only 3 days active
        "CTR": 0.05,
    }

    all_ads = baseline_ads + [anomaly_ad]
    result = run_rca(anomaly_ad, all_ads, "CPA")

    factors = [rc["factor"] for rc in result["root_causes"]]
    assert "learning_phase" in factors, f"Expected 'learning_phase' in factors, got: {factors}"

    learning_rc = next(rc for rc in result["root_causes"] if rc["factor"] == "learning_phase")
    assert learning_rc["impact"] == "low", f"Expected low impact, got: {learning_rc['impact']}"

    print(f"✓ Found learning_phase factor with LOW impact")
    print(f"  Finding: {learning_rc['finding']}")
    return True


def test_rca_no_false_positives():
    """Test RCA does not trigger on normal ads."""
    print("\n=== Test: RCA no false positives ===")

    baseline_ads = _create_baseline_ads(20)

    # Normal ad with all good values
    normal_ad = {
        "ad_name": "Normal Ad",
        "ad_id": "normal_1",
        "ad_provider": "Google Ads",
        "Spend": 500,
        "CPA": 2.0,
        "audience_engagement_score": 50,  # Same as baseline
        "competitive_pressure": 0.3,  # Same as baseline
        "budget_utilization": 50,  # Same as baseline
        "creative_variants": 3,  # Multiple variants
        "creative_status": "active",  # Not fatigued
        "days_active": 30,  # Past learning phase
        "CTR": 0.05,  # Same as baseline
    }

    all_ads = baseline_ads + [normal_ad]
    result = run_rca(normal_ad, all_ads, "CPA")

    # Should have no root causes (or only informational ones)
    high_medium_factors = [rc for rc in result["root_causes"] if rc["impact"] in ["high", "medium"]]

    assert len(high_medium_factors) == 0, f"Expected no high/medium factors, got: {[rc['factor'] for rc in high_medium_factors]}"

    print(f"✓ No false positives for normal ad")
    print(f"  Total factors found: {len(result['root_causes'])} (all low impact)")
    return True


def test_rca_multiple_factors():
    """Test RCA identifies multiple factors correctly."""
    print("\n=== Test: RCA multiple factors ===")

    baseline_ads = _create_baseline_ads(20)

    # Anomaly ad with multiple issues
    anomaly_ad = {
        "ad_name": "Multi-Problem Ad",
        "ad_id": "anomaly_multi",
        "ad_provider": "Google Ads",
        "Spend": 500,
        "CPA": 10.0,
        "audience_engagement_score": 5,  # Low engagement
        "competitive_pressure": 0.9,  # High pressure
        "budget_utilization": 150,  # High budget
        "creative_variants": 1,  # Single variant
        "creative_status": "active",
        "days_active": 3,  # Learning phase
        "CTR": 0.001,  # Low CTR
    }

    all_ads = baseline_ads + [anomaly_ad]
    result = run_rca(anomaly_ad, all_ads, "CPA")

    factors = [rc["factor"] for rc in result["root_causes"]]

    # Should find multiple factors
    expected_factors = ["audience_engagement", "competitive_pressure", "low_ctr",
                        "budget_overutilization", "creative_variants", "learning_phase"]

    for expected in expected_factors:
        assert expected in factors, f"Expected '{expected}' in factors, got: {factors}"

    # Check impact summary
    assert result["impact_summary"]["high_impact_factors"] >= 2, "Expected at least 2 high impact factors"
    assert result["impact_summary"]["medium_impact_factors"] >= 2, "Expected at least 2 medium impact factors"

    print(f"✓ Found {len(factors)} factors: {factors}")
    print(f"  High impact: {result['impact_summary']['high_impact_factors']}")
    print(f"  Medium impact: {result['impact_summary']['medium_impact_factors']}")
    return True


def test_rca_recommendations_from_high_medium():
    """Test recommendations are generated from high/medium impact factors."""
    print("\n=== Test: RCA recommendations from high/medium ===")

    baseline_ads = _create_baseline_ads(20)

    # Anomaly ad with high impact issue
    anomaly_ad = {
        "ad_name": "Recommendation Test Ad",
        "ad_id": "anomaly_rec",
        "ad_provider": "Google Ads",
        "Spend": 500,
        "CPA": 5.0,
        "audience_engagement_score": 5,  # Low - HIGH impact
        "competitive_pressure": 0.3,
        "budget_utilization": 50,
        "creative_variants": 3,
        "creative_status": "active",
        "days_active": 30,
        "CTR": 0.05,
    }

    all_ads = baseline_ads + [anomaly_ad]
    result = run_rca(anomaly_ad, all_ads, "CPA")

    recommendations = result["recommended_actions"]

    # Should have specific recommendations (not generic fallback)
    assert len(recommendations) > 0, "Expected recommendations"
    assert "Manual review recommended" not in recommendations[0], \
        f"Expected specific recommendation, got generic: {recommendations}"

    print(f"✓ Generated {len(recommendations)} specific recommendations")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    return True


# =============================================================================
# Test with Real Fixture Data
# =============================================================================

def test_rca_with_fixture_data():
    """Test RCA with actual fixture data."""
    print("\n=== Test: RCA with fixture data ===")

    from helpers.tools import get_ad_data, detect_anomalies

    data = get_ad_data(account_id="tl")
    ads = data["ads"]

    # Find high CPA anomalies
    anomaly_result = detect_anomalies(ads, metric="CPA", threshold_sigma=2.0, direction="high")
    anomalies = anomaly_result.get("anomalies", [])

    if not anomalies:
        print("⚠ No anomalies found in fixture data")
        return True

    # Run RCA on first anomaly
    anomaly_ad = anomalies[0]["ad"]
    result = run_rca(anomaly_ad, ads, "CPA")

    # Should find some factors
    assert len(result["root_causes"]) > 0, "Expected at least one root cause"

    # Should have recommendations
    assert len(result["recommended_actions"]) > 0, "Expected recommendations"

    print(f"✓ Analyzed anomaly: {result['anomaly_summary']['ad_name']}")
    print(f"✓ Found {len(result['root_causes'])} root causes")

    for rc in result["root_causes"]:
        impact_icon = "🔴" if rc["impact"] == "high" else "🟡" if rc["impact"] == "medium" else "🟢"
        print(f"  {impact_icon} [{rc['impact'].upper()}] {rc['factor']}")

    return True


# =============================================================================
# Test Runner
# =============================================================================

def run_rca_tests():
    """Run all RCA tests."""
    print("=" * 60)
    print("RCA UNIT TESTS")
    print("=" * 60)

    tests = [
        ("Percentile basic", test_percentile_basic),
        ("Percentile empty", test_percentile_empty),
        ("Low audience engagement", test_rca_low_audience_engagement),
        ("High competitive pressure", test_rca_high_competitive_pressure),
        ("Low CTR", test_rca_low_ctr),
        ("High budget utilization", test_rca_high_budget_utilization),
        ("Single creative variant", test_rca_single_creative_variant),
        ("Creative fatigue", test_rca_creative_fatigue),
        ("Learning phase", test_rca_learning_phase),
        ("No false positives", test_rca_no_false_positives),
        ("Multiple factors", test_rca_multiple_factors),
        ("Recommendations from high/medium", test_rca_recommendations_from_high_medium),
        ("RCA with fixture data", test_rca_with_fixture_data),
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
    print(f"RCA TEST RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ ALL RCA TESTS PASSED")
        return True
    else:
        print(f"\n❌ {failed} RCA TESTS FAILED")
        return False


if __name__ == "__main__":
    success = run_rca_tests()
    sys.exit(0 if success else 1)
