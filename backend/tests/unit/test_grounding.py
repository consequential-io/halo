"""Unit tests for grounding validation - ensuring LLM outputs cite accurate data."""

import pytest
from helpers.validators import validate_analyze_output


class TestGrounding:
    """Tests to ensure LLM outputs are grounded in source data."""

    def test_grounded_metrics_pass(self, sample_ad, account_avg_roas):
        """Test that correctly grounded metrics pass validation."""
        response = {
            "ad_name": sample_ad["ad_name"],
            "metrics": {
                "spend": sample_ad["spend"],
                "roas": sample_ad["roas"],
                "days_active": sample_ad["days_active"],
                "account_avg_roas": account_avg_roas,
            },
            "chain_of_thought": {
                "data_extracted": {"spend": sample_ad["spend"], "roas": sample_ad["roas"], "days": sample_ad["days_active"]},
                "comparison": {"roas_ratio": "2.17×"},
                "qualification": {"spend_ok": True, "days_ok": True},
                "classification_logic": {"result": "GOOD", "reason": "High ROAS"},
                "confidence_rationale": {"level": "HIGH", "reason": "Strong signal"},
            },
            "classification": "GOOD",
            "recommended_action": "SCALE",
            "confidence": "HIGH",
            "user_explanation": "ROAS is excellent.",
        }

        is_valid, violations = validate_analyze_output(response, sample_ad)

        assert is_valid is True
        assert len(violations) == 0

    def test_fabricated_spend_detected(self, sample_ad, account_avg_roas):
        """Test that fabricated spend values are detected."""
        response = {
            "ad_name": sample_ad["ad_name"],
            "metrics": {
                "spend": 999999,  # Fabricated value
                "roas": sample_ad["roas"],
                "days_active": sample_ad["days_active"],
                "account_avg_roas": account_avg_roas,
            },
            "chain_of_thought": {
                "data_extracted": {"spend": 999999, "roas": sample_ad["roas"], "days": sample_ad["days_active"]},
                "comparison": {"roas_ratio": "2.17×"},
                "qualification": {"spend_ok": True, "days_ok": True},
                "classification_logic": {"result": "GOOD", "reason": "High ROAS"},
                "confidence_rationale": {"level": "HIGH", "reason": "Strong signal"},
            },
            "classification": "GOOD",
            "recommended_action": "SCALE",
            "confidence": "HIGH",
            "user_explanation": "ROAS is excellent.",
        }

        is_valid, violations = validate_analyze_output(response, sample_ad)

        assert is_valid is False
        assert any("Spend mismatch" in v for v in violations)

    def test_fabricated_roas_detected(self, sample_ad, account_avg_roas):
        """Test that fabricated ROAS values are detected."""
        response = {
            "ad_name": sample_ad["ad_name"],
            "metrics": {
                "spend": sample_ad["spend"],
                "roas": 99.99,  # Fabricated value
                "days_active": sample_ad["days_active"],
                "account_avg_roas": account_avg_roas,
            },
            "chain_of_thought": {
                "data_extracted": {"spend": sample_ad["spend"], "roas": 99.99, "days": sample_ad["days_active"]},
                "comparison": {"roas_ratio": "14.5×"},
                "qualification": {"spend_ok": True, "days_ok": True},
                "classification_logic": {"result": "GOOD", "reason": "Extremely high ROAS"},
                "confidence_rationale": {"level": "HIGH", "reason": "Strong signal"},
            },
            "classification": "GOOD",
            "recommended_action": "SCALE",
            "confidence": "HIGH",
            "user_explanation": "ROAS is exceptional.",
        }

        is_valid, violations = validate_analyze_output(response, sample_ad)

        assert is_valid is False
        assert any("ROAS mismatch" in v for v in violations)

    def test_rounding_tolerance(self, sample_ad, account_avg_roas):
        """Test that small rounding differences are tolerated."""
        response = {
            "ad_name": sample_ad["ad_name"],
            "metrics": {
                "spend": sample_ad["spend"] + 0.5,  # Within tolerance
                "roas": sample_ad["roas"] + 0.005,  # Within tolerance
                "days_active": sample_ad["days_active"],
                "account_avg_roas": account_avg_roas,
            },
            "chain_of_thought": {
                "data_extracted": {"spend": sample_ad["spend"], "roas": sample_ad["roas"], "days": sample_ad["days_active"]},
                "comparison": {"roas_ratio": "2.17×"},
                "qualification": {"spend_ok": True, "days_ok": True},
                "classification_logic": {"result": "GOOD", "reason": "High ROAS"},
                "confidence_rationale": {"level": "HIGH", "reason": "Strong signal"},
            },
            "classification": "GOOD",
            "recommended_action": "SCALE",
            "confidence": "HIGH",
            "user_explanation": "ROAS is excellent.",
        }

        is_valid, violations = validate_analyze_output(response, sample_ad)

        assert is_valid is True
        assert len(violations) == 0

    def test_incomplete_cot_detected(self, sample_ad, account_avg_roas):
        """Test that incomplete chain-of-thought is detected."""
        response = {
            "ad_name": sample_ad["ad_name"],
            "metrics": {
                "spend": sample_ad["spend"],
                "roas": sample_ad["roas"],
                "days_active": sample_ad["days_active"],
                "account_avg_roas": account_avg_roas,
            },
            "chain_of_thought": {
                "data_extracted": {"spend": sample_ad["spend"]},
                # Missing: comparison, qualification, classification_logic, confidence_rationale
            },
            "classification": "GOOD",
            "recommended_action": "SCALE",
            "confidence": "HIGH",
            "user_explanation": "ROAS is excellent.",
        }

        is_valid, violations = validate_analyze_output(response, sample_ad)

        assert is_valid is False
        assert any("Missing CoT step" in v for v in violations)
