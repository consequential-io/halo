"""
Agatha Analysis Tools - Anomaly Detection, Ontology, and RCA.

These tools are used by the Analyze Agent to find anomalies in ad performance data.
"""

import json
import logging
import math
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any
from collections import defaultdict

from config.anomaly_config import ANOMALY_CONFIG, ONTOLOGY_CONFIG, RCA_CONFIG
from config.settings import settings

logger = logging.getLogger(__name__)


# =============================================================================
# Tool 1: Get Ad Data (HALO-24)
# =============================================================================

def get_ad_data(
    account_id: str = "tl",
    days: int | None = None,
    source: str | None = None
) -> dict[str, Any]:
    """
    Fetch ad performance data from fixtures or BigQuery.

    Args:
        account_id: Account identifier ("tl" for ThirdLove, "wh" for WhisperingHomes)
        days: Number of days of data to fetch (defaults to settings.data_lookback_days)
        source: Data source ("fixture" or "bq")

    Returns:
        Dict with "ads" list and "metadata"
    """
    # Use settings defaults if not specified
    if days is None:
        days = settings.data_lookback_days
    if source is None:
        source = settings.data_source

    if source == "fixture":
        return _get_ad_data_from_fixture(account_id)
    elif source == "bq":
        return _get_ad_data_from_bq(account_id, days)
    else:
        logger.warning(f"Unknown source '{source}', defaulting to fixture")
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


def _get_ad_data_from_bq(account_id: str, days: int) -> dict[str, Any]:
    """
    Fetch ad performance data from BigQuery.

    Args:
        account_id: Account identifier ("tl" or "wh")
        days: Number of days of data to fetch

    Returns:
        Dict with "ads" list and "metadata"
    """
    try:
        from google.cloud import bigquery
        from google.cloud.exceptions import GoogleCloudError
    except ImportError:
        logger.error("google-cloud-bigquery not installed. Falling back to fixtures.")
        return _get_ad_data_from_fixture(account_id)

    view_map = {
        "tl": "northstar_master_combined_tl",
        "wh": "northstar_master_combined_wh",
    }

    view_name = view_map.get(account_id.lower())
    if not view_name:
        return {"ads": [], "error": f"Unknown account_id: {account_id}"}

    try:
        client = bigquery.Client(project=settings.gcp_project)

        # TODO: Add timezone configuration
        # Production uses: DATE(DATETIME(TIMESTAMP(datetime_UTC), @timezone))
        # TODO: Add currency conversion
        # Production uses: SAFE_MULTIPLY(spend, {{currency_field:column}})

        query = f"""
        SELECT
            ad_name,
            ad_provider,
            ad_type,
            store,
            ad_id,
            creative_variants,
            days_active,
            Spend,
            Purchases,
            Conversion_Value,
            total_impressions,
            total_clicks,
            ROAS,
            CPA,
            CTR,
            CVR
        FROM (
            SELECT
                TRIM(REGEXP_REPLACE(AD_NAME, '_', ' ')) as ad_name,
                ANY_VALUE(ad_provider) as ad_provider,
                ANY_VALUE(static_video_adtype) as ad_type,
                ANY_VALUE(store) as store,
                ANY_VALUE(ad_id) as ad_id,
                COUNT(DISTINCT CREATIVE_NAME) as creative_variants,
                COUNT(DISTINCT DATE(TIMESTAMP(datetime_UTC))) as days_active,

                SUM(SAFE_CAST(spend AS FLOAT64)) AS Spend,
                SUM(SAFE_CAST(total_orders AS INT64)) AS Purchases,
                SUM(SAFE_CAST(gross_sales AS FLOAT64)) AS Conversion_Value,
                SUM(SAFE_CAST(total_ad_impression AS INT64)) as total_impressions,
                SUM(SAFE_CAST(ad_click AS INT64)) as total_clicks,

                SAFE_DIVIDE(SUM(SAFE_CAST(gross_sales AS FLOAT64)),
                            NULLIF(SUM(SAFE_CAST(spend AS FLOAT64)), 0)) AS ROAS,
                SAFE_DIVIDE(SUM(SAFE_CAST(spend AS FLOAT64)),
                            NULLIF(SUM(SAFE_CAST(total_orders AS INT64)), 0)) AS CPA,
                SAFE_DIVIDE(SUM(SAFE_CAST(ad_click AS INT64)),
                            NULLIF(SUM(SAFE_CAST(total_ad_impression AS INT64)), 0)) AS CTR,
                SAFE_DIVIDE(SUM(SAFE_CAST(total_orders AS INT64)),
                            NULLIF(SUM(SAFE_CAST(ad_click AS INT64)), 0)) AS CVR

            FROM `{settings.gcp_project}.{settings.bq_dataset}.{view_name}`
            WHERE data_source = 'Ad Providers'
              AND DATE(TIMESTAMP(datetime_UTC)) >= DATE_SUB(CURRENT_DATE(), INTERVAL {days} DAY)
              AND DATE(TIMESTAMP(datetime_UTC)) <= CURRENT_DATE()
            GROUP BY 1
        )
        WHERE Spend >= 100
        ORDER BY Spend DESC
        """

        query_job = client.query(query)
        results = query_job.result()

        ads = []
        for row in results:
            ad = {
                "ad_name": row.ad_name,
                "AD_NAME": row.ad_name,  # For compatibility
                "ad_provider": row.ad_provider,
                "ad_type": row.ad_type,
                "store": row.store,
                "ad_id": row.ad_id,
                "creative_variants": row.creative_variants or 1,
                "days_active": row.days_active or 0,
                "Spend": float(row.Spend) if row.Spend else 0,
                "Purchases": int(row.Purchases) if row.Purchases else 0,
                "Conversion_Value": float(row.Conversion_Value) if row.Conversion_Value else 0,
                "total_impressions": int(row.total_impressions) if row.total_impressions else 0,
                "total_clicks": int(row.total_clicks) if row.total_clicks else 0,
                "ROAS": float(row.ROAS) if row.ROAS else 0,
                "CPA": float(row.CPA) if row.CPA else 0,
                "CTR": float(row.CTR) if row.CTR else 0,
                "CVR": float(row.CVR) if row.CVR else 0,
                # Fields not available from BQ - set to None
                # TODO: Implement derived metrics (requires platform benchmarks CTE)
                "audience_engagement_score": None,
                "competitive_pressure": None,
                "budget_utilization": None,
                "creative_status": "unknown",
                "recency": 0,
            }
            ads.append(ad)

        # Calculate z-scores in Python using LOG transform (matches production)
        ads = _calculate_z_scores_bq(ads)

        return {
            "ads": ads,
            "metadata": {
                "source": "bigquery",
                "account_id": account_id,
                "days": days,
                "query_time": str(datetime.utcnow()),
                "total_ads": len(ads),
            }
        }

    except Exception as e:
        logger.warning(f"BigQuery query failed: {e}. Falling back to fixtures.")
        return _get_ad_data_from_fixture(account_id)


def _calculate_z_scores_bq(ads: list[dict]) -> list[dict]:
    """
    Calculate z-scores using LOG transform (matches production query methodology).

    Production uses: (LOG(metric + 1e-8) - AVG(LOG(metric + 1e-8))) / STDDEV(LOG(metric + 1e-8))
    """
    if len(ads) < 2:
        for ad in ads:
            ad["z_cpa"] = ad["z_roas"] = ad["z_ctr"] = ad["z_cvr"] = 0.0
        return ads

    def log_safe(x):
        """LOG(x + 1e-8) to handle zeros, matching production."""
        return math.log(x + 1e-8) if x is not None and x >= 0 else None

    for metric in ["CPA", "ROAS", "CTR", "CVR"]:
        # Get log-transformed values
        log_values = []
        for ad in ads:
            val = ad.get(metric)
            log_val = log_safe(val)
            if log_val is not None:
                log_values.append(log_val)

        if len(log_values) < 2:
            for ad in ads:
                ad[f"z_{metric.lower()}"] = 0.0
            continue

        # Calculate mean and std of log-transformed values
        mean = sum(log_values) / len(log_values)
        variance = sum((v - mean) ** 2 for v in log_values) / len(log_values)
        std = variance ** 0.5 if variance > 0 else 0

        # Calculate z-scores
        for ad in ads:
            val = ad.get(metric)
            log_val = log_safe(val)
            if log_val is not None and std > 0:
                ad[f"z_{metric.lower()}"] = round((log_val - mean) / std, 4)
            else:
                ad[f"z_{metric.lower()}"] = 0.0

    return ads


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

def _percentile(values: list[float], p: float) -> float:
    """Calculate the p-th percentile of a list of values."""
    if not values:
        return 0
    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * p / 100
    f = int(k)
    c = f + 1 if f + 1 < len(sorted_values) else f
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


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

    # Pre-compute percentiles for data-driven thresholds
    def get_values(field: str) -> list[float]:
        return [ad.get(field, 0) for ad in all_ads if ad.get(field) is not None]

    engagement_values = get_values("audience_engagement_score")
    pressure_values = get_values("competitive_pressure")
    budget_values = get_values("budget_utilization")
    ctr_values = get_values("CTR")

    # 1. Audience Analysis (data-driven: below 25th percentile)
    ad_engagement = anomaly_ad.get("audience_engagement_score") or 0
    if engagement_values:
        p25_engagement = _percentile(engagement_values, 25)
        avg_engagement = sum(engagement_values) / len(engagement_values)

        if ad_engagement < p25_engagement:
            root_causes.append({
                "factor": "audience_engagement",
                "finding": f"Engagement score {ad_engagement:.1f} below 25th percentile ({p25_engagement:.1f}), avg: {avg_engagement:.1f}",
                "impact": "high",
                "suggestion": "Review audience targeting settings",
            })

    # 2. Competitive Pressure (data-driven: above 75th percentile)
    ad_pressure = anomaly_ad.get("competitive_pressure", 0)
    if pressure_values:
        p75_pressure = _percentile(pressure_values, 75)

        if ad_pressure > p75_pressure:
            root_causes.append({
                "factor": "competitive_pressure",
                "finding": f"Competitive pressure {ad_pressure:.2f} above 75th percentile ({p75_pressure:.2f})",
                "impact": "medium",
                "suggestion": "Consider different placements or dayparting",
            })

    # 3. CTR Analysis (data-driven: below 25th percentile)
    ad_ctr = anomaly_ad.get("CTR", 0)
    if ctr_values:
        p25_ctr = _percentile(ctr_values, 25)
        avg_ctr = sum(ctr_values) / len(ctr_values)

        if ad_ctr < p25_ctr:
            root_causes.append({
                "factor": "low_ctr",
                "finding": f"CTR {ad_ctr:.4f} below 25th percentile ({p25_ctr:.4f}), avg: {avg_ctr:.4f}",
                "impact": "high",
                "suggestion": "Improve ad copy, creative, or targeting to increase click-through rate",
            })

    # 4. Creative Analysis
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

    # 5. Budget Analysis (data-driven: above 75th percentile)
    budget_util = anomaly_ad.get("budget_utilization", 0)
    if budget_values:
        p75_budget = _percentile(budget_values, 75)

        if budget_util > p75_budget:
            root_causes.append({
                "factor": "budget_overutilization",
                "finding": f"Budget utilization {budget_util:.0f}% above 75th percentile ({p75_budget:.0f}%)",
                "impact": "medium",
                "suggestion": "Review daily budget caps",
            })

    # 6. Days Active (learning phase)
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
