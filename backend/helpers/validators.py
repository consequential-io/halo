"""Validation layer for LLM outputs."""

from typing import Dict, Any, Tuple, List, Optional


def validate_cot_content(
    cot: Dict[str, Any],
    source_data: Dict[str, Any],
    account_avg_roas: float,
    classification: str
) -> List[str]:
    """
    Validate chain-of-thought content is grounded and consistent.

    Args:
        cot: The chain_of_thought dict from LLM response
        source_data: The original source data for this ad
        account_avg_roas: The account's average ROAS for comparison
        classification: The LLM's classification result

    Returns:
        List of violations (empty if valid).
    """
    violations = []

    # 1. data_extracted matches source
    data_extracted = cot.get("data_extracted", {})
    if abs(data_extracted.get("spend", 0) - source_data.get("spend", 0)) > 1:
        violations.append(
            f"CoT data_extracted.spend={data_extracted.get('spend')} "
            f"doesn't match source spend={source_data.get('spend')}"
        )
    if abs(data_extracted.get("roas", 0) - source_data.get("roas", 0)) > 0.01:
        violations.append(
            f"CoT data_extracted.roas={data_extracted.get('roas')} "
            f"doesn't match source roas={source_data.get('roas')}"
        )
    if abs(data_extracted.get("days", 0) - source_data.get("days_active", 0)) > 0:
        violations.append(
            f"CoT data_extracted.days={data_extracted.get('days')} "
            f"doesn't match source days_active={source_data.get('days_active')}"
        )

    # 2. qualification flags are accurate
    qualification = cot.get("qualification", {})
    actual_spend_ok = source_data.get("spend", 0) >= 1000
    actual_days_ok = source_data.get("days_active", 0) >= 7

    if qualification.get("spend_ok") != actual_spend_ok:
        violations.append(
            f"CoT qualification.spend_ok={qualification.get('spend_ok')} "
            f"but actual spend={source_data.get('spend')} (threshold=1000)"
        )
    if qualification.get("days_ok") != actual_days_ok:
        violations.append(
            f"CoT qualification.days_ok={qualification.get('days_ok')} "
            f"but actual days={source_data.get('days_active')} (threshold=7)"
        )

    # 3. classification_logic.result matches classification
    logic = cot.get("classification_logic", {})
    if logic.get("result") != classification:
        violations.append(
            f"CoT classification_logic.result={logic.get('result')} "
            f"doesn't match classification={classification}"
        )

    return violations


def validate_analyze_output(
    llm_response: Dict[str, Any],
    source_data: Dict[str, Any],
    account_avg_roas: float = 0
) -> Tuple[bool, List[str]]:
    """
    Validates LLM output is grounded and complete.

    Args:
        llm_response: The response from the Analyze Agent
        source_data: The original source data for this ad
        account_avg_roas: The account's average ROAS for comparison validation

    Returns:
        Tuple of (is_valid, list_of_violations)

    Checks:
    1. Required fields present
    2. Cited metrics match source data
    3. CoT chain complete and content grounded
    4. Classification values valid

    Does NOT check classification "correctness" - LLM judgment allowed.
    """
    violations = []

    # 1. Required fields
    required = [
        "ad_name", "metrics", "classification", "recommended_action",
        "confidence", "chain_of_thought", "user_explanation"
    ]
    for field in required:
        if field not in llm_response:
            violations.append(f"Missing field: {field}")

    # 2. Cited metrics match source (within tolerance)
    if "metrics" in llm_response:
        cited = llm_response["metrics"]
        actual_spend = source_data.get("spend", 0)
        actual_roas = source_data.get("roas", 0)

        cited_spend = cited.get("spend", 0)
        cited_roas = cited.get("roas", 0)

        if abs(cited_spend - actual_spend) > 1:
            violations.append(
                f"Spend mismatch: cited {cited_spend}, actual {actual_spend}"
            )
        if abs(cited_roas - actual_roas) > 0.01:
            violations.append(
                f"ROAS mismatch: cited {cited_roas}, actual {actual_roas}"
            )

    # 3. CoT completeness and content validation
    cot_required = [
        "data_extracted", "comparison", "qualification",
        "classification_logic", "confidence_rationale"
    ]
    if "chain_of_thought" in llm_response:
        cot = llm_response["chain_of_thought"]
        for step in cot_required:
            if step not in cot:
                violations.append(f"Missing CoT step: {step}")

        # Validate CoT content is grounded and consistent
        classification = llm_response.get("classification", "")
        cot_violations = validate_cot_content(
            cot, source_data, account_avg_roas, classification
        )
        violations.extend(cot_violations)

    # 4. Valid classification values
    valid_classifications = ["GOOD", "OK", "WARNING", "BAD", "WAIT"]
    classification = llm_response.get("classification")
    if classification not in valid_classifications:
        violations.append(
            f"Invalid classification: {classification}. "
            f"Must be one of {valid_classifications}"
        )

    # 5. Valid recommended_action values
    valid_actions = ["SCALE", "MONITOR", "REVIEW", "REDUCE", "PAUSE", "WAIT"]
    action = llm_response.get("recommended_action")
    if action not in valid_actions:
        violations.append(
            f"Invalid recommended_action: {action}. "
            f"Must be one of {valid_actions}"
        )

    # 6. Valid confidence values
    valid_confidence = ["HIGH", "MEDIUM", "LOW"]
    confidence = llm_response.get("confidence")
    if confidence not in valid_confidence:
        violations.append(
            f"Invalid confidence: {confidence}. "
            f"Must be one of {valid_confidence}"
        )

    return (len(violations) == 0, violations)


def handle_validation_failure(
    llm_response: Dict[str, Any],
    violations: List[str],
    retry_count: int
) -> Dict[str, Any]:
    """
    Handle validation failures with retry or graceful degradation.

    Args:
        llm_response: The failed LLM response
        violations: List of validation violations
        retry_count: Current retry attempt number

    Returns:
        Dict with action ("retry" or "degrade") and relevant data
    """
    if retry_count < 2:
        # Retry with feedback
        return {
            "action": "retry",
            "feedback": violations,
            "message": f"Validation failed. Issues: {', '.join(violations)}"
        }
    else:
        # Graceful degradation after 2 retries
        return {
            "action": "degrade",
            "result": {
                "ad_name": llm_response.get("ad_name", "unknown"),
                "classification": "MANUAL_REVIEW",
                "recommended_action": "REVIEW",
                "confidence": "LOW",
                "user_explanation": (
                    "Unable to classify automatically. Please review manually."
                ),
                "violations": violations,
                "original_response": llm_response,
            }
        }


def find_ad_in_source(ad_name: str, source_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find an ad by name in the source data."""
    for ad in source_data.get("ads", []):
        if ad.get("ad_name") == ad_name:
            return ad
    return None
