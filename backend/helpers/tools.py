"""Agent tools for data retrieval."""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Literal, Optional

try:
    from google.adk.tools import FunctionTool
    HAS_ADK = True
except ImportError:
    HAS_ADK = False
    FunctionTool = None  # type: ignore

try:
    from google.cloud import bigquery
    HAS_BIGQUERY = True
except ImportError:
    HAS_BIGQUERY = False
    bigquery = None  # type: ignore

from config.settings import settings, get_bq_table

logger = logging.getLogger(__name__)

# Path to fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


# BigQuery SQL Queries
# Note: datetime_IST is stored as STRING, use TIMESTAMP() to convert
ACCOUNT_AVG_ROAS_QUERY = """
SELECT
    SAFE_DIVIDE(SUM(ROAS * spend), SUM(spend)) as weighted_avg_roas,
    SUM(spend) as total_spend,
    MIN(DATE(TIMESTAMP(datetime_IST))) as start_date,
    MAX(DATE(TIMESTAMP(datetime_IST))) as end_date
FROM `{table}`
WHERE data_source = 'Ad Providers'
  AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
  AND spend > 0
  AND ad_provider IN ('Facebook Ads', 'Google Ads', 'TikTok Ads')
"""

AD_PERFORMANCE_QUERY = """
SELECT
    AD_NAME as ad_name,
    ad_provider,
    SUM(spend) as spend,
    SAFE_DIVIDE(SUM(ROAS * spend), SUM(spend)) as roas,
    DATE_DIFF(
        MAX(DATE(TIMESTAMP(datetime_IST))),
        MIN(DATE(TIMESTAMP(datetime_IST))),
        DAY
    ) + 1 as days_active
FROM `{table}`
WHERE data_source = 'Ad Providers'
  AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
  AND spend > 0
  AND ad_provider IN ('Facebook Ads', 'Google Ads', 'TikTok Ads')
  AND AD_NAME IS NOT NULL
  AND AD_NAME != ''
GROUP BY AD_NAME, ad_provider
HAVING spend >= 1000
ORDER BY spend DESC
LIMIT 100
"""


class BigQueryConnector:
    """Connector for BigQuery data retrieval."""

    def __init__(self, project_id: Optional[str] = None):
        if not HAS_BIGQUERY:
            raise ImportError("google-cloud-bigquery not installed")
        self.project_id = project_id or settings.google_cloud_project
        self._client: Optional[bigquery.Client] = None

    @property
    def client(self) -> bigquery.Client:
        """Lazy-load BigQuery client."""
        if self._client is None:
            self._client = bigquery.Client(project=self.project_id)
        return self._client

    def get_account_avg_roas(
        self,
        tenant: Literal["tl", "wh"] = "tl",
        days: int = 30
    ) -> Dict[str, Any]:
        """Get account average ROAS and metadata."""
        table = get_bq_table(tenant)
        query = ACCOUNT_AVG_ROAS_QUERY.format(table=table, days=days)

        logger.info(f"Querying account avg ROAS for {tenant}, last {days} days")
        result = self.client.query(query).result()

        for row in result:
            return {
                "weighted_avg_roas": float(row.weighted_avg_roas or 0),
                "total_spend": float(row.total_spend or 0),
                "start_date": str(row.start_date) if row.start_date else None,
                "end_date": str(row.end_date) if row.end_date else None,
            }

        return {"weighted_avg_roas": 0, "total_spend": 0}

    def get_ad_performance(
        self,
        tenant: Literal["tl", "wh"] = "tl",
        days: int = 30
    ) -> list:
        """Get ad-level performance data."""
        table = get_bq_table(tenant)
        query = AD_PERFORMANCE_QUERY.format(table=table, days=days)

        logger.info(f"Querying ad performance for {tenant}, last {days} days")
        result = self.client.query(query).result()

        ads = []
        for row in result:
            ads.append({
                "ad_name": row.ad_name,
                "ad_provider": row.ad_provider,
                "spend": float(row.spend or 0),
                "roas": float(row.roas or 0),
                "days_active": int(row.days_active or 0),
            })

        logger.info(f"Retrieved {len(ads)} ads from BigQuery")
        return ads


# Singleton BigQuery connector
_bq_connector: Optional[BigQueryConnector] = None


def get_bq_connector() -> Optional[BigQueryConnector]:
    """Get or create BigQuery connector singleton."""
    global _bq_connector
    if _bq_connector is None and HAS_BIGQUERY:
        try:
            _bq_connector = BigQueryConnector()
        except Exception as e:
            logger.warning(f"Failed to initialize BigQuery connector: {e}")
    return _bq_connector


async def get_ad_data(
    tenant: Literal["tl", "wh"] = "tl",
    days: int = 30,
    use_fixture: bool = True
) -> Dict[str, Any]:
    """
    Retrieve ad performance data for analysis.

    Args:
        tenant: Tenant identifier ("tl" for ThirdLove, "wh" for WhisperingHomes)
        days: Number of days of data to retrieve (default 30)
        use_fixture: If True, return fixture data; if False, query BigQuery

    Returns:
        Dict with account_avg_roas and list of ads with spend, roas, days_active
    """
    if use_fixture:
        return _load_fixture_data(tenant)

    return await get_ad_data_from_bigquery(tenant, days)


async def get_ad_data_from_bigquery(
    tenant: Literal["tl", "wh"] = "tl",
    days: int = 30
) -> Dict[str, Any]:
    """
    Retrieve ad performance data from BigQuery.

    Args:
        tenant: Tenant identifier
        days: Number of days of data

    Returns:
        Dict with account_avg_roas and list of ads
    """
    connector = get_bq_connector()

    if connector is None:
        logger.warning("BigQuery not available, falling back to fixtures")
        return _load_fixture_data(tenant)

    try:
        # Get account average ROAS
        account_data = connector.get_account_avg_roas(tenant, days)

        # Get ad-level performance
        ads = connector.get_ad_performance(tenant, days)

        return {
            "account_avg_roas": account_data["weighted_avg_roas"],
            "total_spend": account_data["total_spend"],
            "date_range": {
                "start": account_data.get("start_date"),
                "end": account_data.get("end_date"),
                "days": days,
            },
            "ads": ads,
            "source": "bigquery",
        }

    except Exception as e:
        logger.error(f"BigQuery query failed: {e}, falling back to fixtures")
        return _load_fixture_data(tenant)


def _load_fixture_data(tenant: str) -> Dict[str, Any]:
    """Load fixture data from JSON file."""
    fixture_file = FIXTURES_DIR / "thirdlove_ads.json"

    if not fixture_file.exists():
        raise FileNotFoundError(f"Fixture file not found: {fixture_file}")

    with open(fixture_file, "r") as f:
        data = json.load(f)

    # Return data without _expected fields (those are for testing)
    ads = []
    for ad in data.get("ads", []):
        ads.append({
            "ad_name": ad["ad_name"],
            "ad_provider": ad["ad_provider"],
            "spend": ad["spend"],
            "roas": ad["roas"],
            "days_active": ad["days_active"],
        })

    return {
        "account_avg_roas": data["account_avg_roas"],
        "total_spend": data.get("total_spend"),
        "date_range": data.get("date_range"),
        "ads": ads,
    }


def get_fixture_with_expected() -> Dict[str, Any]:
    """Load fixture data including _expected fields for testing."""
    fixture_file = FIXTURES_DIR / "thirdlove_ads.json"

    with open(fixture_file, "r") as f:
        return json.load(f)


# Create FunctionTool for ADK agent (if available)
if HAS_ADK:
    get_ad_data_tool = FunctionTool(func=get_ad_data)
else:
    get_ad_data_tool = None  # ADK not installed
