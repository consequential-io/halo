"""
Analyze Agent - Anomaly Detection for Ad Spend.

This agent uses statistical anomaly detection to find ads with unusual performance,
then performs root cause analysis to explain why.
"""

from typing import Any

from helpers.tools import get_ad_data, detect_anomalies, get_ontology, run_rca


ANALYZE_AGENT_PROMPT = """
You are an ad spend analysis agent. Your goal is to find anomalies in ad performance data.

## Approach
1. First, fetch ad data using get_ad_data
2. Detect anomalies using detect_anomalies for key metrics:
   - CPA (high = wasteful spend) - use direction="high"
   - ROAS (low = poor return) - use direction="low"
   - Use z_cpa and z_roas for pre-computed z-scores from fixtures
3. Use get_ontology to understand which dimensions have most anomalies
4. For significant anomalies (severity="significant" or "extreme"), run deep RCA
5. Surface findings with actionable recommendations

## Metrics Priority
- z_cpa > 2.0: High cost per acquisition (waste)
- z_roas < -2.0: Low return on ad spend (poor performance)
- High spend + low ROAS: Maximum waste potential

## Output Format
For each anomaly found, explain:
- **What**: Which ad and what metric is anomalous
- **How much**: The deviation from baseline (z-score, actual vs baseline)
- **Why**: Root cause factors from RCA
- **Action**: What to do about it
- **Impact**: Estimated waste if anomaly continues

## Important
- Surface anomalies, don't classify into fixed buckets
- Focus on the most severe anomalies first
- Always run RCA on the top 3 anomalies
- Provide specific, actionable recommendations
"""


class AnalyzeAgentModel:
    """
    Analyze Agent for anomaly detection in ad spend data.

    This is a simplified version that can be used without the full ADK setup.
    For production, this would use google.adk.agents.LlmAgent.
    """

    def __init__(self):
        self.name = "analyze_agent"
        self.tools = {
            "get_ad_data": get_ad_data,
            "detect_anomalies": detect_anomalies,
            "get_ontology": get_ontology,
            "run_rca": run_rca,
        }

    def run_analysis(self, account_id: str = "tl", days: int = 30, source: str | None = None) -> dict[str, Any]:
        """
        Run full anomaly detection analysis on an account.

        This is a deterministic flow for testing. In production, the LLM
        would orchestrate tool calls based on the prompt.

        Args:
            account_id: Account to analyze ("tl" or "wh")
            days: Days of data to analyze
            source: Data source ("fixture" or "bq"), defaults to settings.data_source

        Returns:
            Analysis results with anomalies, ontology insights, and recommendations
        """
        # Step 1: Get ad data
        data = get_ad_data(account_id=account_id, days=days, source=source)
        if "error" in data:
            return {"error": data["error"]}

        ads = data["ads"]
        if not ads:
            return {"error": "No ads found"}

        # Step 2: Detect anomalies on key metrics
        # Use pre-computed z-scores from fixtures
        cpa_anomalies = detect_anomalies(
            ads, metric="z_cpa", threshold_sigma=2.0, direction="high"
        )
        roas_anomalies = detect_anomalies(
            ads, metric="z_roas", threshold_sigma=2.0, direction="low"
        )

        # Also check raw spend for high-spend anomalies
        spend_anomalies = detect_anomalies(
            ads, metric="Spend", threshold_sigma=2.0, direction="high"
        )

        # Step 3: Get ontology breakdown
        provider_breakdown = get_ontology(ads, group_by=["ad_provider"])
        store_breakdown = get_ontology(ads, group_by=["store"])
        type_breakdown = get_ontology(ads, group_by=["ad_type"])

        # Step 4: Run RCA on top anomalies
        all_anomalies = []

        for anomaly in cpa_anomalies.get("anomalies", [])[:3]:
            rca_result = run_rca(anomaly["ad"], ads, "CPA")
            all_anomalies.append({
                "type": "high_cpa",
                "anomaly": anomaly,
                "rca": rca_result,
            })

        for anomaly in roas_anomalies.get("anomalies", [])[:3]:
            # Avoid duplicates
            ad_id = anomaly["ad"].get("ad_id")
            if not any(a["anomaly"]["ad"].get("ad_id") == ad_id for a in all_anomalies):
                rca_result = run_rca(anomaly["ad"], ads, "ROAS")
                all_anomalies.append({
                    "type": "low_roas",
                    "anomaly": anomaly,
                    "rca": rca_result,
                })

        # Step 5: Calculate summary metrics
        total_anomaly_spend = sum(
            a["anomaly"]["ad"].get("Spend", 0) or 0 for a in all_anomalies
        )

        # Find worst provider
        worst_provider = None
        provider_anomaly_counts = {}
        for a in all_anomalies:
            provider = a["anomaly"]["ad"].get("ad_provider", "Unknown")
            provider_anomaly_counts[provider] = provider_anomaly_counts.get(provider, 0) + 1

        if provider_anomaly_counts:
            worst_provider = max(provider_anomaly_counts, key=provider_anomaly_counts.get)

        return {
            "account_id": account_id,
            "total_ads_analyzed": len(ads),
            "anomalies": {
                "high_cpa": {
                    "count": len(cpa_anomalies.get("anomalies", [])),
                    "baseline_stats": cpa_anomalies.get("baseline_stats", {}),
                },
                "low_roas": {
                    "count": len(roas_anomalies.get("anomalies", [])),
                    "baseline_stats": roas_anomalies.get("baseline_stats", {}),
                },
                "high_spend": {
                    "count": len(spend_anomalies.get("anomalies", [])),
                    "baseline_stats": spend_anomalies.get("baseline_stats", {}),
                },
            },
            "detailed_anomalies": all_anomalies,
            "ontology_insights": {
                "by_provider": provider_breakdown,
                "by_store": store_breakdown,
                "by_ad_type": type_breakdown,
            },
            "summary": {
                "total_anomalies": len(all_anomalies),
                "total_anomaly_spend": round(total_anomaly_spend, 2),
                "worst_provider": worst_provider,
                "provider_anomaly_counts": provider_anomaly_counts,
            },
        }
