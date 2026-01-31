"""
Controller Unit Tests.

Tests for Agatha Controller workflow orchestration.
Run with: python3 tests/test_controller.py
"""

import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from controllers.agatha_controller import AgathaController, get_controller
from config.session_manager import get_session_manager


# =============================================================================
# Session Manager Tests
# =============================================================================

def test_session_creation():
    """Test session creation and retrieval."""
    print("\n=== Test: Session creation ===")

    mgr = get_session_manager()
    session = mgr.create_session("TL")

    assert session is not None
    assert session.tenant == "TL"
    assert session.session_id is not None

    # Retrieve session
    retrieved = mgr.get_session(session.session_id)
    assert retrieved is not None
    assert retrieved.session_id == session.session_id

    print(f"✓ Session created: {session.session_id[:8]}...")
    return True


def test_session_update():
    """Test session data updates."""
    print("\n=== Test: Session update ===")

    mgr = get_session_manager()
    session = mgr.create_session("WH")

    # Update with analysis
    updated = mgr.update_session(
        session.session_id,
        analysis_result={"summary": {"test": True}},
    )

    assert updated is not None
    assert updated.analysis_result is not None
    assert updated.analysis_result["summary"]["test"] is True

    print(f"✓ Session updated with analysis data")
    return True


def test_session_not_found():
    """Test handling of non-existent session."""
    print("\n=== Test: Session not found ===")

    mgr = get_session_manager()
    session = mgr.get_session("non-existent-session-id")

    assert session is None

    print(f"✓ Non-existent session returns None")
    return True


# =============================================================================
# Controller Tests
# =============================================================================

def test_controller_analysis():
    """Test controller analysis workflow."""
    print("\n=== Test: Controller analysis ===")

    controller = get_controller()
    result = controller.run_analysis("TL", days=30, source="fixture")

    assert "session_id" in result
    assert "error" not in result
    assert result["tenant"] == "TL"
    assert result["total_ads"] > 0

    print(f"✓ Analysis completed")
    print(f"  Session: {result['session_id'][:8]}...")
    print(f"  Anomalies: {result['anomalies_found']}")
    print(f"  Total ads: {result['total_ads']}")
    return result["session_id"]


def test_controller_recommendations_sync():
    """Test controller recommendations workflow (sync)."""
    print("\n=== Test: Controller recommendations (sync) ===")

    controller = get_controller()

    # First run analysis
    analysis = controller.run_analysis("TL", days=30, source="fixture")
    session_id = analysis["session_id"]

    # Then get recommendations (sync version, no LLM)
    result = controller.run_recommendations_sync(session_id, enable_llm_reasoning=False)

    assert "error" not in result
    assert result["session_id"] == session_id
    assert "recommendations" in result
    assert "summary" in result

    print(f"✓ Recommendations generated (sync)")
    print(f"  Total: {result['summary']['total_recommendations']}")
    return session_id


async def test_controller_recommendations_async():
    """Test controller recommendations workflow (async)."""
    print("\n=== Test: Controller recommendations (async) ===")

    controller = get_controller()

    # First run analysis
    analysis = controller.run_analysis("TL", days=30, source="fixture")
    session_id = analysis["session_id"]

    # Then get recommendations (async version, no LLM for speed)
    result = await controller.run_recommendations(session_id, enable_llm_reasoning=False)

    assert "error" not in result
    assert result["session_id"] == session_id
    assert len(result["recommendations"]) > 0

    print(f"✓ Recommendations generated (async)")
    print(f"  Total: {result['summary']['total_recommendations']}")
    return session_id


async def test_controller_execution():
    """Test controller execution workflow."""
    print("\n=== Test: Controller execution ===")

    controller = get_controller()

    # Run full workflow
    analysis = controller.run_analysis("TL", days=30, source="fixture")
    session_id = analysis["session_id"]

    await controller.run_recommendations(session_id, enable_llm_reasoning=False)

    # Execute with dry_run
    result = await controller.run_execution(
        session_id,
        approved_ad_ids=None,  # Execute all
        dry_run=True
    )

    assert "error" not in result
    assert result["session_id"] == session_id
    assert "results" in result
    assert result["summary"]["dry_run"] is True

    print(f"✓ Execution completed (dry run)")
    print(f"  Processed: {result['summary']['total_processed']}")
    print(f"  Success: {result['summary']['success']}")
    return True


async def test_controller_full_workflow():
    """Test complete analysis → recommend → execute workflow."""
    print("\n=== Test: Full workflow ===")

    controller = get_controller()

    # Step 1: Analysis
    analysis = controller.run_analysis("TL", days=30, source="fixture")
    assert "error" not in analysis
    session_id = analysis["session_id"]
    print(f"  Step 1: Analysis complete - {analysis['anomalies_found']} anomalies")

    # Step 2: Recommendations
    recs = await controller.run_recommendations(session_id, enable_llm_reasoning=False)
    assert "error" not in recs
    print(f"  Step 2: Recommendations complete - {recs['summary']['total_recommendations']} recs")

    # Step 3: Execution
    exec_result = await controller.run_execution(session_id, dry_run=True)
    assert "error" not in exec_result
    print(f"  Step 3: Execution complete - {exec_result['summary']['success']} success")

    # Verify session state
    state = controller.get_session_state(session_id)
    assert state is not None
    assert state["has_analysis"] is True
    assert state["has_recommendations"] is True
    assert state["has_execution"] is True

    print(f"\n✓ Full workflow completed successfully")
    return True


def test_controller_invalid_session():
    """Test controller handling of invalid session."""
    print("\n=== Test: Controller invalid session ===")

    controller = get_controller()

    # Try recommendations with invalid session
    result = controller.run_recommendations_sync("invalid-session-id")

    assert "error" in result
    assert "not found" in result["error"].lower()

    print(f"✓ Invalid session handled correctly")
    return True


# =============================================================================
# Test Runner
# =============================================================================

def run_controller_tests():
    """Run all controller tests."""
    print("=" * 60)
    print("CONTROLLER UNIT TESTS")
    print("=" * 60)

    sync_tests = [
        ("Session creation", test_session_creation),
        ("Session update", test_session_update),
        ("Session not found", test_session_not_found),
        ("Controller analysis", test_controller_analysis),
        ("Controller recommendations (sync)", test_controller_recommendations_sync),
        ("Controller invalid session", test_controller_invalid_session),
    ]

    async_tests = [
        ("Controller recommendations (async)", test_controller_recommendations_async),
        ("Controller execution", test_controller_execution),
        ("Full workflow", test_controller_full_workflow),
    ]

    passed = 0
    failed = 0

    # Run sync tests
    for name, test_fn in sync_tests:
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

    # Run async tests
    for name, test_fn in async_tests:
        try:
            asyncio.run(test_fn())
            passed += 1
        except AssertionError as e:
            print(f"\n✗ FAILED: {name}")
            print(f"  Error: {e}")
            failed += 1
        except Exception as e:
            print(f"\n✗ ERROR: {name}")
            print(f"  Exception: {type(e).__name__}: {e}")
            failed += 1

    total = len(sync_tests) + len(async_tests)
    print("\n" + "=" * 60)
    print(f"CONTROLLER RESULTS: {passed}/{total} tests passed")
    print("=" * 60)

    if failed == 0:
        print("\n✅ ALL CONTROLLER TESTS PASSED")
        return True
    else:
        print(f"\n❌ {failed} CONTROLLER TESTS FAILED")
        return False


if __name__ == "__main__":
    success = run_controller_tests()
    sys.exit(0 if success else 1)
