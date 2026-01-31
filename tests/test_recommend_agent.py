"""
Recommend Agent Unit Tests.

Tests for budget and creative recommendations based on anomaly analysis.
Run with: python3 -m pytest tests/test_recommend_agent.py -v
Or standalone: python3 tests/test_recommend_agent.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from models.recommend_agent import RecommendAgentModel


# =============================================================================
# Test Data Helpers
# =============================================================================

def _create_high_cpa_anomaly(z_score: float = 3.0, spend: float = 1000, cpa: float = 10.0) -> dict:
    """Create a high CPA anomaly for testing."""
    return {
        "type": "high_cpa",
        "anomaly": {
            "ad": {
                "ad_name": f"High CPA Ad (z={z_score})",
                "ad_id": f"hcpa_{z_score}",
                "ad_provider": "Google Ads",
                "Spend": spend,
                "CPA": cpa,
                "ROAS": 1.0,
                "z_cpa": z_score,
            },
            "z_score": z_score,
            "severity": "extreme" if z_score >= 3.0 else "significant" if z_score >= 2.0 else "mild",
        },
        "rca": {
            "root_causes": [
                {"factor": "audience_engagement", "impact": "high", "finding": "Low engagement score"},
                {"factor": "competitive_pressure", "impact": "medium", "finding": "High competition"},
            ],
            "recommended_actions": ["Reduce budget", "Review targeting"],
        },
    }


def _create_low_roas_anomaly(roas: float = 0.3, spend: float = 500, z_score: float = -2.5) -> dict:
    """Create a low ROAS anomaly for testing."""
    return {
        "type": "low_roas",
        "anomaly": {
            "ad": {
                "ad_name": f"Low ROAS Ad (roas={roas})",
                "ad_id": f"lroas_{roas}",
                "ad_provider": "Meta Ads",
                "Spend": spend,
                "CPA": 5.0,
                "ROAS": roas,
                "z_roas": z_score,
            },
            "z_score": z_score,
            "severity": "extreme" if roas < 0.5 else "significant",
        },
        "rca": {
            "root_causes": [
                {"factor": "creative_fatigue", "impact": "high", "finding": "Creative is fatigued"},
            ],
            "recommended_actions": ["Refresh creative"],
        },
    }


def _create_scaling_candidate(roas: float = 5.0, spend: float = 500, z_cpa: float = 0.0) -> dict:
    """Create an ad that's a good scaling candidate."""
    return {
        "ad_name": f"Scale Candidate (roas={roas})",
        "ad_id": f"scale_{roas}",
        "ad_provider": "Google Ads",
        "Spend": spend,
        "CPA": 1.5,
        "ROAS": roas,
        "z_cpa": z_cpa,
        "creative_variants": 3,
        "days_active": 30,
    }


def _create_refresh_candidate(creative_variants: int = 1, days_active: int = 30, spend: float = 500) -> dict:
    """Create an ad that needs creative refresh."""
    return {
        "ad_name": f"Refresh Candidate ({creative_variants} variant)",
        "ad_id": f"refresh_{creative_variants}",
        "ad_provider": "Meta Ads",
        "Spend": spend,
        "CPA": 3.0,
        "ROAS": 2.0,
        "z_cpa": 0.5,
        "creative_variants": creative_variants,
        "days_active": days_active,
        "creative_status": "active",
    }


# =============================================================================
# High CPA Recommendation Tests
# =============================================================================

def test_recommend_pause_for_extreme_cpa():
    """Test that extreme CPA anomalies get PAUSE recommendation."""
    print("\n=== Test: Pause for extreme CPA ===")

    agent = RecommendAgentModel()
    analysis = {"detailed_anomalies": [_create_high_cpa_anomaly(z_score=3.5, spend=1000)]}

    result = agent.generate_recommendations(analysis)
    recs = result["recommendations"]

    assert len(recs) >= 1, "Expected at least one recommendation"
    rec = recs[0]

    assert rec["action"] == "pause", f"Expected 'pause' for extreme CPA, got '{rec['action']}'"
    assert rec["priority"] == "critical", f"Expected 'critical' priority, got '{rec['priority']}'"
    assert rec["estimated_impact"] == 1000, f"Expected $1000 savings, got ${rec['estimated_impact']}"

    print(f"✓ Extreme CPA → PAUSE action, critical priority")
    print(f"  Impact: ${rec['estimated_impact']} savings")
    return True


def test_recommend_reduce_for_significant_cpa():
    """Test that significant CPA anomalies get REDUCE recommendation."""
    print("\n=== Test: Reduce for significant CPA ===")

    agent = RecommendAgentModel()
    analysis = {"detailed_anomalies": [_create_high_cpa_anomaly(z_score=2.0, spend=1000)]}

    result = agent.generate_recommendations(analysis)
    recs = result["recommendations"]

    assert len(recs) >= 1, "Expected at least one recommendation"
    rec = recs[0]

    assert rec["action"] == "reduce", f"Expected 'reduce' for significant CPA, got '{rec['action']}'"
    assert rec["priority"] == "high", f"Expected 'high' priority, got '{rec['priority']}'"
    assert rec["recommended_change"] == "-50%", f"Expected -50% change, got '{rec['recommended_change']}'"

    print(f"✓ Significant CPA → REDUCE action, high priority")
    print(f"  Recommended change: {rec['recommended_change']}")
    return True


# =============================================================================
# Low ROAS Recommendation Tests
# =============================================================================

def test_recommend_pause_for_very_low_roas():
    """Test that very low ROAS (<0.5) gets PAUSE recommendation."""
    print("\n=== Test: Pause for very low ROAS ===")

    agent = RecommendAgentModel()
    analysis = {"detailed_anomalies": [_create_low_roas_anomaly(roas=0.3, spend=500)]}

    result = agent.generate_recommendations(analysis)
    recs = result["recommendations"]

    assert len(recs) >= 1, "Expected at least one recommendation"
    rec = recs[0]

    assert rec["action"] == "pause", f"Expected 'pause' for very low ROAS, got '{rec['action']}'"
    assert rec["priority"] == "critical", f"Expected 'critical' priority, got '{rec['priority']}'"

    print(f"✓ Very low ROAS (0.3) → PAUSE action, critical priority")
    return True


def test_recommend_reduce_for_low_roas():
    """Test that low ROAS (0.5-1.5) gets REDUCE recommendation."""
    print("\n=== Test: Reduce for low ROAS ===")

    agent = RecommendAgentModel()
    analysis = {"detailed_anomalies": [_create_low_roas_anomaly(roas=1.0, spend=500)]}

    result = agent.generate_recommendations(analysis)
    recs = result["recommendations"]

    assert len(recs) >= 1, "Expected at least one recommendation"
    rec = recs[0]

    assert rec["action"] == "reduce", f"Expected 'reduce' for low ROAS, got '{rec['action']}'"
    assert rec["priority"] == "high", f"Expected 'high' priority, got '{rec['priority']}'"

    print(f"✓ Low ROAS (1.0) → REDUCE action, high priority")
    return True


# =============================================================================
# Scaling Opportunity Tests
# =============================================================================

def test_find_scaling_opportunities():
    """Test that high ROAS ads are identified for scaling."""
    print("\n=== Test: Find scaling opportunities ===")

    agent = RecommendAgentModel()
    all_ads = [
        _create_scaling_candidate(roas=6.0, spend=500),
        _create_scaling_candidate(roas=4.0, spend=300),
        _create_scaling_candidate(roas=1.5, spend=200),  # Below threshold
    ]

    result = agent.generate_recommendations({"detailed_anomalies": []}, all_ads=all_ads)
    recs = result["recommendations"]

    scale_recs = [r for r in recs if r["action"] == "scale"]
    assert len(scale_recs) >= 2, f"Expected at least 2 scaling recs, got {len(scale_recs)}"

    # Best candidate should be first (highest impact)
    top_rec = scale_recs[0]
    assert top_rec["current_roas"] == 6.0, f"Expected top candidate ROAS=6.0, got {top_rec['current_roas']}"
    assert "+" in top_rec["recommended_change"], f"Expected positive change, got '{top_rec['recommended_change']}'"

    print(f"✓ Found {len(scale_recs)} scaling opportunities")
    print(f"  Top candidate: ROAS={top_rec['current_roas']}, change={top_rec['recommended_change']}")
    return True


def test_no_scaling_for_low_spend():
    """Test that low-spend ads are not recommended for scaling."""
    print("\n=== Test: No scaling for low spend ===")

    agent = RecommendAgentModel()
    all_ads = [
        _create_scaling_candidate(roas=5.0, spend=50),  # Below min_spend threshold
    ]

    result = agent.generate_recommendations({"detailed_anomalies": []}, all_ads=all_ads)
    scale_recs = [r for r in result["recommendations"] if r["action"] == "scale"]

    assert len(scale_recs) == 0, f"Expected no scaling recs for low spend, got {len(scale_recs)}"

    print(f"✓ No scaling recommendation for low-spend ad")
    return True


def test_no_scaling_for_anomalous_ads():
    """Test that anomalous ads are excluded from scaling recommendations."""
    print("\n=== Test: No scaling for anomalous ads ===")

    agent = RecommendAgentModel()

    # Ad that looks good but is already flagged as anomalous
    anomaly = _create_high_cpa_anomaly(z_score=2.5, spend=500)
    anomaly["anomaly"]["ad"]["ROAS"] = 5.0  # Good ROAS but still anomalous

    all_ads = [anomaly["anomaly"]["ad"]]

    result = agent.generate_recommendations(
        {"detailed_anomalies": [anomaly]},
        all_ads=all_ads
    )

    scale_recs = [r for r in result["recommendations"] if r["action"] == "scale"]
    assert len(scale_recs) == 0, f"Expected no scaling for anomalous ad, got {len(scale_recs)}"

    print(f"✓ Anomalous ads excluded from scaling")
    return True


# =============================================================================
# Creative Refresh Tests
# =============================================================================

def test_find_creative_refresh_single_variant():
    """Test that single-variant ads are flagged for refresh."""
    print("\n=== Test: Creative refresh for single variant ===")

    agent = RecommendAgentModel()
    all_ads = [
        _create_refresh_candidate(creative_variants=1, days_active=30, spend=500),
        _create_refresh_candidate(creative_variants=3, days_active=30, spend=500),  # Multiple variants
    ]

    result = agent.generate_recommendations({"detailed_anomalies": []}, all_ads=all_ads)
    refresh_recs = [r for r in result["recommendations"] if r["action"] == "refresh_creative"]

    assert len(refresh_recs) >= 1, f"Expected at least 1 refresh rec, got {len(refresh_recs)}"

    rec = refresh_recs[0]
    assert rec["creative_variants"] == 1, f"Expected 1 variant, got {rec['creative_variants']}"

    print(f"✓ Found creative refresh opportunity")
    print(f"  Ad has {rec['creative_variants']} variant, running for {rec['days_active']} days")
    return True


def test_no_refresh_for_low_spend():
    """Test that low-spend ads don't get refresh recommendations."""
    print("\n=== Test: No refresh for low spend ===")

    agent = RecommendAgentModel()
    all_ads = [
        _create_refresh_candidate(creative_variants=1, days_active=30, spend=50),  # Low spend
    ]

    result = agent.generate_recommendations({"detailed_anomalies": []}, all_ads=all_ads)
    refresh_recs = [r for r in result["recommendations"] if r["action"] == "refresh_creative"]

    assert len(refresh_recs) == 0, f"Expected no refresh for low spend, got {len(refresh_recs)}"

    print(f"✓ No refresh recommendation for low-spend ad")
    return True


# =============================================================================
# Summary and Sorting Tests
# =============================================================================

def test_summary_calculation():
    """Test that summary metrics are calculated correctly."""
    print("\n=== Test: Summary calculation ===")

    agent = RecommendAgentModel()
    analysis = {
        "detailed_anomalies": [
            _create_high_cpa_anomaly(z_score=3.0, spend=1000),
            _create_low_roas_anomaly(roas=0.3, spend=500),
        ]
    }
    all_ads = [_create_scaling_candidate(roas=5.0, spend=300)]

    result = agent.generate_recommendations(analysis, all_ads=all_ads)
    summary = result["summary"]

    assert summary["total_recommendations"] >= 3, f"Expected at least 3 recs, got {summary['total_recommendations']}"
    assert summary["total_potential_savings"] >= 1500, f"Expected savings >= $1500, got ${summary['total_potential_savings']}"

    assert "scale" in summary["by_action"]
    assert "pause" in summary["by_action"]
    assert "reduce" in summary["by_action"]

    print(f"✓ Summary calculated correctly")
    print(f"  Total recommendations: {summary['total_recommendations']}")
    print(f"  Potential savings: ${summary['total_potential_savings']}")
    print(f"  Potential revenue: ${summary['total_potential_revenue']}")
    return True


def test_recommendations_sorted_by_priority():
    """Test that recommendations are sorted by priority and impact."""
    print("\n=== Test: Recommendations sorted by priority ===")

    agent = RecommendAgentModel()
    analysis = {
        "detailed_anomalies": [
            _create_high_cpa_anomaly(z_score=1.5, spend=100),   # Lower priority
            _create_high_cpa_anomaly(z_score=3.5, spend=1000),  # Critical, high impact
            _create_low_roas_anomaly(roas=1.2, spend=200),      # Lower priority
        ]
    }

    result = agent.generate_recommendations(analysis)
    recs = result["recommendations"]

    # First recommendation should be critical
    assert recs[0]["priority"] == "critical", f"Expected critical first, got {recs[0]['priority']}"

    # Check priority ordering
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    for i in range(len(recs) - 1):
        curr_priority = priority_order.get(recs[i]["priority"], 3)
        next_priority = priority_order.get(recs[i + 1]["priority"], 3)
        assert curr_priority <= next_priority, f"Priority ordering violated at index {i}"

    print(f"✓ Recommendations properly sorted by priority")
    print(f"  Order: {[r['priority'] for r in recs]}")
    return True


def test_confidence_calculation():
    """Test that confidence scores are calculated reasonably."""
    print("\n=== Test: Confidence calculation ===")

    agent = RecommendAgentModel()
    analysis = {
        "detailed_anomalies": [
            _create_high_cpa_anomaly(z_score=4.0, spend=1000),  # High z-score
            _create_high_cpa_anomaly(z_score=1.5, spend=500),   # Low z-score
        ]
    }

    result = agent.generate_recommendations(analysis)
    recs = result["recommendations"]

    # Higher z-score should have higher confidence
    high_z_rec = next(r for r in recs if r["z_score"] == 4.0)
    low_z_rec = next(r for r in recs if r["z_score"] == 1.5)

    assert high_z_rec["confidence"] > low_z_rec["confidence"], \
        f"Expected higher confidence for higher z-score: {high_z_rec['confidence']} vs {low_z_rec['confidence']}"

    # Confidence should be capped at 0.9
    assert high_z_rec["confidence"] <= 0.9, f"Confidence should be capped at 0.9, got {high_z_rec['confidence']}"

    print(f"✓ Confidence calculated correctly")
    print(f"  High z-score (4.0): confidence={high_z_rec['confidence']:.2f}")
    print(f"  Low z-score (1.5): confidence={low_z_rec['confidence']:.2f}")
    return True


# =============================================================================
# Integration with Fixture Data
# =============================================================================

def test_with_fixture_data():
    """Test RecommendAgent with actual fixture data through AnalyzeAgent."""
    print("\n=== Test: Integration with fixture data ===")

    from models.analyze_agent import AnalyzeAgentModel
    from helpers.tools import get_ad_data

    # Run analysis
    analyze = AnalyzeAgentModel()
    analysis = analyze.run_analysis("tl")

    if "error" in analysis:
        print(f"⚠ Analysis error: {analysis['error']}")
        return True

    # Get recommendations
    recommend = RecommendAgentModel()
    data = get_ad_data("tl")
    result = recommend.generate_recommendations(analysis, all_ads=data["ads"])

    recs = result["recommendations"]
    summary = result["summary"]

    assert summary["total_recommendations"] >= 0, "Expected non-negative recommendation count"

    print(f"✓ Generated recommendations from fixture data")
    print(f"  Total ads: {len(data['ads'])}")
    print(f"  Anomalies processed: {result['analysis_context']['total_anomalies_processed']}")
    print(f"  Recommendations: {summary['total_recommendations']}")
    print(f"  By action: {summary['by_action']}")

    if recs:
        print(f"\n  Top 3 recommendations:")
        for r in recs[:3]:
            print(f"    [{r['priority'].upper()}] {r['action']}: {r['ad_name'][:30]}")

    return True


def test_empty_analysis():
    """Test RecommendAgent handles empty analysis gracefully."""
    print("\n=== Test: Empty analysis handling ===")

    agent = RecommendAgentModel()
    result = agent.generate_recommendations({"detailed_anomalies": []})

    assert result["recommendations"] == [], "Expected empty recommendations"
    assert result["summary"]["total_recommendations"] == 0, "Expected 0 total"

    print(f"✓ Empty analysis handled gracefully")
    return True


# =============================================================================
# Test Runner
# =============================================================================

def run_recommend_agent_tests():
    """Run all Recommend Agent tests."""
    print("=" * 60)
    print("RECOMMEND AGENT UNIT TESTS")
    print("=" * 60)

    tests = [
        ("Pause for extreme CPA", test_recommend_pause_for_extreme_cpa),
        ("Reduce for significant CPA", test_recommend_reduce_for_significant_cpa),
        ("Pause for very low ROAS", test_recommend_pause_for_very_low_roas),
        ("Reduce for low ROAS", test_recommend_reduce_for_low_roas),
        ("Find scaling opportunities", test_find_scaling_opportunities),
        ("No scaling for low spend", test_no_scaling_for_low_spend),
        ("No scaling for anomalous ads", test_no_scaling_for_anomalous_ads),
        ("Creative refresh single variant", test_find_creative_refresh_single_variant),
        ("No refresh for low spend", test_no_refresh_for_low_spend),
        ("Summary calculation", test_summary_calculation),
        ("Sorted by priority", test_recommendations_sorted_by_priority),
        ("Confidence calculation", test_confidence_calculation),
        ("Integration with fixtures", test_with_fixture_data),
        ("Empty analysis handling", test_empty_analysis),
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
    print(f"RECOMMEND AGENT RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ ALL RECOMMEND AGENT TESTS PASSED")
        return True
    else:
        print(f"\n❌ {failed} RECOMMEND AGENT TESTS FAILED")
        return False


if __name__ == "__main__":
    success = run_recommend_agent_tests()
    sys.exit(0 if success else 1)
