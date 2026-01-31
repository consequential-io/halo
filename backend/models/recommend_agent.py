"""
Recommend Agent - Budget and Creative Recommendations for Ad Spend.

This agent takes analysis results (anomalies) and generates actionable recommendations
for scaling winners, cutting losers, and refreshing creatives.

Supports optional LLM-enhanced reasoning while keeping rule-based decisions.
"""

from typing import Any

from config.settings import settings
from helpers.reasoning_enricher import ReasoningEnricher


RECOMMEND_AGENT_PROMPT = """
You are a recommendation agent. Based on the analysis of ad anomalies, generate actionable recommendations.

## Recommendation Types

1. **SCALE**: For high-performing ads (high ROAS, low CPA)
   - Increase budget by 30-100%
   - Estimate additional revenue potential

2. **REDUCE**: For underperforming ads (high CPA, low ROAS)
   - Reduce budget by 50-75%
   - Calculate waste prevention

3. **PAUSE**: For severely underperforming ads
   - Stop spend immediately
   - Calculate total waste prevention

4. **REFRESH_CREATIVE**: For creative fatigue
   - Flag ads with single creative variant
   - Suggest A/B testing

## Output Format
For each recommendation:
- action: 'scale' | 'reduce' | 'pause' | 'refresh_creative'
- ad_name: which ad
- current_spend: current spend level
- recommended_change: dollar or percentage
- reasoning: why this recommendation
- estimated_impact: $ impact (positive = savings/revenue, negative = cost)
- priority: 'critical' | 'high' | 'medium' | 'low'
- confidence: 0.0-1.0

## Important
- Prioritize by estimated impact
- Be conservative with scale recommendations (require strong evidence)
- Be aggressive with pause recommendations (cut losses fast)
- Always explain the reasoning
"""


class RecommendAgentModel:
    """
    Recommend Agent for generating budget and creative recommendations.

    Takes analysis results (anomalies + RCA) and produces actionable recommendations.
    """

    def __init__(self, enable_llm_reasoning: bool | None = None):
        self.name = "recommend_agent"
        # Use settings default if not specified
        if enable_llm_reasoning is None:
            enable_llm_reasoning = settings.enable_llm_reasoning
        self.enable_llm_reasoning = enable_llm_reasoning
        self.reasoning_enricher = ReasoningEnricher(enable_llm=enable_llm_reasoning)
        # Recommendation thresholds
        self.thresholds = {
            "scale": {
                "min_roas": 3.0,          # Minimum ROAS to recommend scaling
                "max_cpa_zscore": 0.5,    # Maximum z_cpa for scaling
                "min_spend": 100,         # Minimum spend to consider
            },
            "reduce": {
                "min_cpa_zscore": 1.5,    # z_cpa above this = reduce
                "max_roas": 1.5,          # ROAS below this = reduce
            },
            "pause": {
                "min_cpa_zscore": 2.5,    # z_cpa above this = pause
                "max_roas": 0.5,          # ROAS below this = pause
            },
            "refresh_creative": {
                "max_creative_variants": 1,  # Single creative = refresh
                "min_days_active": 14,       # Old enough to be fatigued
            },
        }

    def generate_recommendations(
        self,
        analysis_results: dict[str, Any],
        all_ads: list[dict] | None = None
    ) -> dict[str, Any]:
        """
        Generate recommendations based on analysis results.

        Args:
            analysis_results: Output from AnalyzeAgentModel.run_analysis()
            all_ads: Optional full ads list for finding scaling opportunities

        Returns:
            Recommendations with actions, reasoning, and estimated impact
        """
        recommendations = []
        total_potential_savings = 0
        total_potential_revenue = 0

        # Process anomalies from analysis
        detailed_anomalies = analysis_results.get("detailed_anomalies", [])

        for anomaly_data in detailed_anomalies:
            anomaly_type = anomaly_data.get("type")
            anomaly = anomaly_data.get("anomaly", {})
            rca = anomaly_data.get("rca", {})
            ad = anomaly.get("ad", {})

            if anomaly_type == "high_cpa":
                rec = self._recommend_for_high_cpa(ad, anomaly, rca)
                if rec:
                    recommendations.append(rec)
                    if rec["action"] in ["reduce", "pause"]:
                        total_potential_savings += abs(rec.get("estimated_impact", 0))

            elif anomaly_type == "low_roas":
                rec = self._recommend_for_low_roas(ad, anomaly, rca)
                if rec:
                    recommendations.append(rec)
                    if rec["action"] in ["reduce", "pause"]:
                        total_potential_savings += abs(rec.get("estimated_impact", 0))

        # Find scaling opportunities from all ads (if provided)
        if all_ads:
            scale_recs = self._find_scaling_opportunities(all_ads, detailed_anomalies)
            for rec in scale_recs:
                recommendations.append(rec)
                if rec["action"] == "scale":
                    total_potential_revenue += rec.get("estimated_impact", 0)

        # Find creative refresh opportunities
        if all_ads:
            refresh_recs = self._find_creative_refresh_opportunities(all_ads)
            recommendations.extend(refresh_recs)

        # Sort by priority and impact
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(
            key=lambda x: (
                priority_order.get(x.get("priority", "low"), 3),
                -abs(x.get("estimated_impact", 0))
            )
        )

        return {
            "recommendations": recommendations,
            "summary": {
                "total_recommendations": len(recommendations),
                "by_action": self._count_by_action(recommendations),
                "by_priority": self._count_by_priority(recommendations),
                "total_potential_savings": round(total_potential_savings, 2),
                "total_potential_revenue": round(total_potential_revenue, 2),
                "net_impact": round(total_potential_savings + total_potential_revenue, 2),
            },
            "analysis_context": {
                "total_anomalies_processed": len(detailed_anomalies),
                "total_ads_reviewed": len(all_ads) if all_ads else 0,
            },
        }

    async def generate_recommendations_async(
        self,
        analysis_results: dict[str, Any],
        all_ads: list[dict] | None = None
    ) -> dict[str, Any]:
        """
        Generate recommendations with optional LLM-enhanced reasoning.

        This async version enriches the reasoning field using an LLM while
        keeping all rule-based decisions unchanged.

        Args:
            analysis_results: Output from AnalyzeAgentModel.run_analysis()
            all_ads: Optional full ads list for finding scaling opportunities

        Returns:
            Recommendations with enriched reasoning (or template fallback)
        """
        # Get base recommendations using rule-based logic
        result = self.generate_recommendations(analysis_results, all_ads)

        # Enrich reasoning with LLM if enabled
        if self.enable_llm_reasoning and result.get("recommendations"):
            result["recommendations"] = await self.reasoning_enricher.enrich_batch(
                result["recommendations"]
            )

        return result

    def _recommend_for_high_cpa(
        self,
        ad: dict,
        anomaly: dict,
        rca: dict
    ) -> dict | None:
        """Generate recommendation for high CPA anomaly."""
        spend = ad.get("Spend", 0) or 0
        cpa = ad.get("CPA", 0) or 0
        z_score = anomaly.get("z_score", 0)
        severity = anomaly.get("severity", "mild")
        ad_name = ad.get("ad_name") or ad.get("AD_NAME", "Unknown")

        # Determine action based on severity
        if severity == "extreme" or z_score >= self.thresholds["pause"]["min_cpa_zscore"]:
            action = "pause"
            change_pct = 100
            priority = "critical"
        elif severity == "significant" or z_score >= self.thresholds["reduce"]["min_cpa_zscore"]:
            action = "reduce"
            change_pct = 50
            priority = "high"
        else:
            action = "reduce"
            change_pct = 25
            priority = "medium"

        # Calculate impact (savings from reducing/pausing)
        estimated_savings = spend * (change_pct / 100)

        # Build reasoning from RCA
        root_causes = rca.get("root_causes", [])
        reasoning_parts = [f"CPA z-score of {z_score:.2f} indicates cost inefficiency"]
        for rc in root_causes[:2]:
            if rc.get("impact") in ["high", "medium"]:
                reasoning_parts.append(rc.get("finding", "")[:60])

        return {
            "action": action,
            "ad_name": ad_name[:50],
            "ad_id": ad.get("ad_id"),
            "ad_provider": ad.get("ad_provider"),
            "current_spend": round(spend, 2),
            "current_cpa": round(cpa, 2),
            "z_score": round(z_score, 2),
            "recommended_change": f"-{change_pct}%",
            "reasoning": ". ".join(reasoning_parts),
            "estimated_impact": round(estimated_savings, 2),
            "priority": priority,
            "confidence": min(0.9, 0.5 + abs(z_score) * 0.15),
            "root_causes": [rc["factor"] for rc in root_causes[:3]],
        }

    def _recommend_for_low_roas(
        self,
        ad: dict,
        anomaly: dict,
        rca: dict
    ) -> dict | None:
        """Generate recommendation for low ROAS anomaly."""
        spend = ad.get("Spend", 0) or 0
        roas = ad.get("ROAS", 0) or 0
        z_score = anomaly.get("z_score", 0)
        severity = anomaly.get("severity", "mild")
        ad_name = ad.get("ad_name") or ad.get("AD_NAME", "Unknown")

        # Determine action based on ROAS level
        if roas < self.thresholds["pause"]["max_roas"]:
            action = "pause"
            change_pct = 100
            priority = "critical"
        elif roas < self.thresholds["reduce"]["max_roas"]:
            action = "reduce"
            change_pct = 50
            priority = "high"
        else:
            action = "reduce"
            change_pct = 25
            priority = "medium"

        # Calculate impact
        estimated_savings = spend * (change_pct / 100)

        # Build reasoning
        root_causes = rca.get("root_causes", [])
        reasoning_parts = [f"ROAS of {roas:.2f} is below profitability threshold"]
        for rc in root_causes[:2]:
            if rc.get("impact") in ["high", "medium"]:
                reasoning_parts.append(rc.get("finding", "")[:60])

        return {
            "action": action,
            "ad_name": ad_name[:50],
            "ad_id": ad.get("ad_id"),
            "ad_provider": ad.get("ad_provider"),
            "current_spend": round(spend, 2),
            "current_roas": round(roas, 2),
            "z_score": round(z_score, 2),
            "recommended_change": f"-{change_pct}%",
            "reasoning": ". ".join(reasoning_parts),
            "estimated_impact": round(estimated_savings, 2),
            "priority": priority,
            "confidence": min(0.9, 0.5 + abs(z_score) * 0.15),
            "root_causes": [rc["factor"] for rc in root_causes[:3]],
        }

    def _find_scaling_opportunities(
        self,
        all_ads: list[dict],
        anomalies: list[dict]
    ) -> list[dict]:
        """Find ads that should be scaled up."""
        recommendations = []

        # Get IDs of anomalous ads to exclude
        anomaly_ids = set()
        for a in anomalies:
            ad_id = a.get("anomaly", {}).get("ad", {}).get("ad_id")
            if ad_id:
                anomaly_ids.add(ad_id)

        for ad in all_ads:
            ad_id = ad.get("ad_id")
            if ad_id in anomaly_ids:
                continue

            spend = ad.get("Spend", 0) or 0
            roas = ad.get("ROAS", 0) or 0
            cpa = ad.get("CPA", 0) or 0
            z_cpa = ad.get("z_cpa", 0) or 0

            # Check if this is a scaling candidate
            if (spend >= self.thresholds["scale"]["min_spend"] and
                roas >= self.thresholds["scale"]["min_roas"] and
                z_cpa <= self.thresholds["scale"]["max_cpa_zscore"]):

                ad_name = ad.get("ad_name") or ad.get("AD_NAME") or "Unknown"

                # Calculate scaling recommendation
                scale_pct = min(100, int((roas / 3.0) * 30))  # 30-100% based on ROAS
                additional_spend = spend * (scale_pct / 100)
                estimated_revenue = additional_spend * roas

                recommendations.append({
                    "action": "scale",
                    "ad_name": ad_name[:50],
                    "ad_id": ad_id,
                    "ad_provider": ad.get("ad_provider"),
                    "current_spend": round(spend, 2),
                    "current_roas": round(roas, 2),
                    "current_cpa": round(cpa, 2),
                    "recommended_change": f"+{scale_pct}%",
                    "reasoning": f"Strong ROAS of {roas:.2f}x with efficient CPA suggests scaling potential",
                    "estimated_impact": round(estimated_revenue, 2),
                    "priority": "high" if roas >= 5.0 else "medium",
                    "confidence": min(0.85, 0.4 + (roas / 10)),
                })

        # Return top 5 scaling opportunities
        recommendations.sort(key=lambda x: -x.get("estimated_impact", 0))
        return recommendations[:5]

    def _find_creative_refresh_opportunities(
        self,
        all_ads: list[dict]
    ) -> list[dict]:
        """Find ads that need creative refresh."""
        recommendations = []

        for ad in all_ads:
            creative_variants = ad.get("creative_variants", 1) or 1
            days_active = ad.get("days_active", 0) or 0
            creative_status = ad.get("creative_status", "")
            spend = ad.get("Spend", 0) or 0

            # Check for creative fatigue indicators
            needs_refresh = False
            reasons = []

            if creative_variants <= self.thresholds["refresh_creative"]["max_creative_variants"]:
                needs_refresh = True
                reasons.append("Single creative variant (no A/B testing)")

            if creative_status == "fatigued":
                needs_refresh = True
                reasons.append("Creative marked as fatigued")

            if days_active >= self.thresholds["refresh_creative"]["min_days_active"] and creative_variants == 1:
                needs_refresh = True
                reasons.append(f"Running single creative for {days_active} days")

            if needs_refresh and spend >= 100:
                ad_name = ad.get("ad_name") or ad.get("AD_NAME") or "Unknown"

                recommendations.append({
                    "action": "refresh_creative",
                    "ad_name": ad_name[:50],
                    "ad_id": ad.get("ad_id"),
                    "ad_provider": ad.get("ad_provider"),
                    "current_spend": round(spend, 2),
                    "creative_variants": creative_variants,
                    "days_active": days_active,
                    "recommended_change": "Add 2-3 creative variants",
                    "reasoning": ". ".join(reasons),
                    "estimated_impact": round(spend * 0.15, 2),  # Estimate 15% improvement
                    "priority": "medium",
                    "confidence": 0.7,
                })

        # Return top 5 refresh opportunities by spend
        recommendations.sort(key=lambda x: -x.get("current_spend", 0))
        return recommendations[:5]

    def _count_by_action(self, recommendations: list[dict]) -> dict:
        """Count recommendations by action type."""
        counts = {"scale": 0, "reduce": 0, "pause": 0, "refresh_creative": 0}
        for rec in recommendations:
            action = rec.get("action", "")
            if action in counts:
                counts[action] += 1
        return counts

    def _count_by_priority(self, recommendations: list[dict]) -> dict:
        """Count recommendations by priority."""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for rec in recommendations:
            priority = rec.get("priority", "low")
            if priority in counts:
                counts[priority] += 1
        return counts
