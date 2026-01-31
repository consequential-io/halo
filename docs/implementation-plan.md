# Agatha Implementation Plan

## Overview
Multi-agent ad spend optimization system for hackathon demo (Feb 1, 09:00 IST)

**Approach:** AI-First (LLM reasons, Python validates)

---

## AI-First Architecture

```
Data → LLM reasons with guidelines → Python validates → Output
       ↑ Uses judgment + context     ↑ Catches hallucinations
```

| Task | Rules-Based (Wrong) | AI-First (Right) |
|------|---------------------|------------------|
| Classification | Python threshold check | LLM reasons with guidelines |
| Edge cases | Falls through to default | LLM handles nuance |
| Explanations | Template strings | Natural language citing data |

---

## Input Data Schema

### Raw Data (from BigQuery CSV)

Daily ad-level data with these columns:
```python
{
    "spend": float,
    "return_on_ad_spend_roas": float,
    "impressions": int,
    "cpc": float,
    "cpm": float,
    "ctr": float,
    "clicks": int,
    "datetime_PST": str,           # "2026-01-30 00:00:00"
    "ad_group_name": str,
    "ad_name": str,
    "ad_provider": str,            # "Google Ads", "Facebook Ads", "TikTok Ads"
    "creative_call_to_action_type": str,
    "creative_object_type": str,   # "Search", "SHARE", "WEB_CONVERSIONS"
    "customer_entry_page": str,
    "customer_lastVisit_campaign": str,
    "store": str                   # "US"
}
```

### Aggregated Input (passed to Analyze Agent)

```python
{
    "account_avg_roas": float,     # Weighted avg: SUM(roas * spend) / SUM(spend)
    "ads": [
        {
            "ad_name": str,
            "ad_provider": str,    # "Google Ads", "Facebook Ads", "TikTok Ads"
            "spend": float,        # SUM(spend) for this ad
            "roas": float,         # Weighted avg ROAS for this ad
            "days_active": int     # COUNT(DISTINCT date)
        }
    ]
}
```

### Data Stats (ThirdLove)
- Total spend: $4.5M
- Account avg ROAS: 6.90
- Unique ads: 1,084
- Date range: 299 days

### Test Fixture
See `backend/fixtures/thirdlove_ads.json` with 10 real ads covering all classifications:
- GOOD: "Thirdlove® Bras" (ROAS 29.58, 4.3× avg)
- OK: "DPA-Catalog-AllProducts 22382-D" (ROAS 7.76, 1.1× avg)
- WARNING: "purchase retention DPA-catalogsales" (ROAS 6.03, 0.87× avg)
- BAD: "7369346196164364049 catalog carousel" (ROAS 0.00, TikTok)
- WAIT: "Thirdlove® 4th Of July Sale" (6 days only)

---

## Output Schema (Canonical)

Every Analyze Agent response must match this structure:

```python
{
    # Identity
    "ad_name": str,
    "ad_provider": str,           # Optional: "Google Ads", "Facebook Ads", "TikTok Ads"

    # Metrics (cited from source data)
    "metrics": {
        "spend": float,
        "roas": float,
        "days_active": int,
        "account_avg_roas": float,
    },

    # AI Classification
    "classification": str,       # "GOOD", "OK", "WARNING", "BAD", "WAIT"
    "recommended_action": str,   # "SCALE", "MONITOR", "REVIEW", "REDUCE", "PAUSE", "WAIT"
    "confidence": str,           # "HIGH", "MEDIUM", "LOW"

    # Chain-of-Thought (required)
    "chain_of_thought": {
        "data_extracted": {},        # What metrics were found
        "comparison": {},            # ROAS ratio vs account avg
        "qualification": {},         # Spend/days thresholds met?
        "classification_logic": {},  # Why this classification
        "confidence_rationale": {}   # Why this confidence level
    },

    # User-facing
    "user_explanation": str,     # 1-2 sentences citing specific numbers
}
```

---

## Decision Thresholds (Guidelines for LLM)

**Account Baseline (ThirdLove):** $4.5M spend, 6.90 ROAS, 298 days

| ROAS vs Avg | Spend | Days | Classification | Action |
|-------------|-------|------|----------------|--------|
| >= 2× | >= $1k | >= 7 | GOOD | Scale 30-100% |
| 1× - 2× | >= $1k | >= 7 | OK | Monitor |
| 0.5× - 1× | >= $10k | >= 7 | WARNING | Review |
| < 0.5× | >= $10k | >= 7 | BAD | Reduce 50% |
| = 0 | >= $5k | >= 7 | BAD | Pause |
| Any | < $1k | < 7 | WAIT | Learning |

**These are GUIDELINES.** LLM may deviate with reasoning (e.g., "1.95× avg but upward trend → GOOD").

---

## Analyze Agent Prompt

```python
ANALYZE_AGENT_PROMPT = """
You are analyzing ad performance data. Your classifications MUST be grounded in actual metrics.

## RULES
1. NEVER invent metrics - only use values from provided data
2. ALWAYS cite specific numbers when making claims
3. ALWAYS compare to account average (provided in context)
4. If data insufficient, classify as WAIT

## CLASSIFICATION GUIDELINES (use judgment for edge cases)
- GOOD: ROAS >= 2× avg, spend >= $1k, days >= 7 → SCALE
- OK: ROAS 1-2× avg, spend >= $1k, days >= 7 → MONITOR
- WARNING: ROAS 0.5-1× avg, spend >= $10k, days >= 7 → REVIEW
- BAD: ROAS < 0.5× avg (spend >= $10k) OR ROAS = 0 (spend >= $5k), days >= 7 → REDUCE/PAUSE
- WAIT: spend < $1k OR days < 7 → WAIT

## OUTPUT FORMAT
{
  "ad_name": "<exact name from data>",
  "metrics": {
    "spend": <actual>,
    "roas": <actual>,
    "days_active": <actual>,
    "account_avg_roas": <actual>
  },
  "chain_of_thought": {
    "data_extracted": {"spend": ..., "roas": ..., "days": ...},
    "comparison": {"roas_ratio": "<ad_roas> / <avg> = <ratio>"},
    "qualification": {"spend_ok": true/false, "days_ok": true/false},
    "classification_logic": {"result": "...", "reason": "..."},
    "confidence_rationale": {"level": "...", "reason": "..."}
  },
  "classification": "GOOD|OK|WARNING|BAD|WAIT",
  "recommended_action": "SCALE|MONITOR|REVIEW|REDUCE|PAUSE|WAIT",
  "confidence": "HIGH|MEDIUM|LOW",
  "user_explanation": "<1-2 sentences citing numbers>"
}
"""
```

---

## Few-Shot Examples

```python
FEW_SHOT_EXAMPLES = """
## GOOD SPEND
Input: "Thirdlove® Bras" — $212k spend, 29.58 ROAS, 30 days, account avg 6.88

{
  "ad_name": "Thirdlove® Bras",
  "metrics": {"spend": 212000, "roas": 29.58, "days_active": 30, "account_avg_roas": 6.88},
  "chain_of_thought": {
    "comparison": {"roas_ratio": "29.58 / 6.88 = 4.3×"},
    "qualification": {"spend_ok": true, "days_ok": true},
    "classification_logic": {"result": "GOOD", "reason": "4.3× avg exceeds 2× threshold"}
  },
  "classification": "GOOD",
  "recommended_action": "SCALE",
  "confidence": "HIGH",
  "user_explanation": "ROAS of 29.58 is 4.3× your account average. Scale budget 50-100%."
}

## BAD SPEND (Zero ROAS)
Input: "TikTok Campaign Q4" — $88k spend, 0.00 ROAS, 45 days, account avg 6.88

{
  "ad_name": "TikTok Campaign Q4",
  "metrics": {"spend": 88000, "roas": 0.0, "days_active": 45, "account_avg_roas": 6.88},
  "chain_of_thought": {
    "comparison": {"roas_ratio": "0.0 / 6.88 = 0×", "is_zero": true},
    "qualification": {"spend_ok": true, "days_ok": true},
    "classification_logic": {"result": "BAD", "reason": "Zero ROAS after $88k and 45 days"}
  },
  "classification": "BAD",
  "recommended_action": "PAUSE",
  "confidence": "HIGH",
  "user_explanation": "Zero return on $88k over 45 days. Pause immediately."
}

## WAIT (Insufficient Data)
Input: "New Spring Collection" — $800 spend, 2.50 ROAS, 4 days, account avg 6.88

{
  "ad_name": "New Spring Collection",
  "metrics": {"spend": 800, "roas": 2.50, "days_active": 4, "account_avg_roas": 6.88},
  "chain_of_thought": {
    "qualification": {"spend_ok": false, "days_ok": false},
    "classification_logic": {"result": "WAIT", "reason": "Only 4 days and $800 spend"}
  },
  "classification": "WAIT",
  "recommended_action": "WAIT",
  "confidence": "LOW",
  "user_explanation": "Only 4 days with $800 spend. Need more data before classification."
}
"""
```

---

## Recommend Agent Prompt

```python
RECOMMEND_AGENT_PROMPT = """
Generate actionable recommendations from Analyze Agent output.

For each recommendation, MUST include:
1. Source metrics (from Analyze output)
2. Calculation showing derivation
3. Dollar impact estimate

## OUTPUT FORMAT
{
  "ad_name": "...",
  "action": "SCALE|REDUCE|PAUSE",
  "current_spend": <number>,
  "change_percentage": <number>,
  "proposed_new_spend": <number>,
  "expected_impact": {
    "calculation": "<show math>",
    "estimated_revenue_change": <number>
  },
  "confidence": "HIGH|MEDIUM|LOW",
  "rationale": "<cite specific metrics>"
}

## EXAMPLE
"Scale 'Thirdlove® Bras' budget by 75%"
- Current spend: $212,000
- ROAS: 29.58 (4.3× account avg)
- Proposed increase: $159,000
- Expected revenue: $159,000 × 29.58 = $4.7M
"""
```

---

## Execute Agent Prompt

```python
EXECUTE_AGENT_PROMPT = """
Execute approved recommendations. For hackathon, this is MOCK ONLY.

## INPUT
List of approved recommendations from Recommend Agent

## OUTPUT
{
  "executed": [
    {
      "ad_name": "...",
      "action_taken": "SCALED|REDUCED|PAUSED",
      "old_budget": <number>,
      "new_budget": <number>,
      "status": "SUCCESS|MOCK",
      "message": "Budget updated from $X to $Y"
    }
  ],
  "summary": "Executed N actions affecting $X in spend"
}

## MOCK MODE
Return success with "[MOCK]" prefix in messages. No actual API calls.
"""
```

---

## Validation Layer

Single canonical validator (runs after LLM response):

```python
# backend/helpers/validators.py

def validate_analyze_output(llm_response: dict, source_data: dict) -> tuple[bool, list[str]]:
    """
    Validates LLM output is grounded and complete.
    Returns (is_valid, list_of_violations)

    Checks:
    1. Required fields present
    2. Cited metrics match source data
    3. CoT chain complete
    4. Classification values valid

    Does NOT check classification "correctness" - LLM judgment allowed.
    """
    violations = []

    # 1. Required fields
    required = ["ad_name", "metrics", "classification", "recommended_action",
                "confidence", "chain_of_thought", "user_explanation"]
    for field in required:
        if field not in llm_response:
            violations.append(f"Missing field: {field}")

    # 2. Cited metrics match source (within tolerance)
    if "metrics" in llm_response:
        cited = llm_response["metrics"]
        if abs(cited.get("spend", 0) - source_data.get("spend", 0)) > 1:
            violations.append(f"Spend mismatch: cited {cited.get('spend')}, actual {source_data.get('spend')}")
        if abs(cited.get("roas", 0) - source_data.get("roas", 0)) > 0.01:
            violations.append(f"ROAS mismatch: cited {cited.get('roas')}, actual {source_data.get('roas')}")

    # 3. CoT completeness
    cot_required = ["data_extracted", "comparison", "qualification",
                    "classification_logic", "confidence_rationale"]
    if "chain_of_thought" in llm_response:
        for step in cot_required:
            if step not in llm_response["chain_of_thought"]:
                violations.append(f"Missing CoT step: {step}")

    # 4. Valid classification values
    if llm_response.get("classification") not in ["GOOD", "OK", "WARNING", "BAD", "WAIT"]:
        violations.append(f"Invalid classification: {llm_response.get('classification')}")

    return (len(violations) == 0, violations)


def handle_validation_failure(llm_response: dict, violations: list[str], retry_count: int) -> dict:
    """
    Handle validation failures with retry or graceful degradation.
    """
    if retry_count < 2:
        # Retry with feedback
        return {"action": "retry", "feedback": violations}
    else:
        # Graceful degradation after 2 retries
        return {
            "action": "degrade",
            "result": {
                "ad_name": llm_response.get("ad_name", "unknown"),
                "classification": "MANUAL_REVIEW",
                "user_explanation": "Unable to classify automatically. Please review manually.",
                "violations": violations
            }
        }
```

---

## Account Average Calculation

The `account_avg_roas` must be calculated from BigQuery before calling the agent:

```sql
-- Calculate account average ROAS (last 30 days)
SELECT
    SAFE_DIVIDE(SUM(ROAS * spend), SUM(spend)) as weighted_avg_roas
FROM `otb-dev-platform.master.northstar_master_combined_tl`
WHERE data_source = 'Ad Providers'
  AND datetime_UTC >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND spend > 0
```

Pass this to the agent in context:
```python
context = {
    "account_avg_roas": 6.88,  # From query above
    "ads": [...]  # Ad data to analyze
}
```

---

## Architecture

```
Meta OAuth → Agatha Orchestrator
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
ANALYZE         RECOMMEND        EXECUTE
(AI reasoning)  (AI reasoning)  (Mock write)
```

---

## Data Sources

| Priority | Source | Use |
|----------|--------|-----|
| Demo | Meta API | Live data, impressive |
| Dev/Test | BigQuery | Pre-loaded, fast |
| Fallback | BigQuery | If Meta fails |

### BigQuery Views
- ThirdLove: `otb-dev-platform.master.northstar_master_combined_tl`
- WhisperingHomes: `otb-dev-platform.master.northstar_master_combined_wh`

### Key Query Pattern
```sql
SELECT
    ad_name,
    ad_provider,
    SUM(spend) as spend,
    SAFE_DIVIDE(SUM(ROAS * spend), SUM(spend)) as roas,
    DATE_DIFF(MAX(DATE(datetime_UTC)), MIN(DATE(datetime_UTC)), DAY) + 1 as days_active
FROM `otb-dev-platform.master.northstar_master_combined_tl`
WHERE data_source = 'Ad Providers'
  AND datetime_UTC >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY ad_name, ad_provider
ORDER BY spend DESC
```

---

## Meta API Integration

**Pattern:** Facebook OAuth → token → Marketing API calls

**Required scopes:** `ads_read`, `ads_management`, `business_management`

**Endpoints:**
- Ad details: `GET /v19.0/{ad_id}?fields=id,name,creative{id,image_url},status`
- Creative preview: `GET /v19.0/{creative_id}/previews?ad_format=DESKTOP_FEED_STANDARD`

**Backend routes:**
- `GET /auth/facebook` - Redirect to OAuth
- `GET /auth/facebook/callback` - Exchange code for token
- `GET /meta-ads/ads/{ad_id}` - Fetch ad details
- `GET /meta-ads/creative/{creative_id}/preview` - Fetch preview

---

## Timeline

**Start:** Jan 31, 17:30 IST | **Demo:** Feb 1, 09:00 IST | **Available:** 15.5 hours

| Milestone | Target | Gate |
|-----------|--------|------|
| Minimal setup + mock tool | 18:30 | - |
| Analyze Agent + fixtures | 21:00 | - |
| **GATE 1** | 21:30 | CoT complete + metrics grounded? |
| Recommend Agent | 23:30 | - |
| **GATE 2** | 00:00 | Recommendations sensible? |
| BigQuery integration | 01:30 | - |
| **GATE 3** | 02:00 | Live data quality OK? |
| Execute Agent (mock) | 03:30 | - |
| FastAPI routes | 05:00 | - |
| Frontend basic UI | 06:30 | - |
| Integration | 07:30 | - |
| Buffer | 08:30 | - |
| **DEMO** | 09:00 | - |

### Gate Definitions

| Gate | Question | Pass Criteria | Fail Action |
|------|----------|---------------|-------------|
| **1** | Grounded reasoning? | CoT complete, metrics match source | Fix prompt, add examples |
| **2** | Actionable recs? | Cites metrics, shows calculation | Simplify prompt |
| **3** | Live data OK? | Same quality as fixtures | Use fixtures (fallback) |

---

## Implementation Tasks

### Phase 1: AI Validation (17:30 - 00:00)

| Task | Deliverable |
|------|-------------|
| P1-1 | Minimal pyproject.toml + settings |
| P1-2 | Mock data tool (`get_ad_data()`) |
| P1-3 | Analyze Agent with prompt + validation |
| P1-4 | GATE 1: Validate output |
| P1-5 | Recommend Agent with grounded output |
| P1-6 | GATE 2: Human review |

### Phase 2: Data Integration (00:00 - 02:00)

| Task | Deliverable |
|------|-------------|
| P2-1 | BigQuery data tool |
| P2-2 | Re-run agents with live data |
| P2-3 | GATE 3: Quality check |

### Phase 3: API & Execute (02:00 - 05:00)

| Task | Deliverable |
|------|-------------|
| P3-1 | Execute Agent (mock) |
| P3-2 | FastAPI routes (`/analyze`, `/recommend`, `/execute`) |
| P3-3 | Session management |

### Phase 4: Frontend & Demo (05:00 - 08:30)

| Task | Deliverable |
|------|-------------|
| P4-1 | Minimal React UI |
| P4-2 | Integration testing |
| P4-3 | Demo script + fallback |

---

## File Structure

```
halo/
├── backend/
│   ├── main.py
│   ├── config/
│   │   ├── settings.py
│   │   └── session_manager.py
│   ├── models/
│   │   ├── analyze_agent.py
│   │   ├── recommend_agent.py
│   │   └── execute_agent.py
│   ├── controllers/
│   │   ├── base_controller.py
│   │   └── agatha_controller.py
│   ├── routes/
│   │   ├── auth_routes.py
│   │   └── agent_routes.py
│   ├── helpers/
│   │   ├── tools.py
│   │   └── validators.py
│   └── schemas/
├── frontend/
│   └── src/
└── docs/
```

---

## Key Patterns (from otb-agents)

```python
# Agent Definition
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

agent = LlmAgent(
    name="analyze_agent",
    model="gemini-2.5-pro",
    instruction=ANALYZE_AGENT_PROMPT,
    tools=[get_ad_data_tool],
)

# Controller Pattern
class AgathaController(BaseController):
    async def run_analysis(self, request):
        return await self.run_agent_flow(
            agent=self.analyze_agent,
            message_content=json.dumps(request.dict()),
        )
```

---

## Model Configuration

```python
MODEL_CONFIG = {
    "provider": os.getenv("AI_PROVIDER", "gemini"),
    "gemini": {"model": "gemini-2.5-pro"},
    "openai": {"model": "gpt-4-turbo"},
}
```

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Meta API complexity | BigQuery as primary, Meta for demo |
| Time pressure | Minimal UI, shadcn components |
| Integration bugs | Buffer time, fallback demo script |
| OAuth issues | Pre-authenticate test account |
| LLM hallucination | Validation layer + retry logic |
| Unexplainable decisions | CoT required in all outputs |

---

## Verification Checklist

Before demo:
- [ ] Analyze outputs include complete `chain_of_thought`
- [ ] Cited metrics match source data (within tolerance)
- [ ] Recommendations include dollar impact calculations
- [ ] `validate_analyze_output()` catches bad data (test with fabricated metrics)
- [ ] Few-shot examples produce sensible classifications
- [ ] User explanations cite specific numbers
- [ ] Edge cases handled (borderline thresholds, zero ROAS, new ads)
- [ ] Graceful degradation works after 2 retry failures

---

## Decisions Made

| Decision | Choice |
|----------|--------|
| Team split | Both fullstack, split by feature |
| Data source | Meta (demo) + BigQuery (dev/fallback) |
| AI Model | Config-driven (Gemini/OpenAI) |
| Execute actions | Mock for hackathon |
| Classification | AI-first (LLM reasons, Python validates) |

## Open Questions

| Question | Owner | Status |
|----------|-------|--------|
| Demo scenario/script? | Jaidev | TL account showing $88k TikTok waste |
