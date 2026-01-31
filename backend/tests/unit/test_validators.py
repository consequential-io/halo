"""Unit tests for validators."""

import pytest
from helpers.validators import (
    validate_analyze_output,
    handle_validation_failure,
    find_ad_in_source,
)


class TestValidateAnalyzeOutput:
    """Tests for validate_analyze_output function."""

    def test_valid_response(self, sample_analysis_result, sample_ad):
        """Test that a valid response passes validation."""
        is_valid, violations = validate_analyze_output(
            sample_analysis_result, sample_ad
        )
        assert is_valid is True
        assert len(violations) == 0

    def test_missing_required_field(self, sample_analysis_result, sample_ad):
        """Test that missing required fields are caught."""
        del sample_analysis_result["classification"]

        is_valid, violations = validate_analyze_output(
            sample_analysis_result, sample_ad
        )

        assert is_valid is False
        assert "Missing field: classification" in violations

    def test_metrics_mismatch_spend(self, sample_analysis_result, sample_ad):
        """Test that spend mismatch is caught."""
        sample_analysis_result["metrics"]["spend"] = 99999  # Wrong value

        is_valid, violations = validate_analyze_output(
            sample_analysis_result, sample_ad
        )

        assert is_valid is False
        assert any("Spend mismatch" in v for v in violations)

    def test_metrics_mismatch_roas(self, sample_analysis_result, sample_ad):
        """Test that ROAS mismatch is caught."""
        sample_analysis_result["metrics"]["roas"] = 99.99  # Wrong value

        is_valid, violations = validate_analyze_output(
            sample_analysis_result, sample_ad
        )

        assert is_valid is False
        assert any("ROAS mismatch" in v for v in violations)

    def test_missing_cot_step(self, sample_analysis_result, sample_ad):
        """Test that missing CoT steps are caught."""
        del sample_analysis_result["chain_of_thought"]["comparison"]

        is_valid, violations = validate_analyze_output(
            sample_analysis_result, sample_ad
        )

        assert is_valid is False
        assert "Missing CoT step: comparison" in violations

    def test_invalid_classification(self, sample_analysis_result, sample_ad):
        """Test that invalid classification values are caught."""
        sample_analysis_result["classification"] = "EXCELLENT"  # Invalid

        is_valid, violations = validate_analyze_output(
            sample_analysis_result, sample_ad
        )

        assert is_valid is False
        assert any("Invalid classification" in v for v in violations)

    def test_invalid_action(self, sample_analysis_result, sample_ad):
        """Test that invalid action values are caught."""
        sample_analysis_result["recommended_action"] = "BOOST"  # Invalid

        is_valid, violations = validate_analyze_output(
            sample_analysis_result, sample_ad
        )

        assert is_valid is False
        assert any("Invalid recommended_action" in v for v in violations)

    def test_invalid_confidence(self, sample_analysis_result, sample_ad):
        """Test that invalid confidence values are caught."""
        sample_analysis_result["confidence"] = "VERY_HIGH"  # Invalid

        is_valid, violations = validate_analyze_output(
            sample_analysis_result, sample_ad
        )

        assert is_valid is False
        assert any("Invalid confidence" in v for v in violations)


class TestHandleValidationFailure:
    """Tests for handle_validation_failure function."""

    def test_retry_on_first_attempt(self, sample_analysis_result):
        """Test that first failure returns retry action."""
        violations = ["Missing field: classification"]

        result = handle_validation_failure(
            sample_analysis_result, violations, retry_count=0
        )

        assert result["action"] == "retry"
        assert result["feedback"] == violations

    def test_retry_on_second_attempt(self, sample_analysis_result):
        """Test that second failure still returns retry action."""
        violations = ["Missing field: classification"]

        result = handle_validation_failure(
            sample_analysis_result, violations, retry_count=1
        )

        assert result["action"] == "retry"

    def test_degrade_after_max_retries(self, sample_analysis_result):
        """Test that max retries triggers degradation."""
        violations = ["Missing field: classification"]

        result = handle_validation_failure(
            sample_analysis_result, violations, retry_count=2
        )

        assert result["action"] == "degrade"
        assert result["result"]["classification"] == "MANUAL_REVIEW"
        assert result["result"]["violations"] == violations


class TestFindAdInSource:
    """Tests for find_ad_in_source function."""

    def test_find_existing_ad(self, thirdlove_ads):
        """Test finding an existing ad."""
        ad = find_ad_in_source("Thirdlove® Bras", thirdlove_ads)
        assert ad is not None
        assert ad["ad_name"] == "Thirdlove® Bras"

    def test_find_nonexistent_ad(self, thirdlove_ads):
        """Test finding a non-existent ad returns None."""
        ad = find_ad_in_source("Nonexistent Ad", thirdlove_ads)
        assert ad is None
