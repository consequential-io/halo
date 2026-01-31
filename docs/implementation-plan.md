# Agatha Implementation Plan

## Overview
Multi-agent ad spend optimization system for hackathon demo (Feb 1, 09:00 IST)

**Approach:** AI-First (LLM reasons with guidelines, Python validates)

## Decisions Made

| # | Question | Decision |
|---|----------|----------|
| Team split | Both fullstack, split by feature | Each owns E2E features |
| Data source | Meta API (demo) + BigQuery (dev/test/fallback) | BQ has both Meta & Google data |
| AI Model | Config-driven | Switch between Gemini/OpenAI via env var |
| Execute actions | Mock write for hackathon | Real API stretch goal |
| BigQuery views | TL + WH views identified | See BigQuery Data Access section |
| Meta OAuth | Custom OAuth with httpx | See Meta API Integration section |
| Meta creatives | Two-step fetch pattern | See Meta API Integration section |
| Classification | AI-first (LLM reasons, Python validates) | Not rules-based |

## Open Questions

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 6 | Meta OAuth scopes needed? | Hemanth | RESOLVED - see Meta API section |
| 7 | Meta Ad creatives access? | Hemanth | RESOLVED - see Meta API section |
| 8 | Demo scenario/script? | Jaidev | TL account showing $88k TikTok waste |

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

## Meta API Integration

### Facebook Login Pattern

**Frontend (simple redirect):**
```javascript
const handleFacebookLogin = () => {
  const facebookLoginUrl = buildUrl("auth/facebook", { redirectTo: returnUrl });
  window.open(facebookLoginUrl, "_self");
};
```

**Backend route needed:** `/auth/facebook` (FastAPI OAuth handler)
- Redirects to Facebook OAuth
- Handles callback with token exchange
- Stores access token in session

### Meta Ad Creative Preview

**Two-step fetch pattern:**

```
Step 1: GET /meta-ads/ads/{adId}
Response: {
  "data": {
    "ad_id": "...",
    "ad_name": "...",
    "creative_id": "...",    // Needed for Step 2
    "image_url": "...",      // Thumbnail URL
    "status": "ACTIVE"
  }
}

Step 2: GET /meta-ads/creative/{creativeId}/preview
Response: {
  "data": {
    "has_video": true/false,
    "has_preview": true/false,
    "preview_html": "<iframe>...</iframe>"  // Embeddable preview
  }
}
```

### Required Meta API Scopes
- `ads_read` - Read ad account data
- `ads_management` - For Execute Agent (if doing real writes)
- `business_management` - Access business accounts

### Meta Marketing API Endpoints
```python
# Ad details
GET https://graph.facebook.com/v19.0/{ad_id}
  ?fields=id,name,creative{id,image_url,thumbnail_url,video_id},status
  &access_token={token}

# Creative preview
GET https://graph.facebook.com/v19.0/{creative_id}/previews
  ?ad_format=DESKTOP_FEED_STANDARD
  &access_token={token}
```

### Custom OAuth Flow (FastAPI)
```python
# routes/auth_routes.py
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import httpx

router = APIRouter()

META_APP_ID = settings.meta_app_id
META_APP_SECRET = settings.meta_app_secret
META_REDIRECT_URI = settings.meta_redirect_uri

@router.get("/facebook")
async def facebook_login(redirectTo: str = "/"):
    """Redirect to Facebook OAuth consent screen"""
    oauth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={META_APP_ID}"
        f"&redirect_uri={META_REDIRECT_URI}"
        f"&scope=ads_read,ads_management,business_management"
        f"&state={redirectTo}"  # Pass return URL in state
    )
    return RedirectResponse(url=oauth_url)

@router.get("/facebook/callback")
async def facebook_callback(code: str, state: str = "/"):
    """Handle OAuth callback, exchange code for token"""
    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_response = await client.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "redirect_uri": META_REDIRECT_URI,
                "code": code
            }
        )
        token_data = token_response.json()
        access_token = token_data.get("access_token")

        # Get long-lived token (optional but recommended)
        long_token_response = await client.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "fb_exchange_token": access_token
            }
        )
        long_token_data = long_token_response.json()

        # Store token in session/memory (for hackathon)
        # In production: encrypt and store in database

        # Redirect to frontend with token
        return RedirectResponse(
            url=f"{state}?token={long_token_data.get('access_token', access_token)}"
        )
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

## Team Feature Split

| Feature | Owner | Scope |
|---------|-------|-------|
| **Analyze flow** | Person A | BQ/Meta read → Analyze Agent → Analysis UI |
| **Recommend flow** | Person A | Recommend Agent → Recommendations UI |
| **Execute flow** | Person B | Execute Agent → Approval UI → Confirmation |
| **Foundation** | Person B | Scaffolding, session manager, base controller |
| **Auth/OAuth** | Person B | Meta OAuth integration |
| **Demo prep** | Both | Script, fallback, submission materials |

---

## Data Source Strategy

```
┌─────────────────────────────────────────┐
│           Data Source Priority          │
├─────────────────────────────────────────┤
│ DEMO:     Meta API (live, impressive)   │
│ DEV/TEST: BigQuery (pre-loaded, fast)   │
│ FALLBACK: BigQuery (if Meta fails)      │
├─────────────────────────────────────────┤
│ BigQuery contains: Meta + Google data   │
│ - TL: 298 days history                  │
│ - WH: 76 days history                   │
└─────────────────────────────────────────┘
```

---

## BigQuery Data Access

### Views
| Tenant | View |
|--------|------|
| ThirdLove (TL) | `otb-dev-platform.master.northstar_master_combined_tl` |
| WhisperingHomes (WH) | `otb-dev-platform.master.northstar_master_combined_wh` |

### Data Source Filtering (Critical)
Each metric type requires filtering by authoritative source to avoid double-counting:

| Metric Type | Filter | Columns |
|-------------|--------|---------|
| **Advertising** | `WHERE data_source = 'Ad Providers'` | spend, ad_click, CPA, CPC, CPM, CTR, ROAS |
| **Revenue** | `WHERE data_source = 'Shopify'` | gross_sales, net_sales, total_sales, order_id |
| **Engagement** | `WHERE data_source IN ('CDP (Blotout)', 'CDP GA4 Totals')` | session_id, page_views |

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

### Account Average Calculation
```sql
-- Calculate account average ROAS (last 30 days)
SELECT
    SAFE_DIVIDE(SUM(ROAS * spend), SUM(spend)) as weighted_avg_roas
FROM `otb-dev-platform.master.northstar_master_combined_tl`
WHERE data_source = 'Ad Providers'
  AND datetime_UTC >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND spend > 0
```

### ROAS Calculation (Mixed Sources - Use CTEs)
```sql
WITH revenue AS (
  SELECT
    DATE(TIMESTAMP(datetime_UTC, 'America/Los_Angeles')) as date,
    SUM(total_sales) as revenue
  FROM `otb-dev-platform.master.northstar_master_combined_tl`
  WHERE data_source = 'Shopify'
  GROUP BY date
),
ad_spend AS (
  SELECT
    DATE(TIMESTAMP(datetime_UTC, 'America/Los_Angeles')) as date,
    SUM(spend) as spend
  FROM `otb-dev-platform.master.northstar_master_combined_tl`
  WHERE data_source = 'Ad Providers'
  GROUP BY date
)
SELECT
  r.date,
  r.revenue,
  a.spend,
  SAFE_DIVIDE(r.revenue, a.spend) as calculated_roas
FROM revenue r
JOIN ad_spend a ON r.date = a.date
ORDER BY r.date DESC
```

### Available Columns (Ad Providers)
- `spend` - Total ad spend
- `ROAS` - Return on ad spend (pre-calculated)
- `ad_click` - Number of clicks
- `CPA` - Cost per acquisition
- `CPC` - Cost per click
- `CPM` - Cost per mille (1000 impressions)
- `CTR` - Click-through rate
- `ad_name` - Ad creative name
- `ad_provider` - Platform (Google Ads, Facebook Ads, TikTok Ads)
- `store` - Market (US, IND)
- `datetime_UTC` - Timestamp

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

### Critical Path

```
NOW (17:30)
    │
    ▼ [1h] Minimal setup
18:30
    │
    ▼ [2.5h] Analyze Agent (fixtures)
21:00
    │
    ▼ [0.5h] GATE 1 ← First AI validation
21:30
    │
    ▼ [2h] Recommend Agent
23:30
    │
    ▼ [0.5h] GATE 2 ← Second AI validation
00:00 (Feb 1)
    │
    ▼ [1.5h] BigQuery integration
01:30
    │
    ▼ [0.5h] GATE 3 ← Live data or fallback
02:00
    │
    ▼ [5.5h] Execute + Routes + Frontend
07:30
    │
    ▼ [1h] Integration
08:30
    │
    ▼ [0.5h] Buffer
09:00 DEMO
```

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
│   ├── main.py                    # FastAPI app
│   ├── config/
│   │   ├── __init__.py
│   │   ├── session_manager.py     # Singleton session service
│   │   └── settings.py            # Environment config
│   ├── models/
│   │   ├── __init__.py
│   │   ├── analyze_agent.py       # Analyze Agent
│   │   ├── recommend_agent.py     # Recommend Agent
│   │   └── execute_agent.py       # Execute Agent
│   ├── controllers/
│   │   ├── __init__.py
│   │   ├── base_controller.py     # Common agent flow
│   │   └── agatha_controller.py   # Orchestrator
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth_routes.py         # Meta OAuth
│   │   └── agent_routes.py        # Agent endpoints
│   ├── helpers/
│   │   ├── __init__.py
│   │   ├── tools.py               # Agent tools (BQ, Meta)
│   │   └── validators.py          # validate_analyze_output()
│   ├── fixtures/
│   │   └── thirdlove_ads.json     # Test data
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── requests.py
│   │   └── responses.py
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Login
│   │   │   ├── dashboard/
│   │   │   └── recommendations/
│   │   └── components/
│   └── .env.local.example
└── docs/
    ├── implementation-plan.md
    └── requirements-agatha.md
```

---

## Key Patterns (from otb-agents)

### Agent Definition
```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

agent = LlmAgent(
    name="analyze_agent",
    model="gemini-2.5-pro",
    instruction=ANALYZE_AGENT_PROMPT,
    tools=[get_ad_data_tool],
)
```

### Controller Pattern
```python
class AgathaController(BaseController):
    async def run_analysis(self, request):
        return await self.run_agent_flow(
            agent=self.analyze_agent,
            message_content=json.dumps(request.dict()),
        )
```

### Tool Definition
```python
async def get_ad_data(account_id: str, days: int = 30) -> Dict:
    # Query BigQuery or Meta API
    ...

get_ad_data_tool = FunctionTool(func=get_ad_data)
```

---

## Model Configuration

```python
# config/settings.py
import os

MODEL_CONFIG = {
    "provider": os.getenv("AI_PROVIDER", "gemini"),  # gemini | openai
    "gemini": {
        "model": os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
    },
    "openai": {
        "model": os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
    }
}
```

---

## Foundational Elements

### Logging (Structured JSON)

```python
# config/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logging.root.handlers = [handler]
    logging.root.setLevel(logging.INFO)
```

### Testing (Unit + Integration)

```
tests/
├── unit/
│   ├── test_classify_spend.py      # Good/bad spend logic
│   ├── test_analyze_agent.py       # Agent callbacks
│   └── test_recommend_logic.py     # Recommendation rules
├── integration/
│   ├── test_agent_flow.py          # E2E agent execution
│   ├── test_bigquery_connector.py  # BQ data retrieval
│   └── test_api_endpoints.py       # FastAPI routes
└── conftest.py                     # Shared fixtures

# Run: pytest tests/ -v --cov=backend
```

**Test Strategy:**
- Unit tests: Mock LLM responses, test business logic
- Integration tests: Use `AsyncMock` for agent execution
- Fixtures: Pre-loaded test data from BigQuery exports

### Observability (OpenTelemetry + Google ADK)

```python
# config/observability.py
from fi_instrumentation import register
from fi_instrumentation.fi_types import ProjectType
from traceai_google_adk import GoogleADKInstrumentor
import os

def setup_observability():
    trace_provider = register(
        project_type=ProjectType.OBSERVE,
        project_name=os.getenv("FI_PROJECT_NAME", "agatha")
    )
    GoogleADKInstrumentor().instrument(tracer_provider=trace_provider)
    return trace_provider
```

**Traces captured:**
- Agent execution (via ADK instrumentation)
- Tool calls (BQ queries, Meta API)
- Request/response at API level

---

## Deployment (Cloud Run - GCP)

### cloudbuild.yaml
```yaml
steps:
  # Build backend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/agatha-backend', './backend']

  # Build frontend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/agatha-frontend', './frontend']

  # Deploy backend to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'deploy'
      - 'agatha-backend'
      - '--image=gcr.io/$PROJECT_ID/agatha-backend'
      - '--region=us-central1'
      - '--allow-unauthenticated'

  # Deploy frontend to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args:
      - 'run'
      - 'deploy'
      - 'agatha-frontend'
      - '--image=gcr.io/$PROJECT_ID/agatha-frontend'
      - '--region=us-central1'
      - '--allow-unauthenticated'
```

### Dockerfiles

**Backend:**
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install .
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Frontend:**
```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
CMD ["npm", "start"]
```

### Environment Variables (Cloud Run)
- `AI_PROVIDER`: gemini | openai
- `GEMINI_MODEL`: gemini-2.5-pro
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `META_APP_ID`: Meta app credentials
- `META_APP_SECRET`: Meta app secret
- `FI_PROJECT_NAME`: Observability project name

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Meta API complexity | Use BigQuery as primary for dev, Meta for demo |
| Time pressure | Minimal UI, use component library (shadcn) |
| Integration bugs | Buffer time, fallback demo script |
| OAuth issues | Pre-authenticate test account |
| Cloud Run cold start | Keep backend warm with health checks |
| Secret management | Use GCP Secret Manager |
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
- [ ] Meta OAuth flow works (for demo)

---

## Dependencies Between Tasks

```
P1-1 (minimal setup)
    │
    └── P1-2 (mock data tool)
           │
           └── P1-3 (Analyze Agent) ──► GATE 1
                  │
                  └── P1-5 (Recommend Agent) ──► GATE 2
                         │
                         ├── P2-1 (BigQuery tool) ──► GATE 3
                         │
                         └── P3-1 (Execute Agent)
                                │
                                └── P3-2 (FastAPI routes)
                                       │
                                       └── P4-1 (Frontend)
                                              │
                                              └── P4-2 (Integration)
```

**Key insight:** Agents are validated with mock data BEFORE building data connectors or infrastructure. Gates ensure we don't build infra for broken AI.
