"""Configuration for anomaly detection, ontology, and RCA tools."""

ANOMALY_CONFIG = {
    "default_threshold_sigma": 2.0,
    "severity_levels": {
        "mild": 1.5,        # 1.5-2σ
        "significant": 2.0,  # 2-3σ
        "extreme": 3.0,      # >3σ
    },
    "metrics": {
        "Spend": {"direction": "high", "min_value": 100},
        "CPA": {"direction": "high", "min_value": 0},
        "ROAS": {"direction": "low", "min_value": 0},
        "CTR": {"direction": "both", "min_value": 0},
        "z_cpa": {"direction": "high", "min_value": None, "use_abs": True},
        "z_roas": {"direction": "low", "min_value": None, "use_abs": True},
        "z_ctr": {"direction": "both", "min_value": None, "use_abs": True},
    },
    "min_sample_size": 10,
    "min_spend_filter": 100,
}

ONTOLOGY_CONFIG = {
    "dimensions": [
        "ad_provider",
        "store",
        "ad_type",
        "creative_status",
        "spend_tier",
        "db_campaign_status",
        "performance_segment",
    ],
    "default_metrics": ["Spend", "ROAS", "CPA", "CTR"],
    "aggregations": {
        "Spend": "sum",
        "ROAS": "mean",
        "CPA": "mean",
        "CTR": "mean",
        "Conversion_Value": "sum",
        "Purchases": "sum",
    },
}

RCA_CONFIG = {
    "analysis_dimensions": [
        "audience_engagement_score",
        "competitive_pressure",
        "creative_variants",
        "unique_creatives",
        "creative_status",
        "budget_utilization",
        "daily_spend_velocity",
        "days_active",
        "recency",
    ],
    "comparison_dimensions": ["ad_provider", "store", "ad_type"],
    "impact_thresholds": {
        "high": 0.5,     # >50% deviation from baseline
        "medium": 0.25,  # 25-50% deviation
        "low": 0.1,      # 10-25% deviation
    },
    "platform_avg_fields": [
        "platform_avg_ctr",
        "platform_avg_cvr",
        "platform_avg_roas",
        "platform_avg_cpm",
    ],
}
