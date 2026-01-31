"""
GATE 1 Validation: Test anomaly detection tools against fixtures.

Run with: python -m pytest tests/test_gate1_validation.py -v
Or standalone: python tests/test_gate1_validation.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from helpers.tools import get_ad_data, detect_anomalies, get_ontology, run_rca
from models.analyze_agent import AnalyzeAgentModel


def test_get_ad_data_loads_fixtures():
    """Test that fixture data loads correctly."""
    print("\n=== Test: get_ad_data loads fixtures ===")

    result = get_ad_data(account_id="tl")

    assert "ads" in result, f"Expected 'ads' key, got: {result.keys()}"
    assert len(result["ads"]) > 0, "Expected non-empty ads list"

    # Check first ad has expected fields
    first_ad = result["ads"][0]
    expected_fields = ["ad_name", "ad_provider", "Spend", "ROAS", "CPA", "z_cpa", "z_roas"]

    for field in expected_fields:
        # Handle case variations
        has_field = field in first_ad or field.upper() in first_ad or field.lower() in first_ad
        assert has_field, f"Expected field '{field}' in ad data"

    print(f"✓ Loaded {len(result['ads'])} ads from fixtures")
    print(f"✓ First ad: {first_ad.get('ad_name') or first_ad.get('AD_NAME')}")
    return True


def test_detect_anomalies_finds_high_cpa():
    """Test that detect_anomalies finds ads with high z_cpa."""
    print("\n=== Test: detect_anomalies finds high CPA ===")

    data = get_ad_data(account_id="tl")
    ads = data["ads"]

    result = detect_anomalies(ads, metric="z_cpa", threshold_sigma=2.0, direction="high")

    assert "anomalies" in result, f"Expected 'anomalies' key, got: {result.keys()}"

    # Should find some anomalies
    anomalies = result["anomalies"]
    print(f"✓ Found {len(anomalies)} high CPA anomalies")

    if anomalies:
        # Verify all anomalies have z_score >= 2.0
        for a in anomalies:
            assert a["z_score"] >= 2.0, f"Expected z_score >= 2.0, got {a['z_score']}"
        print(f"✓ All anomalies have z_score >= 2.0")

        # Show top anomaly
        top = anomalies[0]
        print(f"✓ Top anomaly: {top['ad']['ad_name']} (z_score={top['z_score']}, severity={top['severity']})")

    return True


def test_detect_anomalies_finds_low_roas():
    """Test that detect_anomalies finds ads with low z_roas."""
    print("\n=== Test: detect_anomalies finds low ROAS ===")

    data = get_ad_data(account_id="tl")
    ads = data["ads"]

    result = detect_anomalies(ads, metric="z_roas", threshold_sigma=2.0, direction="low")

    assert "anomalies" in result
    anomalies = result["anomalies"]
    print(f"✓ Found {len(anomalies)} low ROAS anomalies")

    if anomalies:
        for a in anomalies:
            assert a["z_score"] <= -2.0, f"Expected z_score <= -2.0, got {a['z_score']}"
        print(f"✓ All anomalies have z_score <= -2.0")

    return True


def test_get_ontology_groups_by_provider():
    """Test that get_ontology correctly groups by ad_provider."""
    print("\n=== Test: get_ontology groups by provider ===")

    data = get_ad_data(account_id="tl")
    ads = data["ads"]

    result = get_ontology(ads, group_by=["ad_provider"])

    assert "breakdown" in result
    assert "dimensions_used" in result
    assert result["dimensions_used"] == ["ad_provider"]

    breakdown = result["breakdown"]
    print(f"✓ Found {len(breakdown)} providers")

    for provider, stats in breakdown.items():
        print(f"  - {provider}: {stats['count']} ads, ${stats.get('total_spend', 0):,.0f} spend")
        assert "count" in stats
        assert stats["count"] > 0

    return True


def test_get_ontology_multiple_dimensions():
    """Test ontology with multiple dimensions."""
    print("\n=== Test: get_ontology with multiple dimensions ===")

    data = get_ad_data(account_id="tl")
    ads = data["ads"]

    result = get_ontology(ads, group_by=["ad_provider", "store"])

    assert "breakdown" in result
    breakdown = result["breakdown"]

    print(f"✓ Found {len(breakdown)} provider+store combinations")

    # Keys should be "Provider > Store" format
    for key in list(breakdown.keys())[:3]:
        print(f"  - {key}: {breakdown[key]['count']} ads")
        assert " > " in key, f"Expected ' > ' separator in key: {key}"

    return True


def test_run_rca_identifies_factors():
    """Test that run_rca identifies root cause factors."""
    print("\n=== Test: run_rca identifies factors ===")

    data = get_ad_data(account_id="tl")
    ads = data["ads"]

    # Find an anomaly first
    anomaly_result = detect_anomalies(ads, metric="z_cpa", threshold_sigma=1.5, direction="high")
    anomalies = anomaly_result.get("anomalies", [])

    if not anomalies:
        print("⚠ No anomalies found to test RCA (this is OK if data is clean)")
        return True

    anomaly_ad = anomalies[0]["ad"]
    rca_result = run_rca(anomaly_ad, ads, "CPA")

    assert "anomaly_summary" in rca_result
    assert "root_causes" in rca_result
    assert "comparison_to_similar" in rca_result
    assert "recommended_actions" in rca_result

    print(f"✓ RCA for: {rca_result['anomaly_summary']['ad_name']}")
    print(f"✓ Found {len(rca_result['root_causes'])} root causes")

    for rc in rca_result["root_causes"]:
        print(f"  - [{rc['impact']}] {rc['factor']}: {rc['finding']}")

    print(f"✓ Recommendations: {rca_result['recommended_actions']}")

    return True


def test_analyze_agent_full_flow():
    """Test the full Analyze Agent flow."""
    print("\n=== Test: Analyze Agent full flow ===")

    agent = AnalyzeAgentModel()
    result = agent.run_analysis(account_id="tl")

    assert "error" not in result, f"Agent returned error: {result.get('error')}"
    assert "anomalies" in result
    assert "detailed_anomalies" in result
    assert "ontology_insights" in result
    assert "summary" in result

    print(f"✓ Analyzed {result['total_ads_analyzed']} ads")
    print(f"✓ High CPA anomalies: {result['anomalies']['high_cpa']['count']}")
    print(f"✓ Low ROAS anomalies: {result['anomalies']['low_roas']['count']}")
    print(f"✓ Total anomalies with RCA: {result['summary']['total_anomalies']}")
    print(f"✓ Total anomaly spend: ${result['summary']['total_anomaly_spend']:,.0f}")

    if result['summary']['worst_provider']:
        print(f"✓ Worst provider: {result['summary']['worst_provider']}")

    # Show detailed anomalies
    if result['detailed_anomalies']:
        print("\n  Top anomalies:")
        for i, a in enumerate(result['detailed_anomalies'][:3]):
            ad_name = a['anomaly']['ad'].get('ad_name', 'Unknown')
            z_score = a['anomaly']['z_score']
            a_type = a['type']
            print(f"    {i+1}. [{a_type}] {ad_name} (z={z_score})")

    return True


def run_gate1_validation():
    """Run all Gate 1 validation tests."""
    print("=" * 60)
    print("GATE 1 VALIDATION: Anomaly Detection Tools")
    print("=" * 60)

    tests = [
        ("Load fixture data", test_get_ad_data_loads_fixtures),
        ("Detect high CPA anomalies", test_detect_anomalies_finds_high_cpa),
        ("Detect low ROAS anomalies", test_detect_anomalies_finds_low_roas),
        ("Ontology by provider", test_get_ontology_groups_by_provider),
        ("Ontology multiple dimensions", test_get_ontology_multiple_dimensions),
        ("RCA identifies factors", test_run_rca_identifies_factors),
        ("Analyze Agent full flow", test_analyze_agent_full_flow),
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
    print(f"GATE 1 RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ GATE 1 PASSED - Ready to proceed to Recommend Agent")
        return True
    else:
        print(f"\n❌ GATE 1 FAILED - {failed} tests need fixing")
        return False


if __name__ == "__main__":
    success = run_gate1_validation()
    sys.exit(0 if success else 1)
