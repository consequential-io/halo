"""RCA diagnostic check tools for the RCA Agent."""

import logging
from typing import Dict, Any, Literal, Optional
from datetime import datetime, timedelta

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
# Use SAFE_CAST to handle nulls/empty strings gracefully
CAST_SPEND = "SAFE_CAST(spend AS FLOAT64)"
CAST_ROAS = "SAFE_CAST(ROAS AS FLOAT64)"
CAST_CTR = "SAFE_CAST(CTR AS FLOAT64)"
CAST_CPM = "SAFE_CAST(CPM AS FLOAT64)"
CAST_CPA = "SAFE_CAST(CPA AS FLOAT64)"
CAST_IMPRESSIONS = "SAFE_CAST(total_ad_impression AS INT64)"
CAST_ORDERS = "SAFE_CAST(total_orders AS INT64)"
CAST_ATC = "SAFE_CAST(addtocarts AS INT64)"
CAST_CHECKOUT = "SAFE_CAST(initiatecheckout AS INT64)"
CAST_DAILY_BUDGET = "SAFE_CAST(AD_GROUP_DAILY_BUDGET AS FLOAT64)"
CAST_CAMPAIGN_CAP = "SAFE_CAST(CAMPAIGN_SPEND_CAP AS FLOAT64)"


async def get_metric_timeline(
    days: int = 30,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """
    Get daily timeline of key metrics for the account.

    Returns daily CPM, ROAS, CPA trends to show when issues started.
    """
    engine = RCACheckEngine(tenant)

    query = f"""
    SELECT
        DATE(TIMESTAMP(datetime_IST)) as date,
        AVG({CAST_CPM}) as avg_cpm,
        SAFE_DIVIDE(SUM({CAST_ROAS} * {CAST_SPEND}), SUM({CAST_SPEND})) as weighted_roas,
        AVG({CAST_CPA}) as avg_cpa,
        SUM({CAST_SPEND}) as total_spend,
        COUNT(DISTINCT AD_NAME) as active_ads
    FROM `{engine.table}`
    WHERE data_source = 'Ad Providers'
      AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
      AND {CAST_SPEND} > 0
      AND CAMPAIGN_STATUS = 'ACTIVE'
    GROUP BY DATE(TIMESTAMP(datetime_IST))
    ORDER BY date
    """

    results = engine._run_query(query)

    if not results:
        return {"error": "No data found", "timeline": []}

    timeline = []
    for row in results:
        timeline.append({
            "date": str(row.get("date")),
            "cpm": round(float(row.get("avg_cpm") or 0), 2),
            "roas": round(float(row.get("weighted_roas") or 0), 2),
            "cpa": round(float(row.get("avg_cpa") or 0), 2),
            "spend": round(float(row.get("total_spend") or 0), 0),
            "active_ads": int(row.get("active_ads") or 0),
        })

    # Calculate week-over-week changes
    if len(timeline) >= 14:
        last_week = timeline[-7:]
        prev_week = timeline[-14:-7]

        avg_cpm_last = sum(d["cpm"] for d in last_week) / 7
        avg_cpm_prev = sum(d["cpm"] for d in prev_week) / 7
        cpm_change = ((avg_cpm_last - avg_cpm_prev) / avg_cpm_prev * 100) if avg_cpm_prev > 0 else 0

        avg_roas_last = sum(d["roas"] for d in last_week) / 7
        avg_roas_prev = sum(d["roas"] for d in prev_week) / 7
        roas_change = ((avg_roas_last - avg_roas_prev) / avg_roas_prev * 100) if avg_roas_prev > 0 else 0
    else:
        cpm_change = 0
        roas_change = 0
        avg_cpm_last = 0
        avg_cpm_prev = 0
        avg_roas_last = 0
        avg_roas_prev = 0

    return {
        "timeline": timeline,
        "period_days": days,
        "summary": {
            "cpm_wow_change": round(cpm_change, 1),
            "roas_wow_change": round(roas_change, 1),
            "avg_cpm_last_week": round(avg_cpm_last, 2),
            "avg_cpm_prev_week": round(avg_cpm_prev, 2),
            "avg_roas_last_week": round(avg_roas_last, 2),
            "avg_roas_prev_week": round(avg_roas_prev, 2),
        }
    }


class RCACheckEngine:
    """Engine for running RCA diagnostic checks against BigQuery."""

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

    def _run_query(self, query: str) -> list:
        """Execute a BigQuery query and return results as list of dicts."""
        if not self.client:
            logger.warning("BigQuery not available")
            return []

        try:
            result = self.client.query(query).result()
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []


async def check_budget_exhaustion(
    ad_name: str,
    days: int = 7,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """
    Check if ad budget is exhausted or nearly exhausted.

    Args:
        ad_name: Name of the ad to check
        days: Number of days to analyze
        tenant: Tenant identifier

    Returns:
        Dict with exhaustion status and details
    """
    engine = RCACheckEngine(tenant)

    query = f"""
    SELECT
        AD_NAME,
        SUM({CAST_SPEND}) as total_spend,
        MAX({CAST_DAILY_BUDGET}) as daily_budget,
        MAX({CAST_CAMPAIGN_CAP}) as campaign_cap,
        COUNT(DISTINCT DATE(TIMESTAMP(datetime_IST))) as days_with_spend,
        AVG({CAST_SPEND}) as avg_daily_spend
    FROM `{engine.table}`
    WHERE AD_NAME = '{ad_name}'
      AND data_source = 'Ad Providers'
      AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
      AND {CAST_SPEND} > 0
    GROUP BY AD_NAME
    """

    results = engine._run_query(query)

    if not results:
        return {
            "exhausted": False,
            "error": "No data found for this ad",
            "ad_name": ad_name
        }

    row = results[0]
    daily_budget = float(row.get('daily_budget') or 0)
    campaign_cap = float(row.get('campaign_cap') or 0)
    avg_daily_spend = float(row.get('avg_daily_spend') or 0)
    total_spend = float(row.get('total_spend') or 0)

    # Check if hitting daily budget
    budget_utilization = avg_daily_spend / daily_budget if daily_budget > 0 else 0

    # Check if hitting campaign cap
    cap_utilization = total_spend / campaign_cap if campaign_cap > 0 else 0

    exhausted = budget_utilization > 0.95 or cap_utilization > 0.95

    return {
        "exhausted": exhausted,
        "budget_utilization": round(budget_utilization * 100, 1),
        "cap_utilization": round(cap_utilization * 100, 1),
        "daily_budget": daily_budget,
        "campaign_cap": campaign_cap,
        "avg_daily_spend": round(avg_daily_spend, 2),
        "interpretation": (
            f"Budget {budget_utilization*100:.0f}% utilized. "
            f"{'EXHAUSTED - not spending full potential' if exhausted else 'Normal utilization'}"
        )
    }


async def check_creative_fatigue(
    ad_name: str,
    days: int = 14,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """
    Check if creative is fatigued by analyzing CTR trend.

    Args:
        ad_name: Name of the ad to check
        days: Number of days to analyze
        tenant: Tenant identifier

    Returns:
        Dict with fatigue status and CTR trend
    """
    engine = RCACheckEngine(tenant)

    query = f"""
    WITH daily_metrics AS (
        SELECT
            DATE(TIMESTAMP(datetime_IST)) as date,
            SUM({CAST_IMPRESSIONS}) as impressions,
            AVG({CAST_CTR}) as ctr,
            SUM({CAST_SPEND}) as spend
        FROM `{engine.table}`
        WHERE AD_NAME = '{ad_name}'
          AND data_source = 'Ad Providers'
          AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
          AND {CAST_SPEND} > 0
        GROUP BY DATE(TIMESTAMP(datetime_IST))
        ORDER BY date
    ),
    first_half AS (
        SELECT AVG(ctr) as avg_ctr
        FROM daily_metrics
        WHERE date < DATE_SUB(CURRENT_DATE(), INTERVAL {days // 2} DAY)
    ),
    second_half AS (
        SELECT AVG(ctr) as avg_ctr
        FROM daily_metrics
        WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL {days // 2} DAY)
    )
    SELECT
        (SELECT COUNT(*) FROM daily_metrics) as days_running,
        (SELECT avg_ctr FROM first_half) as ctr_first_half,
        (SELECT avg_ctr FROM second_half) as ctr_second_half,
        (SELECT MIN(date) FROM daily_metrics) as first_date,
        (SELECT MAX(date) FROM daily_metrics) as last_date
    """

    results = engine._run_query(query)

    if not results:
        return {
            "fatigued": False,
            "error": "No data found for this ad",
            "ad_name": ad_name
        }

    row = results[0]
    ctr_first = float(row.get('ctr_first_half') or 0)
    ctr_second = float(row.get('ctr_second_half') or 0)
    days_running = int(row.get('days_running') or 0)

    # Calculate CTR trend
    ctr_change = ((ctr_second - ctr_first) / ctr_first * 100) if ctr_first > 0 else 0

    # Creative is fatigued if CTR dropped more than 15%
    fatigued = ctr_change < -15

    return {
        "fatigued": fatigued,
        "ctr_trend_pct": round(ctr_change, 1),
        "ctr_first_half": round(ctr_first, 4),
        "ctr_second_half": round(ctr_second, 4),
        "days_running": days_running,
        "interpretation": (
            f"CTR {'dropped' if ctr_change < 0 else 'increased'} {abs(ctr_change):.1f}% over {days_running} days. "
            f"{'FATIGUED - refresh creative' if fatigued else 'Creative still performing'}"
        )
    }


async def check_cpm_spike(
    ad_name: str,
    days: int = 7,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """
    Check if CPM has spiked (auction competition increased).

    Args:
        ad_name: Name of the ad to check
        days: Number of days to analyze
        tenant: Tenant identifier

    Returns:
        Dict with CPM spike status and details
    """
    engine = RCACheckEngine(tenant)

    query = f"""
    WITH recent AS (
        SELECT AVG({CAST_CPM}) as avg_cpm
        FROM `{engine.table}`
        WHERE AD_NAME = '{ad_name}'
          AND data_source = 'Ad Providers'
          AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)
          AND {CAST_SPEND} > 0
          AND {CAST_CPM} > 0
    ),
    baseline AS (
        SELECT AVG({CAST_CPM}) as avg_cpm
        FROM `{engine.table}`
        WHERE AD_NAME = '{ad_name}'
          AND data_source = 'Ad Providers'
          AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
          AND TIMESTAMP(datetime_IST) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)
          AND {CAST_SPEND} > 0
          AND {CAST_CPM} > 0
    )
    SELECT
        (SELECT avg_cpm FROM recent) as current_cpm,
        (SELECT avg_cpm FROM baseline) as baseline_cpm
    """

    results = engine._run_query(query)

    if not results:
        return {
            "spiked": False,
            "error": "No data found for this ad",
            "ad_name": ad_name
        }

    row = results[0]
    current_cpm = float(row.get('current_cpm') or 0)
    baseline_cpm = float(row.get('baseline_cpm') or 0)

    # Calculate CPM change
    cpm_change = ((current_cpm - baseline_cpm) / baseline_cpm * 100) if baseline_cpm > 0 else 0

    # CPM spiked if increased more than 25%
    spiked = cpm_change > 25

    return {
        "spiked": spiked,
        "cpm_change_pct": round(cpm_change, 1),
        "current_cpm": round(current_cpm, 2),
        "baseline_cpm": round(baseline_cpm, 2),
        "interpretation": (
            f"CPM {'increased' if cpm_change > 0 else 'decreased'} {abs(cpm_change):.1f}% "
            f"(${baseline_cpm:.2f} → ${current_cpm:.2f}). "
            f"{'SPIKED - auction competition up' if spiked else 'CPM normal'}"
        )
    }


async def check_landing_page(
    ad_name: str,
    days: int = 7,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """
    Check if there's a landing page / conversion funnel issue.
    CTR stable but conversions dropped = landing page problem.

    Args:
        ad_name: Name of the ad to check
        days: Number of days to analyze
        tenant: Tenant identifier

    Returns:
        Dict with landing page issue status and funnel metrics
    """
    engine = RCACheckEngine(tenant)

    query = f"""
    WITH recent AS (
        SELECT
            AVG({CAST_CTR}) as ctr,
            SAFE_DIVIDE(SUM({CAST_ATC}), SUM({CAST_IMPRESSIONS})) * 100 as atc_rate,
            SAFE_DIVIDE(SUM({CAST_CHECKOUT}), SUM({CAST_ATC})) * 100 as checkout_rate,
            SAFE_DIVIDE(SUM({CAST_ORDERS}), SUM({CAST_CHECKOUT})) * 100 as purchase_rate,
            SUM({CAST_ORDERS}) as orders
        FROM `{engine.table}`
        WHERE AD_NAME = '{ad_name}'
          AND data_source = 'Ad Providers'
          AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)
          AND {CAST_SPEND} > 0
    ),
    baseline AS (
        SELECT
            AVG({CAST_CTR}) as ctr,
            SAFE_DIVIDE(SUM({CAST_ATC}), SUM({CAST_IMPRESSIONS})) * 100 as atc_rate,
            SAFE_DIVIDE(SUM({CAST_CHECKOUT}), SUM({CAST_ATC})) * 100 as checkout_rate,
            SAFE_DIVIDE(SUM({CAST_ORDERS}), SUM({CAST_CHECKOUT})) * 100 as purchase_rate,
            SUM({CAST_ORDERS}) as orders
        FROM `{engine.table}`
        WHERE AD_NAME = '{ad_name}'
          AND data_source = 'Ad Providers'
          AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
          AND TIMESTAMP(datetime_IST) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)
          AND {CAST_SPEND} > 0
    )
    SELECT
        (SELECT ctr FROM recent) as current_ctr,
        (SELECT ctr FROM baseline) as baseline_ctr,
        (SELECT atc_rate FROM recent) as current_atc_rate,
        (SELECT atc_rate FROM baseline) as baseline_atc_rate,
        (SELECT checkout_rate FROM recent) as current_checkout_rate,
        (SELECT checkout_rate FROM baseline) as baseline_checkout_rate,
        (SELECT purchase_rate FROM recent) as current_purchase_rate,
        (SELECT purchase_rate FROM baseline) as baseline_purchase_rate
    """

    results = engine._run_query(query)

    if not results:
        return {
            "issue": False,
            "error": "No data found for this ad",
            "ad_name": ad_name
        }

    row = results[0]

    current_ctr = float(row.get('current_ctr') or 0)
    baseline_ctr = float(row.get('baseline_ctr') or 0)
    current_atc = float(row.get('current_atc_rate') or 0)
    baseline_atc = float(row.get('baseline_atc_rate') or 0)
    current_checkout = float(row.get('current_checkout_rate') or 0)
    baseline_checkout = float(row.get('baseline_checkout_rate') or 0)

    # Calculate changes
    ctr_change = ((current_ctr - baseline_ctr) / baseline_ctr * 100) if baseline_ctr > 0 else 0
    atc_change = ((current_atc - baseline_atc) / baseline_atc * 100) if baseline_atc > 0 else 0
    checkout_change = ((current_checkout - baseline_checkout) / baseline_checkout * 100) if baseline_checkout > 0 else 0

    # Landing page issue: CTR stable (within 10%) but conversion metrics dropped >30%
    ctr_stable = abs(ctr_change) < 10
    conversion_dropped = atc_change < -30 or checkout_change < -30
    issue = ctr_stable and conversion_dropped

    return {
        "issue": issue,
        "ctr_change_pct": round(ctr_change, 1),
        "atc_rate_change_pct": round(atc_change, 1),
        "checkout_rate_change_pct": round(checkout_change, 1),
        "current_atc_rate": round(current_atc, 2),
        "current_checkout_rate": round(current_checkout, 2),
        "interpretation": (
            f"CTR {'stable' if ctr_stable else 'changed'} ({ctr_change:+.1f}%), "
            f"Add-to-cart {atc_change:+.1f}%, Checkout {checkout_change:+.1f}%. "
            f"{'LANDING PAGE ISSUE - CTR ok but conversions down' if issue else 'Funnel looks normal'}"
        )
    }


async def check_tracking(
    ad_name: str,
    days: int = 3,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """
    Check if conversion tracking is broken.
    Clicks happening but zero conversions = tracking issue.

    Args:
        ad_name: Name of the ad to check
        days: Number of days to analyze
        tenant: Tenant identifier

    Returns:
        Dict with tracking status and details
    """
    engine = RCACheckEngine(tenant)

    query = f"""
    SELECT
        SUM({CAST_IMPRESSIONS}) as impressions,
        AVG({CAST_CTR}) as avg_ctr,
        SUM({CAST_IMPRESSIONS}) * AVG({CAST_CTR}) / 100 as estimated_clicks,
        SUM({CAST_ORDERS}) as orders,
        SUM({CAST_ATC}) as add_to_carts,
        MAX(TIMESTAMP(datetime_IST)) as last_activity
    FROM `{engine.table}`
    WHERE AD_NAME = '{ad_name}'
      AND data_source = 'Ad Providers'
      AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days} DAY)
      AND {CAST_SPEND} > 0
    """

    results = engine._run_query(query)

    if not results:
        return {
            "broken": False,
            "error": "No data found for this ad",
            "ad_name": ad_name
        }

    row = results[0]
    impressions = int(row.get('impressions') or 0)
    estimated_clicks = float(row.get('estimated_clicks') or 0)
    orders = int(row.get('orders') or 0)
    add_to_carts = int(row.get('add_to_carts') or 0)

    # Tracking is broken if we have clicks but zero orders AND zero add-to-carts for 48+ hours
    has_traffic = estimated_clicks > 100  # Meaningful traffic
    no_conversions = orders == 0 and add_to_carts == 0
    broken = has_traffic and no_conversions

    return {
        "broken": broken,
        "impressions": impressions,
        "estimated_clicks": int(estimated_clicks),
        "orders": orders,
        "add_to_carts": add_to_carts,
        "interpretation": (
            f"{int(estimated_clicks)} clicks, {orders} orders, {add_to_carts} add-to-carts in last {days} days. "
            f"{'TRACKING BROKEN - clicks but no conversions' if broken else 'Tracking appears functional'}"
        )
    }


async def check_seasonality(
    ad_name: str,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """
    Check if performance drop is due to seasonality.
    Compare to 7 days ago and 30 days ago.

    Args:
        ad_name: Name of the ad to check
        tenant: Tenant identifier

    Returns:
        Dict with seasonality analysis
    """
    engine = RCACheckEngine(tenant)

    # Check performance vs 7 days ago and 30 days ago
    query = f"""
    WITH current_period AS (
        SELECT
            SAFE_DIVIDE(SUM({CAST_ROAS} * {CAST_SPEND}), SUM({CAST_SPEND})) as roas,
            SUM({CAST_SPEND}) as spend,
            AVG({CAST_CTR}) as ctr
        FROM `{engine.table}`
        WHERE AD_NAME = '{ad_name}'
          AND data_source = 'Ad Providers'
          AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)
          AND {CAST_SPEND} > 0
    ),
    week_ago AS (
        SELECT
            SAFE_DIVIDE(SUM({CAST_ROAS} * {CAST_SPEND}), SUM({CAST_SPEND})) as roas,
            SUM({CAST_SPEND}) as spend,
            AVG({CAST_CTR}) as ctr
        FROM `{engine.table}`
        WHERE AD_NAME = '{ad_name}'
          AND data_source = 'Ad Providers'
          AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 DAY)
          AND TIMESTAMP(datetime_IST) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
          AND {CAST_SPEND} > 0
    ),
    month_ago AS (
        SELECT
            SAFE_DIVIDE(SUM({CAST_ROAS} * {CAST_SPEND}), SUM({CAST_SPEND})) as roas,
            SUM({CAST_SPEND}) as spend,
            AVG({CAST_CTR}) as ctr
        FROM `{engine.table}`
        WHERE AD_NAME = '{ad_name}'
          AND data_source = 'Ad Providers'
          AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 33 DAY)
          AND TIMESTAMP(datetime_IST) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
          AND {CAST_SPEND} > 0
    ),
    -- Check if ALL channels are affected (suggests external/seasonal factor)
    all_channels_current AS (
        SELECT SAFE_DIVIDE(SUM({CAST_ROAS} * {CAST_SPEND}), SUM({CAST_SPEND})) as roas
        FROM `{engine.table}`
        WHERE data_source = 'Ad Providers'
          AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)
          AND {CAST_SPEND} > 0
    ),
    all_channels_week_ago AS (
        SELECT SAFE_DIVIDE(SUM({CAST_ROAS} * {CAST_SPEND}), SUM({CAST_SPEND})) as roas
        FROM `{engine.table}`
        WHERE data_source = 'Ad Providers'
          AND TIMESTAMP(datetime_IST) >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 10 DAY)
          AND TIMESTAMP(datetime_IST) < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
          AND {CAST_SPEND} > 0
    )
    SELECT
        (SELECT roas FROM current_period) as current_roas,
        (SELECT roas FROM week_ago) as roas_7d_ago,
        (SELECT roas FROM month_ago) as roas_30d_ago,
        (SELECT roas FROM all_channels_current) as all_channels_current,
        (SELECT roas FROM all_channels_week_ago) as all_channels_7d_ago
    """

    results = engine._run_query(query)

    if not results:
        return {
            "seasonal": False,
            "error": "No data found for this ad",
            "ad_name": ad_name
        }

    row = results[0]
    current = float(row.get('current_roas') or 0)
    week_ago = float(row.get('roas_7d_ago') or 0)
    month_ago = float(row.get('roas_30d_ago') or 0)
    all_current = float(row.get('all_channels_current') or 0)
    all_week_ago = float(row.get('all_channels_7d_ago') or 0)

    # Calculate changes
    vs_7d = ((current - week_ago) / week_ago * 100) if week_ago > 0 else 0
    vs_30d = ((current - month_ago) / month_ago * 100) if month_ago > 0 else 0
    all_channels_change = ((all_current - all_week_ago) / all_week_ago * 100) if all_week_ago > 0 else 0

    # It's likely seasonal if ALL channels dropped similarly
    all_channels_affected = all_channels_change < -15

    return {
        "seasonal": all_channels_affected,
        "vs_7d_ago_pct": round(vs_7d, 1),
        "vs_30d_ago_pct": round(vs_30d, 1),
        "all_channels_change_pct": round(all_channels_change, 1),
        "all_channels_affected": all_channels_affected,
        "interpretation": (
            f"This ad: {vs_7d:+.1f}% vs 7d ago, {vs_30d:+.1f}% vs 30d ago. "
            f"All channels: {all_channels_change:+.1f}%. "
            f"{'SEASONAL - all channels affected similarly' if all_channels_affected else 'Not seasonal - issue specific to this ad'}"
        )
    }


# ============================================================================
# FUTURE CHECKS (Not yet implemented - need additional data)
# ============================================================================

async def check_bid_cap_too_low(
    ad_name: str,
    days: int = 7,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """
    🔮 FUTURE: Check if bid cap is too low (losing auctions).

    Needs: bid_cap from Ads API (not in BigQuery)
    """
    return {
        "implemented": False,
        "error": "This check requires bid_cap data from Ads API",
        "needed_data": ["bid_cap"],
        "ad_name": ad_name
    }


async def check_audience_exhaustion(
    ad_name: str,
    days: int = 7,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """
    🔮 FUTURE: Check if audience is exhausted (high frequency).

    Needs: frequency, reach, audience_size from Ads API
    """
    return {
        "implemented": False,
        "error": "This check requires frequency/reach data from Ads API",
        "needed_data": ["frequency", "reach", "audience_size"],
        "ad_name": ad_name
    }


async def check_recent_changes(
    ad_name: str,
    days: int = 2,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """
    🔮 FUTURE: Check for recent changes to the ad/campaign.

    Needs: Change logs from Ads API
    """
    return {
        "implemented": False,
        "error": "This check requires change logs from Ads API",
        "needed_data": ["ad_change_history", "campaign_change_history"],
        "ad_name": ad_name
    }
