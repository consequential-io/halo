"""
Agatha Analysis Tools - Anomaly Detection, Ontology, and RCA.

These tools are used by the Analyze Agent to find anomalies in ad performance data.
"""

import json
import statistics
from pathlib import Path
from typing import Any
from collections import defaultdict

from config.anomaly_config import ANOMALY_CONFIG, ONTOLOGY_CONFIG, RCA_CONFIG


# =============================================================================
# Tool 1: Get Ad Data (HALO-24)
# =============================================================================

def get_ad_data(
    account_id: str = "tl",
    days: int = 30,
    source: str = "fixture"
) -> dict[str, Any]:
    """
    Fetch ad performance data from fixtures or BigQuery.

    Args:
        account_id: Account identifier ("tl" for ThirdLove, "wh" for WhisperingHomes)
        days: Number of days of data to fetch (used for BQ, ignored for fixtures)
        source: Data source ("fixture" or "bq")

    Returns:
        Dict with "ads" list and "metadata"
    """
    if source == "fixture":
        return _get_ad_data_from_fixture(account_id)
    else:
        # TODO: Implement BigQuery connector
        return _get_ad_data_from_fixture(account_id)


def _get_ad_data_from_fixture(account_id: str) -> dict[str, Any]:
    """Load ad data from fixture files."""
    fixture_map = {
        "tl": "tl_ad_performance_prod.json",
        "wh": "wh_ad_performance_prod.json",
    }

    filename = fixture_map.get(account_id.lower())
    if not filename:
        return {"ads": [], "error": f"Unknown account_id: {account_id}"}

    # Try multiple paths for fixtures
    possible_paths = [
        Path(__file__).parent.parent.parent / "tests" / "fixtures" / filename,
        Path(__file__).parent.parent / "tests" / "fixtures" / filename,
        Path("tests/fixtures") / filename,
    ]

    for fixture_path in possible_paths:
        if fixture_path.exists():
            with open(fixture_path) as f:
                data = json.load(f)

            # Handle single object with shapes (production format)
            if isinstance(data, dict):
                if "shapes" in data:
                    ads = data["shapes"][0]["data"]
                    metadata = data.get("metadata", {})
                    return {"ads": ads, "metadata": metadata}
                elif "success" in data and "shapes" not in data:
                    # Look for shapes in nested structure
                    return {"ads": [], "error": "No shapes found in fixture"}

            # Handle array wrapper (alternative format)
            if isinstance(data, list) and len(data) > 0:
                first = data[0]
                if isinstance(first, dict) and "shapes" in first:
                    ads = first["shapes"][0]["data"]
                    metadata = first.get("metadata", {})
                    return {"ads": ads, "metadata": metadata}
                # Direct list of ads
                return {"ads": data, "metadata": {"source": "fixture"}}

            return {"ads": [], "error": f"Unexpected fixture format: {type(data)}"}

    return {"ads": [], "error": f"Fixture not found: {filename}"}


# =============================================================================
# Tool 2: Detect Anomalies (HALO-59)
# =============================================================================

def detect_anomalies(
    ads: list[dict],
    metric: str,
    threshold_sigma: float = 2.0,
    direction: str = "both",
    min_spend: float = 100,
    config: dict | None = None
) -> dict[str, Any]:
    """
    Find ads where a metric deviates significantly from baseline.

    Args:
        ads: List of ad dictionaries
        metric: Metric to analyze ("Spend", "CPA", "ROAS", "CTR", "z_cpa", etc.)
        threshold_sigma: Number of standard deviations for anomaly threshold
        direction: "high" (above mean), "low" (below mean), or "both"
        min_spend: Minimum spend to include ad in analysis
        config: Optional config override

    Returns:
        Dict with "anomalies" list and "baseline_stats"
    """
    if config is None:
        config = ANOMALY_CONFIG

    # Filter ads with minimum spend
    eligible = [ad for ad in ads if ad.get("Spend", 0) >= min_spend]

    if len(eligible) < config.get("min_sample_size", 10):
        return {
            "anomalies": [],
            "baseline_stats": {},
            "warning": f"Insufficient sample size: {len(eligible)} < {config.get('min_sample_size', 10)}"
        }

    # Check if metric uses pre-computed z-scores
    use_precomputed_z = metric.startswith("z_")

    if use_precomputed_z:
        # Use pre-computed z-scores directly from fixtures
        anomalies = []
        z_values = [ad.get(metric, 0) for ad in eligible if ad.get(metric) is not None]

        if not z_values:
            return {"anomalies": [], "baseline_stats": {}, "error": f"No {metric} values found"}

        for ad in eligible:
            z_score = ad.get(metric)
            if z_score is None:
                continue

            is_anomaly = False
            if direction == "high" and z_score >= threshold_sigma:
                is_anomaly = True
            elif direction == "low" and z_score <= -threshold_sigma:
                is_anomaly = True
            elif direction == "both" and abs(z_score) >= threshold_sigma:
                is_anomaly = True

            if is_anomaly:
                severity = _get_severity(abs(z_score), config)
                anomalies.append({
                    "ad": ad,
                    "metric": metric,
                    "value": ad.get(metric.replace("z_", "").upper(), z_score),
                    "z_score": round(z_score, 2),
                    "direction": "high" if z_score > 0 else "low",
                    "severity": severity,
                })

        return {
            "anomalies": sorted(anomalies, key=lambda x: abs(x["z_score"]), reverse=True),
            "baseline_stats": {
                "metric": metric,
                "threshold_sigma": threshold_sigma,
                "count": len(eligible),
            }
        }

    # Calculate z-scores from raw metric values
    values = [ad.get(metric, 0) for ad in eligible if ad.get(metric) is not None]

    if not values:
        return {"anomalies": [], "baseline_stats": {}, "error": f"No {metric} values found"}

    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0

    if std == 0:
        return {
            "anomalies": [],
            "baseline_stats": {"mean": mean, "std": 0, "count": len(values)},
            "warning": "Zero standard deviation - all values are identical"
        }

    anomalies = []
    for ad in eligible:
        value = ad.get(metric)
        if value is None:
            continue

        z_score = (value - mean) / std

        is_anomaly = False
        if direction == "high" and z_score >= threshold_sigma:
            is_anomaly = True
        elif direction == "low" and z_score <= -threshold_sigma:
            is_anomaly = True
        elif direction == "both" and abs(z_score) >= threshold_sigma:
            is_anomaly = True

        if is_anomaly:
            severity = _get_severity(abs(z_score), config)
            anomalies.append({
                "ad": ad,
                "metric": metric,
                "value": value,
                "baseline": round(mean, 2),
                "z_score": round(z_score, 2),
                "direction": "high" if z_score > 0 else "low",
                "severity": severity,
            })

    return {
        "anomalies": sorted(anomalies, key=lambda x: abs(x["z_score"]), reverse=True),
        "baseline_stats": {
            "mean": round(mean, 2),
            "std": round(std, 2),
            "median": round(statistics.median(values), 2),
            "count": len(values),
        }
    }


def _get_severity(abs_z_score: float, config: dict) -> str:
    """Determine severity level based on z-score magnitude."""
    levels = config.get("severity_levels", {})
    if abs_z_score >= levels.get("extreme", 3.0):
        return "extreme"
    elif abs_z_score >= levels.get("significant", 2.0):
        return "significant"
    elif abs_z_score >= levels.get("mild", 1.5):
        return "mild"
    return "normal"


# =============================================================================
# Tool 3: Get Ontology (HALO-60)
# =============================================================================

def get_ontology(
    ads: list[dict],
    group_by: list[str],
    metrics: list[str] | None = None,
    config: dict | None = None
) -> dict[str, Any]:
    """
    Return hierarchical breakdown of ad data by dimensions.

    Args:
        ads: List of ad dictionaries
        group_by: Dimensions to group by (e.g., ["ad_provider", "store"])
        metrics: Metrics to aggregate (defaults to Spend, ROAS, CPA, CTR)
        config: Optional config override

    Returns:
        Dict with "breakdown" by dimension values and aggregated metrics
    """
    if config is None:
        config = ONTOLOGY_CONFIG

    if metrics is None:
        metrics = config.get("default_metrics", ["Spend", "ROAS", "CPA", "CTR"])

    # Validate dimensions
    valid_dims = config.get("dimensions", [])
    invalid_dims = [d for d in group_by if d not in valid_dims]
    if invalid_dims:
        return {
            "breakdown": {},
            "error": f"Invalid dimensions: {invalid_dims}. Valid: {valid_dims}"
        }

    # Build hierarchical breakdown
    groups = defaultdict(list)

    for ad in ads:
        # Build key from dimension values
        key_parts = [str(ad.get(dim, "Unknown")) for dim in group_by]
        key = " > ".join(key_parts) if len(key_parts) > 1 else key_parts[0]
        groups[key].append(ad)

    # Aggregate metrics for each group
    aggregations = config.get("aggregations", {})
    breakdown = {}

    for key, group_ads in groups.items():
        breakdown[key] = {"count": len(group_ads)}

        for metric in metrics:
            values = [ad.get(metric) for ad in group_ads if ad.get(metric) is not None]
            if not values:
                continue

            agg_type = aggregations.get(metric, "mean")
            if agg_type == "sum":
                breakdown[key][f"total_{metric.lower()}"] = round(sum(values), 2)
            else:  # mean
                breakdown[key][f"avg_{metric.lower()}"] = round(sum(values) / len(values), 2)

    # Sort by total spend (descending)
    sorted_breakdown = dict(
        sorted(
            breakdown.items(),
            key=lambda x: x[1].get("total_spend", 0),
            reverse=True
        )
    )

    return {
        "breakdown": sorted_breakdown,
        "dimensions_used": group_by,
        "total_ads": len(ads),
        "total_groups": len(sorted_breakdown),
    }


# =============================================================================
# Tool 4: Run RCA - Root Cause Analysis (HALO-61)
# =============================================================================

def run_rca(
    anomaly_ad: dict,
    all_ads: list[dict],
    anomaly_metric: str,
    config: dict | None = None
) -> dict[str, Any]:
    """
    Deep root cause analysis for an anomalous ad.

    Args:
        anomaly_ad: The anomalous ad to analyze
        all_ads: All ads for comparison
        anomaly_metric: The metric that triggered the anomaly
        config: Optional config override

    Returns:
        Dict with anomaly_summary, root_causes, comparison_to_similar, recommended_actions
    """
    if config is None:
        config = RCA_CONFIG

    root_causes = []

    # 1. Audience Analysis
    ad_engagement = anomaly_ad.get("audience_engagement_score") or 0
    if all_ads:
        engagement_values = [
            ad.get("audience_engagement_score") or 0
            for ad in all_ads
            if ad.get("audience_engagement_score") is not None
        ]
        platform_engagement = sum(engagement_values) / len(engagement_values) if engagement_values else 0

        if platform_engagement > 0 and ad_engagement < platform_engagement * 0.5:
            root_causes.append({
                "factor": "audience_engagement",
                "finding": f"Engagement score {ad_engagement:.1f} vs platform avg {platform_engagement:.1f} ({ad_engagement/platform_engagement*100:.0f}%)",
                "impact": "high",
                "suggestion": "Review audience targeting settings",
            })

    # 2. Competitive Pressure
    ad_pressure = anomaly_ad.get("competitive_pressure", 0)
    if ad_pressure > 0.7:
        root_causes.append({
            "factor": "competitive_pressure",
            "finding": f"High competitive pressure: {ad_pressure:.2f} (threshold: 0.7)",
            "impact": "medium",
            "suggestion": "Consider different placements or dayparting",
        })

    # 3. Creative Analysis
    creative_variants = anomaly_ad.get("creative_variants", 1)
    if creative_variants == 1:
        root_causes.append({
            "factor": "creative_variants",
            "finding": "Single creative variant (no A/B testing)",
            "impact": "medium",
            "suggestion": "Test 2-3 creative variants",
        })

    creative_status = anomaly_ad.get("creative_status", "")
    if creative_status == "fatigued":
        recency = anomaly_ad.get("recency", 0)
        root_causes.append({
            "factor": "creative_fatigue",
            "finding": f"Creative marked as fatigued (running for {recency} days)",
            "impact": "high",
            "suggestion": "Refresh creative assets immediately",
        })

    # 4. Budget Analysis
    budget_util = anomaly_ad.get("budget_utilization", 0)
    if budget_util > 100:
        root_causes.append({
            "factor": "budget_overutilization",
            "finding": f"Budget utilization at {budget_util:.0f}% (overspending)",
            "impact": "medium",
            "suggestion": "Review daily budget caps",
        })

    # 5. Days Active (learning phase)
    days_active = anomaly_ad.get("days_active", 0)
    if days_active < 7:
        root_causes.append({
            "factor": "learning_phase",
            "finding": f"Ad only active for {days_active} days (learning phase)",
            "impact": "low",
            "suggestion": "Allow more time for optimization before making changes",
        })

    # 6. Comparison to similar ads
    comparison = _compare_to_similar(anomaly_ad, all_ads, anomaly_metric, config)

    # Generate recommendations
    recommendations = []
    high_impact = [rc for rc in root_causes if rc["impact"] == "high"]
    medium_impact = [rc for rc in root_causes if rc["impact"] == "medium"]

    for rc in high_impact + medium_impact:
        if rc["suggestion"] not in recommendations:
            recommendations.append(rc["suggestion"])

    if not recommendations:
        recommendations = ["Anomaly detected but no clear root cause identified. Manual review recommended."]

    # Calculate potential waste/gain
    metric_value = anomaly_ad.get(anomaly_metric, 0)
    spend = anomaly_ad.get("Spend", 0)

    return {
        "anomaly_summary": {
            "ad_name": anomaly_ad.get("ad_name") or anomaly_ad.get("AD_NAME"),
            "ad_id": anomaly_ad.get("ad_id"),
            "ad_provider": anomaly_ad.get("ad_provider"),
            "metric": anomaly_metric,
            "value": metric_value,
            "z_score": anomaly_ad.get(f"z_{anomaly_metric.lower()}", "N/A"),
            "spend": spend,
        },
        "root_causes": root_causes,
        "comparison_to_similar": comparison,
        "recommended_actions": recommendations,
        "impact_summary": {
            "high_impact_factors": len(high_impact),
            "medium_impact_factors": len(medium_impact),
            "total_factors": len(root_causes),
        }
    }


def _compare_to_similar(
    anomaly_ad: dict,
    all_ads: list[dict],
    metric: str,
    config: dict
) -> dict[str, Any]:
    """Compare anomaly ad to similar ads across dimensions."""
    comparison_dims = config.get("comparison_dimensions", ["ad_provider", "store", "ad_type"])
    result = {}

    for dim in comparison_dims:
        ad_value = anomaly_ad.get(dim)
        if not ad_value:
            continue

        similar = [ad for ad in all_ads if ad.get(dim) == ad_value and ad != anomaly_ad]
        if not similar:
            continue

        metric_values = [ad.get(metric, 0) for ad in similar if ad.get(metric) is not None]
        if metric_values:
            avg = sum(metric_values) / len(metric_values)
            result[f"same_{dim}_avg_{metric.lower()}"] = round(avg, 2)
            result[f"same_{dim}_count"] = len(similar)

    return result
