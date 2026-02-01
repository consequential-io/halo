# AI Impact Statement

**Project:** Agatha - Ad Spend Optimization Agent
**Date:** February 2025
**Organization:** Consequential.io

---

## What the AI Does

Agatha is a multi-agent system that analyzes advertising performance data, detects spending anomalies, and generates optimization recommendations. Three specialized agents work sequentially: **Analyze** (classifies ad spend as good/bad/ok based on ROAS), **Recommend** (suggests budget adjustments with estimated impact), and **Execute** (applies approved changes via APIs).

## Models Used

**Primary:** Google Gemini 2.5 Pro via Google ADK (Agent Development Kit). Selected for superior structured data reasoning, long context window (1M tokens), and native tool-calling support. The model interprets performance patterns and generates human-readable recommendations with confidence scores.

## Data Provenance & Licenses

- **BigQuery data:** Proprietary ecommerce ad performance data from Out of the Blue clients, used with explicit permission for development and demonstration
- **Meta Marketing API:** Live data accessed via OAuth with user consent, subject to Meta Platform Terms of Service
- No training data is extracted; all inference is on production models

## Hallucination/Bias Mitigations

### Chain-of-Thought Grounding

The LLM must show its reasoning in a structured format that we validate against source data:

```json
{
  "chain_of_thought": {
    "data_extracted": {"spend": 212297, "roas": 29.58, "days": 287},
    "comparison": {"roas_ratio": "29.58 / 6.90 = 4.3×"},
    "qualification": {"spend_ok": true, "days_ok": true},
    "classification_logic": {"result": "GOOD", "reason": "ROAS 4.3× above average"}
  }
}
```

**Validation checks:**
- `data_extracted` values must match source input (±1% tolerance)
- `qualification` flags verified against actual thresholds (spend ≥ $1000, days ≥ 7)
- `classification_logic.result` must match stated classification
- If any check fails → retry with feedback OR fallback to rule-based classification

### Additional Mitigations

- **Rule-based fallbacks:** If LLM output fails validation, deterministic rules generate the classification
- **Source citations:** All recommendations include underlying data references with exact values
- **Relative benchmarks:** ROAS thresholds are relative to account averages, avoiding industry bias
- **Bad-only anomaly filtering:** RCA pipeline only flags negative business impacts (ROAS drops, CPA spikes), not statistical noise
- **Timeline visualization:** Shows historical trends so users can verify anomalies are real, not data artifacts
- **Confidence scoring:** Each recommendation tagged HIGH/MEDIUM/LOW based on data quality and pattern strength
- **Human-in-the-loop:** All execution actions require explicit user approval
- **Dry-run mode:** Production writes disabled during hackathon; mock execution only

## Expected Outcomes

- **User:** Reduced time-to-insight from 48 hours to <5 minutes; actionable recommendations vs. raw data
- **Business:** 10-30% reduction in wasted ad spend; higher ROI on marketing investment
- **Safety:** No autonomous actions; transparent reasoning; reversible recommendations only

---

*Word count: 198*
