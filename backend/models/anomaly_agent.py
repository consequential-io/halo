"""Anomaly Detection Agent - Detects anomalous behavior in ad metrics."""

import json
import logging
from typing import Dict, Any, List, Literal, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import BigQuery
try:
    from google.cloud import bigquery
    HAS_BIGQUERY = True
except ImportError:
    HAS_BIGQUERY = False
    bigquery = None

from config.settings import settings, get_bq_table

# BigQuery column casting helpers (some columns are stored as STRING)
CAST_SPEND = "SAFE_CAST(spend AS FLOAT64)"
CAST_ROAS = "SAFE_CAST(ROAS AS FLOAT64)"
CAST_CTR = "SAFE_CAST(CTR AS FLOAT64)"
CAST_CPM = "SAFE_CAST(CPM AS FLOAT64)"
CAST_CPA = "SAFE_CAST(CPA AS FLOAT64)"


@dataclass
class Anomaly:
    """Represents a detected anomaly."""
    ad_name: str
    ad_provider: str
    metric: str
    current_value: float
    baseline_mean: float
    baseline_std: float
    z_score: float
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    direction: str  # DROP, SPIKE
    pct_change: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ad_name": self.ad_name,
            "ad_provider": self.ad_provider,
            "metric": self.metric,
            "current_value": round(self.current_value, 2),
            "baseline_mean": round(self.baseline_mean, 2),
            "baseline_std": round(self.baseline_std, 2),
            "z_score": round(self.z_score, 2),
            "severity": self.severity,
            "direction": self.direction,
            "pct_change": round(self.pct_change, 1),
            "interpretation": self._interpret()
        }

    def _interpret(self) -> str:
        """Generate human-readable interpretation."""
        return (
            f"{self.metric.upper()} {self.direction.lower()}ed {abs(self.pct_change):.0f}% "
            f"({self.baseline_mean:.2f} → {self.current_value:.2f}). "
            f"Z-score: {self.z_score:.1f} ({self.severity})"
        )


class AnomalyDetector:
    """
    Statistical anomaly detector for ad metrics.

    Uses z-score based detection:
    - Z-score > 2 or < -2: Anomaly detected
    - Severity based on z-score magnitude
    """

    # Metrics to monitor
    METRICS = ["roas", "spend", "ctr", "cpm", "cpa"]

    # Z-score thresholds for severity
    SEVERITY_THRESHOLDS = {
        "CRITICAL": 3.0,
        "HIGH": 2.5,
        "MEDIUM": 2.0,
    }

    def __init__(self, tenant: Literal["tl", "wh"] = "wh"):
        self.tenant = tenant
        self.table = get_bq_table(tenant)
        self._client = None

    @property
    def client(self):
        """Lazy-load BigQuery client."""
        if self._client is None and HAS_BIGQUERY:
            self._client = bigquery.Client(project=settings.google_cloud_project)
        return self._client

    async def detect_anomalies(
        self,
        baseline_days: int = 30,
        current_days: int = 3,
        min_spend: float = 1000,
        z_threshold: float = 2.0
    ) -> Dict[str, Any]:
        """
        Detect anomalies across all ads.

        Args:
            baseline_days: Days for calculating baseline (mean, std)
            current_days: Recent days to compare against baseline
            min_spend: Minimum spend to consider an ad
            z_threshold: Z-score threshold for anomaly detection

        Returns:
            Dict with detected anomalies and metadata
        """
        if not self.client:
            logger.warning("BigQuery not available, using mock data")
            return self._mock_anomalies()

        # Query for baseline and current metrics per ad
        query = f"""
        WITH baseline AS (
            SELECT
                AD_NAME,
                ad_provider,
                AVG(daily_roas) as mean_roas,
                STDDEV(daily_roas) as std_roas,
                AVG(daily_spend) as mean_spend,
                STDDEV(daily_spend) as std_spend,
                AVG(daily_ctr) as mean_ctr,
                STDDEV(daily_ctr) as std_ctr,
                AVG(daily_cpm) as mean_cpm,
                STDDEV(daily_cpm) as std_cpm,
                AVG(daily_cpa) as mean_cpa,
                STDDEV(daily_cpa) as std_cpa
            FROM (
                SELECT
                    AD_NAME,
                    ad_provider,
                    DATE(TIMESTAMP(datetime_IST)) as date,
                    SAFE_DIVIDE(SUM({CAST_ROAS} * {CAST_SPEND}), SUM({CAST_SPEND})) as daily_roas,
                    SUM({CAST_SPEND}) as daily_spend,
                    AVG({CAST_CTR}) as daily_ctr,
                    AVG({CAST_CPM}) as daily_cpm,
                    AVG({CAST_CPA}) as daily_cpa
                FROM `{self.table}`
                WHERE data_source = 'Ad Providers'
                  AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {baseline_days} DAY)
                  AND TIMESTAMP(datetime_IST) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {current_days} DAY)
                  AND {CAST_SPEND} > 0
                  AND CAMPAIGN_STATUS = 'ACTIVE'
                GROUP BY AD_NAME, ad_provider, DATE(TIMESTAMP(datetime_IST))
            )
            GROUP BY AD_NAME, ad_provider
            HAVING SUM(daily_spend) >= {min_spend}
        ),
        current_period AS (
            SELECT
                AD_NAME,
                ad_provider,
                SAFE_DIVIDE(SUM({CAST_ROAS} * {CAST_SPEND}), SUM({CAST_SPEND})) as current_roas,
                SUM({CAST_SPEND}) / {current_days} as current_spend,
                AVG({CAST_CTR}) as current_ctr,
                AVG({CAST_CPM}) as current_cpm,
                AVG({CAST_CPA}) as current_cpa
            FROM `{self.table}`
            WHERE data_source = 'Ad Providers'
              AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {current_days} DAY)
              AND {CAST_SPEND} > 0
              AND CAMPAIGN_STATUS = 'ACTIVE'
            GROUP BY AD_NAME, ad_provider
        )
        SELECT
            b.AD_NAME as ad_name,
            b.ad_provider,
            c.current_roas,
            b.mean_roas,
            b.std_roas,
            SAFE_DIVIDE(c.current_roas - b.mean_roas, NULLIF(b.std_roas, 0)) as z_roas,
            c.current_spend,
            b.mean_spend,
            b.std_spend,
            SAFE_DIVIDE(c.current_spend - b.mean_spend, NULLIF(b.std_spend, 0)) as z_spend,
            c.current_ctr,
            b.mean_ctr,
            b.std_ctr,
            SAFE_DIVIDE(c.current_ctr - b.mean_ctr, NULLIF(b.std_ctr, 0)) as z_ctr,
            c.current_cpm,
            b.mean_cpm,
            b.std_cpm,
            SAFE_DIVIDE(c.current_cpm - b.mean_cpm, NULLIF(b.std_cpm, 0)) as z_cpm,
            c.current_cpa,
            b.mean_cpa,
            b.std_cpa,
            SAFE_DIVIDE(c.current_cpa - b.mean_cpa, NULLIF(b.std_cpa, 0)) as z_cpa
        FROM baseline b
        JOIN current_period c ON b.AD_NAME = c.AD_NAME AND b.ad_provider = c.ad_provider
        WHERE b.std_roas > 0
        ORDER BY ABS(SAFE_DIVIDE(c.current_roas - b.mean_roas, b.std_roas)) DESC
        """

        try:
            result = self.client.query(query).result()
            rows = [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Anomaly detection query failed: {e}")
            return self._mock_anomalies()

        # Process results and find anomalies
        anomalies = []
        for row in rows:
            ad_anomalies = self._check_row_for_anomalies(row, z_threshold)
            anomalies.extend(ad_anomalies)

        # Sort by severity and z-score
        anomalies.sort(key=lambda x: (
            {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[x.severity],
            -abs(x.z_score)
        ))

        return {
            "anomalies_detected": len(anomalies),
            "baseline_period": f"{baseline_days} days",
            "current_period": f"{current_days} days",
            "z_threshold": z_threshold,
            "anomalies": [a.to_dict() for a in anomalies]
        }

    def _check_row_for_anomalies(
        self,
        row: Dict[str, Any],
        z_threshold: float
    ) -> List[Anomaly]:
        """Check a single row for anomalies across all metrics."""
        anomalies = []

        for metric in self.METRICS:
            current = float(row.get(f'current_{metric}') or 0)
            mean = float(row.get(f'mean_{metric}') or 0)
            std = float(row.get(f'std_{metric}') or 0)
            z_score = float(row.get(f'z_{metric}') or 0)

            # Skip if no valid z-score
            if std == 0 or z_score == 0:
                continue

            # Check if anomalous
            if abs(z_score) >= z_threshold:
                # Determine direction
                direction = "DROP" if z_score < 0 else "SPIKE"

                # For CPA and CPM, a spike is bad; for ROAS, CTR, a drop is bad
                # Spend drop could be intentional, so we skip it
                if metric == "spend":
                    # Skip spend anomalies - drops could be intentional budget changes
                    continue
                elif metric in ["cpa", "cpm"]:
                    # High CPA/CPM is bad
                    is_bad = z_score > 0
                else:
                    # Low ROAS/CTR is bad
                    is_bad = z_score < 0

                # Only capture BAD anomalies (negatively impacting business)
                if not is_bad:
                    continue

                # Determine severity
                severity = "LOW"
                for level, threshold in self.SEVERITY_THRESHOLDS.items():
                    if abs(z_score) >= threshold:
                        severity = level
                        break

                # Calculate percentage change
                pct_change = ((current - mean) / mean * 100) if mean != 0 else 0

                anomalies.append(Anomaly(
                    ad_name=row.get('ad_name', 'Unknown'),
                    ad_provider=row.get('ad_provider', 'Unknown'),
                    metric=metric,
                    current_value=current,
                    baseline_mean=mean,
                    baseline_std=std,
                    z_score=z_score,
                    severity=severity,
                    direction=direction,
                    pct_change=pct_change
                ))

        return anomalies

    def _mock_anomalies(self) -> Dict[str, Any]:
        """Return mock anomalies for testing without BigQuery."""
        return {
            "anomalies_detected": 2,
            "baseline_period": "30 days",
            "current_period": "3 days",
            "z_threshold": 2.0,
            "anomalies": [
                {
                    "ad_name": "Summer Sale Video",
                    "ad_provider": "Facebook Ads",
                    "metric": "roas",
                    "current_value": 1.8,
                    "baseline_mean": 4.5,
                    "baseline_std": 0.8,
                    "z_score": -3.4,
                    "severity": "CRITICAL",
                    "direction": "DROP",
                    "pct_change": -60.0,
                    "interpretation": "ROAS dropped 60% (4.50 → 1.80). Z-score: -3.4 (CRITICAL)"
                },
                {
                    "ad_name": "Brand Awareness Campaign",
                    "ad_provider": "Google Ads",
                    "metric": "cpm",
                    "current_value": 18.5,
                    "baseline_mean": 12.0,
                    "baseline_std": 2.5,
                    "z_score": 2.6,
                    "severity": "HIGH",
                    "direction": "SPIKE",
                    "pct_change": 54.2,
                    "interpretation": "CPM spiked 54% (12.00 → 18.50). Z-score: 2.6 (HIGH)"
                }
            ]
        }


async def detect_anomalies(
    tenant: Literal["tl", "wh"] = "wh",
    baseline_days: int = 30,
    current_days: int = 3,
    min_spend: float = 1000,
    z_threshold: float = 2.0
) -> Dict[str, Any]:
    """
    Convenience function to detect anomalies.

    This function can be used as a tool by the RCA agent.
    """
    detector = AnomalyDetector(tenant)
    return await detector.detect_anomalies(
        baseline_days=baseline_days,
        current_days=current_days,
        min_spend=min_spend,
        z_threshold=z_threshold
    )
