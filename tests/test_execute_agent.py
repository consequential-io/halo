"""
Execute Agent Unit Tests.

Tests for ad spend execution based on approved recommendations.
Run with: python3 -m pytest tests/test_execute_agent.py -v
Or standalone: python3 tests/test_execute_agent.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from models.execute_agent import ExecuteAgentModel, SUPPORTED_ACTIONS


# =============================================================================
# Test Data Helpers
# =============================================================================

def _create_pause_recommendation() -> dict:
    """Create a pause recommendation for testing."""
    return {
        "action": "pause",
        "ad_name": "Underperforming Campaign",
        "ad_id": "ad_pause_001",
        "ad_provider": "Google Ads",
        "current_spend": 500.0,
        "recommended_change": "-100%",
        "reasoning": "CPA is 3x above average",
        "estimated_impact": 500.0,
        "priority": "critical",
    }


def _create_reduce_recommendation() -> dict:
    """Create a reduce recommendation for testing."""
    return {
        "action": "reduce",
        "ad_name": "High CPA Campaign",
        "ad_id": "ad_reduce_001",
        "ad_provider": "Meta Ads",
        "current_spend": 1000.0,
        "recommended_change": "-50%",
        "reasoning": "CPA z-score of 2.0",
        "estimated_impact": 500.0,
        "priority": "high",
    }


def _create_scale_recommendation() -> dict:
    """Create a scale recommendation for testing."""
    return {
        "action": "scale",
        "ad_name": "Top Performer",
        "ad_id": "ad_scale_001",
        "ad_provider": "Google Ads",
        "current_spend": 300.0,
        "current_roas": 5.5,
        "recommended_change": "+50%",
        "reasoning": "Strong ROAS suggests scaling potential",
        "estimated_impact": 825.0,
        "priority": "high",
    }


def _create_refresh_recommendation() -> dict:
    """Create a creative refresh recommendation for testing."""
    return {
        "action": "refresh_creative",
        "ad_name": "Stale Creative",
        "ad_id": "ad_refresh_001",
        "ad_provider": "Meta Ads",
        "current_spend": 400.0,
        "creative_variants": 1,
        "days_active": 45,
        "recommended_change": "Add 2-3 creative variants",
        "reasoning": "Single creative for 45 days",
        "priority": "medium",
    }


# =============================================================================
# Single Action Tests
# =============================================================================

def test_execute_pause_action():
    """Test executing a pause recommendation."""
    print("\n=== Test: Execute pause action ===")

    agent = ExecuteAgentModel(dry_run=True)
    rec = _create_pause_recommendation()

    result = agent.execute_action(rec, tenant="TL")

    assert result["status"] == "success", f"Expected success, got {result['status']}"
    assert result["action"] == "pause", f"Expected action=pause, got {result['action']}"
    assert result["ad_id"] == "ad_pause_001"
    assert result["dry_run"] is True
    assert "[DRY RUN]" in result["message"]
    assert result["details"]["action_type"] == "pause"

    print(f"✓ Pause action executed successfully (dry run)")
    print(f"  Message: {result['message']}")
    return True


def test_execute_reduce_action():
    """Test executing a budget reduce recommendation."""
    print("\n=== Test: Execute reduce action ===")

    agent = ExecuteAgentModel(dry_run=True)
    rec = _create_reduce_recommendation()

    result = agent.execute_action(rec, tenant="TL")

    assert result["status"] == "success"
    assert result["action"] == "reduce"
    assert result["details"]["action_type"] == "budget_reduce"
    assert result["details"]["current_budget"] == 1000.0
    assert result["details"]["new_budget"] == 500.0  # 50% reduction
    assert result["details"]["change_percent"] == -50

    print(f"✓ Reduce action executed successfully")
    print(f"  Budget: ${result['details']['current_budget']} → ${result['details']['new_budget']}")
    return True


def test_execute_scale_action():
    """Test executing a budget scale recommendation."""
    print("\n=== Test: Execute scale action ===")

    agent = ExecuteAgentModel(dry_run=True)
    rec = _create_scale_recommendation()

    result = agent.execute_action(rec, tenant="TL")

    assert result["status"] == "success"
    assert result["action"] == "scale"
    assert result["details"]["action_type"] == "budget_scale"
    assert result["details"]["current_budget"] == 300.0
    assert result["details"]["new_budget"] == 450.0  # 50% increase
    assert result["details"]["change_percent"] == 50

    print(f"✓ Scale action executed successfully")
    print(f"  Budget: ${result['details']['current_budget']} → ${result['details']['new_budget']}")
    return True


def test_execute_refresh_creative_action():
    """Test executing a creative refresh recommendation."""
    print("\n=== Test: Execute refresh creative action ===")

    agent = ExecuteAgentModel(dry_run=True)
    rec = _create_refresh_recommendation()

    result = agent.execute_action(rec, tenant="TL")

    assert result["status"] == "success"
    assert result["action"] == "refresh_creative"
    assert result["details"]["action_type"] == "creative_refresh_flag"
    assert result["details"]["requires_manual_action"] is True

    print(f"✓ Creative refresh flagged successfully")
    print(f"  Note: {result['message']}")
    return True


def test_unsupported_action_skipped():
    """Test that unsupported actions are skipped."""
    print("\n=== Test: Unsupported action skipped ===")

    agent = ExecuteAgentModel(dry_run=True)
    rec = {
        "action": "delete_campaign",  # Not supported
        "ad_id": "ad_unknown_001",
        "ad_name": "Unknown Action",
    }

    result = agent.execute_action(rec, tenant="TL")

    assert result["status"] == "skipped"
    assert "Unsupported action" in result["message"]

    print(f"✓ Unsupported action correctly skipped")
    print(f"  Message: {result['message']}")
    return True


# =============================================================================
# Batch Execution Tests
# =============================================================================

def test_execute_batch_all():
    """Test executing all recommendations in a batch."""
    print("\n=== Test: Execute batch (all) ===")

    agent = ExecuteAgentModel(dry_run=True)
    recommendations = [
        _create_pause_recommendation(),
        _create_reduce_recommendation(),
        _create_scale_recommendation(),
        _create_refresh_recommendation(),
    ]

    result = agent.execute_batch(recommendations, tenant="TL")

    assert result["summary"]["total_processed"] == 4
    assert result["summary"]["success"] == 4
    assert result["summary"]["failed"] == 0
    assert result["summary"]["skipped"] == 0
    assert result["summary"]["dry_run"] is True

    print(f"✓ Batch execution completed")
    print(f"  Processed: {result['summary']['total_processed']}")
    print(f"  Success: {result['summary']['success']}")
    return True


def test_execute_batch_filtered():
    """Test executing only approved recommendations."""
    print("\n=== Test: Execute batch (filtered by approved_ad_ids) ===")

    agent = ExecuteAgentModel(dry_run=True)
    recommendations = [
        _create_pause_recommendation(),    # ad_pause_001
        _create_reduce_recommendation(),   # ad_reduce_001
        _create_scale_recommendation(),    # ad_scale_001
        _create_refresh_recommendation(),  # ad_refresh_001
    ]

    # Only approve pause and scale
    approved_ids = ["ad_pause_001", "ad_scale_001"]
    result = agent.execute_batch(recommendations, approved_ad_ids=approved_ids, tenant="TL")

    assert result["summary"]["total_processed"] == 2
    assert result["summary"]["success"] == 2

    executed_ids = [r["ad_id"] for r in result["results"]]
    assert "ad_pause_001" in executed_ids
    assert "ad_scale_001" in executed_ids
    assert "ad_reduce_001" not in executed_ids

    print(f"✓ Filtered batch execution completed")
    print(f"  Approved: {approved_ids}")
    print(f"  Executed: {executed_ids}")
    return True


def test_execute_batch_with_mixed_results():
    """Test batch with some unsupported actions."""
    print("\n=== Test: Execute batch (mixed results) ===")

    agent = ExecuteAgentModel(dry_run=True)
    recommendations = [
        _create_pause_recommendation(),
        {"action": "unknown_action", "ad_id": "bad_001", "ad_name": "Bad"},
        _create_scale_recommendation(),
    ]

    result = agent.execute_batch(recommendations, tenant="TL")

    assert result["summary"]["total_processed"] == 3
    assert result["summary"]["success"] == 2
    assert result["summary"]["skipped"] == 1

    print(f"✓ Mixed batch handled correctly")
    print(f"  Success: {result['summary']['success']}, Skipped: {result['summary']['skipped']}")
    return True


def test_execute_batch_empty():
    """Test executing empty batch."""
    print("\n=== Test: Execute batch (empty) ===")

    agent = ExecuteAgentModel(dry_run=True)
    result = agent.execute_batch([], tenant="TL")

    assert result["summary"]["total_processed"] == 0
    assert result["summary"]["success"] == 0

    print(f"✓ Empty batch handled gracefully")
    return True


# =============================================================================
# Dry Run vs Real Execution Tests
# =============================================================================

def test_dry_run_mode():
    """Test that dry_run mode produces correct messages."""
    print("\n=== Test: Dry run mode ===")

    agent = ExecuteAgentModel(dry_run=True)
    rec = _create_pause_recommendation()

    result = agent.execute_action(rec)

    assert result["dry_run"] is True
    assert "[DRY RUN]" in result["message"]

    print(f"✓ Dry run mode correctly indicated")
    return True


def test_real_execution_mode():
    """Test that non-dry-run mode produces correct messages."""
    print("\n=== Test: Real execution mode ===")

    agent = ExecuteAgentModel(dry_run=False)
    rec = _create_pause_recommendation()

    result = agent.execute_action(rec)

    assert result["dry_run"] is False
    assert "[DRY RUN]" not in result["message"]

    print(f"✓ Real execution mode correctly indicated")
    print(f"  Message: {result['message']}")
    return True


# =============================================================================
# Supported Actions Tests
# =============================================================================

def test_supported_actions():
    """Test that all expected actions are supported."""
    print("\n=== Test: Supported actions ===")

    expected = {"pause", "reduce", "scale", "refresh_creative"}
    assert SUPPORTED_ACTIONS == expected, f"Expected {expected}, got {SUPPORTED_ACTIONS}"

    print(f"✓ All expected actions supported: {SUPPORTED_ACTIONS}")
    return True


# =============================================================================
# Integration Test
# =============================================================================

def test_integration_with_recommend_agent():
    """Test Execute Agent with actual RecommendAgent output."""
    print("\n=== Test: Integration with RecommendAgent ===")

    from models.analyze_agent import AnalyzeAgentModel
    from models.recommend_agent import RecommendAgentModel
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
    rec_result = recommend.generate_recommendations(analysis, all_ads=data["ads"])

    recommendations = rec_result["recommendations"]
    if not recommendations:
        print(f"⚠ No recommendations generated, skipping execution test")
        return True

    # Execute first 3 recommendations
    execute = ExecuteAgentModel(dry_run=True)
    exec_result = execute.execute_batch(recommendations[:3], tenant="TL")

    assert exec_result["summary"]["total_processed"] <= 3
    assert "timestamp" in exec_result

    print(f"✓ Full pipeline integration test passed")
    print(f"  Recommendations: {len(recommendations)}")
    print(f"  Executed: {exec_result['summary']['total_processed']}")
    print(f"  Success: {exec_result['summary']['success']}")
    return True


# =============================================================================
# Test Runner
# =============================================================================

def run_execute_agent_tests():
    """Run all Execute Agent tests."""
    print("=" * 60)
    print("EXECUTE AGENT UNIT TESTS")
    print("=" * 60)

    tests = [
        ("Execute pause action", test_execute_pause_action),
        ("Execute reduce action", test_execute_reduce_action),
        ("Execute scale action", test_execute_scale_action),
        ("Execute refresh creative", test_execute_refresh_creative_action),
        ("Unsupported action skipped", test_unsupported_action_skipped),
        ("Batch execution (all)", test_execute_batch_all),
        ("Batch execution (filtered)", test_execute_batch_filtered),
        ("Batch execution (mixed)", test_execute_batch_with_mixed_results),
        ("Batch execution (empty)", test_execute_batch_empty),
        ("Dry run mode", test_dry_run_mode),
        ("Real execution mode", test_real_execution_mode),
        ("Supported actions", test_supported_actions),
        ("Integration with RecommendAgent", test_integration_with_recommend_agent),
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
    print(f"EXECUTE AGENT RESULTS: {passed}/{len(tests)} tests passed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ ALL EXECUTE AGENT TESTS PASSED")
        return True
    else:
        print(f"\n❌ {failed} EXECUTE AGENT TESTS FAILED")
        return False


if __name__ == "__main__":
    success = run_execute_agent_tests()
    sys.exit(0 if success else 1)
