# Agatha Implementation Plan

## Overview
Multi-agent ad spend optimization system for hackathon demo (Feb 1, 09:00 IST)

**Approach:** AI-First Implementation (validate AI value before infrastructure)

---

## AI-First Architecture

### The Core Principle

**LLM reasons, Python validates.** Not the other way around.

```
WRONG (AI-wrapped rules):
  Data → Python classify_spend() → Python assign_grade() → LLM formats output
         ↑ Deterministic rules      ↑ More rules           ↑ Just formatting

RIGHT (AI-first):
  Data → LLM reasons with guidelines → Python validates → Output
         ↑ Uses judgment + context     ↑ Catches hallucinations
```

### Why This Matters

| Task | Rules-Based (Wrong) | AI-First (Right) |
|------|---------------------|------------------|
| Classification | Python threshold check | LLM reasons about data with guidelines |
| Edge cases | Falls through to default | LLM handles nuance (1.95× avg = maybe GOOD) |
| Explanations | Template strings | LLM generates natural insights |
| Trends | Not detected | LLM spots "ROAS declining 3 weeks" |
| Creative analysis | Just "fatigued" flag | LLM explains what's wrong |

---

## Hallucination Prevention Strategy

### The Problem
LLMs can invent plausible-sounding recommendations not grounded in data:
- "This ad is underperforming" (based on what numbers?)
- "You should scale by 50%" (why 50%?)
- "Creative fatigue detected" (what signals?)

### Solution: Data-Grounded Prompts + Validation Layer

Every agent response MUST:
1. Cite the actual metrics it's reasoning about
2. Show step-by-step logic the user can verify
3. Pass post-LLM validation that checks cited numbers match source data

### Validation Layer (Post-LLM Check)

```python
# backend/helpers/validators.py

def validate_grounded_response(llm_response: dict, source_data: dict) -> tuple[bool, list[str]]:
    """
    Verify LLM claims are grounded in actual data.
    Returns (is_valid, list_of_violations)
    """
    violations = []

    for ad in llm_response.get("ads", []):
        ad_name = ad["ad_name"]
        source_ad = find_ad_in_source(ad_name, source_data)

        if not source_ad:
            violations.append(f"Ad '{ad_name}' not found in source data")
            continue

        # Verify cited numbers match reality (with tolerance for rounding)
        if abs(ad["metrics"]["spend"] - source_ad["spend"]) > 1:
            violations.append(f"Spend mismatch for '{ad_name}': cited {ad['metrics']['spend']}, actual {source_ad['spend']}")

        if abs(ad["metrics"]["roas"] - source_ad["roas"]) > 0.01:
            violations.append(f"ROAS mismatch for '{ad_name}': cited {ad['metrics']['roas']}, actual {source_ad['roas']}")

    return (len(violations) == 0, violations)
```

---

## Chain-of-Thought (CoT) Reasoning

### Why CoT Matters
Users need to trust recommendations. Showing reasoning:
- Builds confidence in the system
- Allows users to catch errors
- Makes the "why" as valuable as the "what"

### 6-Step Reasoning Chain

Every ad analysis must follow this structure:

| Step | Question | Output |
|------|----------|--------|
| **1. Data Extraction** | What are the actual metrics? | spend, roas, days_active, account_avg |
| **2. Threshold Comparison** | How does ROAS compare to account avg? | roas_ratio = ad_roas / account_avg |
| **3. Qualification Check** | Is there enough data to decide? | spend >= $1k AND days >= 7 |
| **4. Classification** | What category does this fall into? | GOOD / OK / WARNING / BAD / WAIT |
| **5. Recommendation** | What action should be taken? | Scale / Monitor / Review / Reduce / Pause |
| **6. Confidence** | How certain is this classification? | HIGH / MEDIUM / LOW with rationale |

### Example CoT Output

```json
{
  "ad_name": "TikTok Campaign Q4",
  "chain_of_thought": {
    "step_1_data": {
      "spend": 88000,
      "roas": 0.0,
      "days_active": 45,
      "account_avg_roas": 6.88
    },
    "step_2_comparison": {
      "roas_ratio": "0.0 / 6.88 = 0.0",
      "vs_good_threshold": "0.0 < 2.0 ❌",
      "is_zero_roas": true
    },
    "step_3_qualification": {
      "spend_qualified": "$88,000 >= $5,000 ✓",
      "days_qualified": "45 >= 7 ✓",
      "fully_qualified": true
    },
    "step_4_classification": {
      "logic": "ROAS = 0 AND spend >= $5k AND days >= 7 → BAD (PAUSE rule)",
      "result": "BAD"
    },
    "step_5_recommendation": {
      "action": "PAUSE",
      "rationale": "Zero return on $88k investment over 45 days."
    },
    "step_6_confidence": {
      "level": "HIGH",
      "rationale": "Zero ROAS is unambiguous. High spend provides certainty."
    }
  },
  "summary": "PAUSE this campaign. $88,000 spent over 45 days with zero return."
}
```

---

## Decision Thresholds (Guidelines, Not Absolutes)

### Scope
- **In scope:** Ads data only (BigQuery ad platform metrics)
- **Out of scope:** Shopify attribution data (for now)

### Account Baseline (ThirdLove Reference)
- Total spend: $4.5M over 298 days
- Overall ROAS: 6.90 (ad platform)
- Unique ads: 1,083

### Decision Matrix

| ROAS vs Account Avg | Spend | Days | Status | Action |
|---------------------|-------|------|--------|--------|
| >= 2× (>= 13.8) | >= $1k | >= 7 | 🟢 GOOD | Scale 30-100% |
| 1× - 2× (6.9 - 13.8) | >= $1k | >= 7 | 🟡 OK | Monitor |
| 0.5× - 1× (3.45 - 6.9) | >= $10k | >= 7 | 🟠 WARNING | Review |
| < 0.5× (< 3.45) | >= $10k | >= 7 | 🔴 BAD | Reduce 50% |
| = 0 | >= $5k | >= 7 | 🔴 BAD | Pause |
| Any | < $1k | < 7 | ⚪ WAIT | Learning |

**IMPORTANT:** These are GUIDELINES for the LLM, not absolute rules. The LLM may use judgment for:
- Ads just below thresholds (1.95× might still be GOOD)
- Trending ads (declining ROAS over time)
- Funnel position (TOF expected to have lower ROAS)
- Seasonality patterns

### Funnel-Aware Expectations

| Funnel | Creative Types | Expected ROAS | Threshold Adjustment |
|--------|----------------|---------------|----------------------|
| BOF | Search, Shopping, Brand | 5-20+ | Use standard thresholds |
| TOF | Video, Prospecting, TikTok | 0-5 | Lower threshold (1× avg = OK) |

---

## Analyze Agent Prompt Template

```python
ANALYZE_AGENT_PROMPT = """
You are analyzing ad performance data. Your classifications MUST be grounded in the actual metrics provided.

## RULES
1. NEVER invent metrics - only use values from the provided data
2. ALWAYS cite the specific numbers when making claims
3. ALWAYS compare to the account average (provided in context)
4. If data is insufficient, say "WAIT - need more data" instead of guessing

## CLASSIFICATION GUIDELINES (use judgment, not rigid rules)

🟢 GOOD SPEND (Scale 30-100%):
- ROAS >= 2× account average AND spend >= $1,000 AND running >= 7 days
- Example: "Thirdlove® Bras" — $212k spend, 29.58 ROAS (4.3× avg) → SCALE

🟡 OK (Monitor):
- ROAS 1-2× account average, qualified spend/time
- No action needed, performing adequately

🟠 WARNING (Review):
- ROAS 0.5-1× account average after significant spend ($10k+)
- May need creative refresh or audience adjustment

🔴 BAD SPEND (Pause/Reduce):
- ROAS = 0 after $5k+ spend AND 7+ days → PAUSE
- ROAS < 0.5× account average after $10k+ → REDUCE 50%
- Example: TikTok ads — $88k spend, 0.00 ROAS after 45 days → PAUSE

⚪ WAIT (Learning phase):
- spend < $1,000 OR running < 7 days
- Insufficient data to classify

## USE JUDGMENT FOR:
- Borderline cases (1.95× avg might still merit GOOD)
- Trend detection (ROAS declining week-over-week)
- Funnel context (TOF campaigns have lower ROAS by design)

## OUTPUT FORMAT
For each ad, include:
{
  "ad_name": "<exact name from data>",
  "metrics": {
    "spend": <actual value>,
    "roas": <actual value>,
    "days_active": <actual value>,
    "account_avg_roas": <actual value>
  },
  "chain_of_thought": {
    "step_1_data": {...},
    "step_2_comparison": {...},
    "step_3_qualification": {...},
    "step_4_classification": {...},
    "step_5_recommendation": {...},
    "step_6_confidence": {...}
  },
  "classification": "GOOD|OK|WARNING|BAD|WAIT",
  "recommended_action": "SCALE|MONITOR|REVIEW|REDUCE|PAUSE|WAIT",
  "confidence": "HIGH|MEDIUM|LOW",
  "user_explanation": "<1-2 sentence explanation citing specific numbers>"
}
"""
```

---

## Few-Shot Examples (Critical for Grounding)

```python
FEW_SHOT_EXAMPLES = """
## Example 1: GOOD SPEND
Input: Ad "Thirdlove® Bras" — $212k spend, 29.58 ROAS, 30 days, account avg 6.88

Analysis:
{
  "ad_name": "Thirdlove® Bras",
  "metrics": {"spend": 212000, "roas": 29.58, "days_active": 30, "account_avg_roas": 6.88},
  "chain_of_thought": {
    "step_2_comparison": {"roas_ratio": "29.58 / 6.88 = 4.3×"},
    "step_3_qualification": {"spend_qualified": true, "days_qualified": true},
    "step_4_classification": {"result": "GOOD", "logic": "4.3× avg, exceeds 2× threshold"}
  },
  "classification": "GOOD",
  "recommended_action": "SCALE",
  "confidence": "HIGH",
  "user_explanation": "ROAS of 29.58 is 4.3× your account average. Scale budget 50-100%."
}

## Example 2: BAD SPEND (Zero ROAS)
Input: Ad "TikTok Campaign Q4" — $88k spend, 0.00 ROAS, 45 days, account avg 6.88

Analysis:
{
  "ad_name": "TikTok Campaign Q4",
  "metrics": {"spend": 88000, "roas": 0.0, "days_active": 45, "account_avg_roas": 6.88},
  "chain_of_thought": {
    "step_2_comparison": {"roas_ratio": "0.0 / 6.88 = 0×", "is_zero_roas": true},
    "step_3_qualification": {"spend_qualified": true, "days_qualified": true},
    "step_4_classification": {"result": "BAD", "logic": "Zero ROAS after $88k and 45 days"}
  },
  "classification": "BAD",
  "recommended_action": "PAUSE",
  "confidence": "HIGH",
  "user_explanation": "Zero return on $88k over 45 days. Pause immediately."
}

## Example 3: WAIT (Insufficient Data)
Input: Ad "New Spring Collection" — $800 spend, 2.50 ROAS, 4 days, account avg 6.88

Analysis:
{
  "ad_name": "New Spring Collection",
  "metrics": {"spend": 800, "roas": 2.50, "days_active": 4, "account_avg_roas": 6.88},
  "chain_of_thought": {
    "step_3_qualification": {"spend_qualified": false, "days_qualified": false},
    "step_4_classification": {"result": "WAIT", "logic": "Only 4 days and $800 spend"}
  },
  "classification": "WAIT",
  "recommended_action": "WAIT",
  "confidence": "LOW",
  "user_explanation": "Only 4 days active with $800 spend. Need 3 more days before classification."
}
"""
```

---

## Recommend Agent Grounding

Recommendations must include source data and calculations:

```python
RECOMMEND_AGENT_PROMPT = """
Generate actionable recommendations based on the Analyze Agent output.

For each recommendation, you MUST include:
1. Source ad data (from Analyze output)
2. Calculation showing how recommendation was derived
3. Dollar impact estimate

## Example Grounded Recommendation:

"Scale 'Thirdlove® Bras' budget by 75%"
- Current spend: $212,000
- ROAS: 29.58 (4.3× account avg)
- Proposed increase: $159,000 (75% of current)
- Expected additional revenue: $159,000 × 29.58 = $4.7M
- Confidence: HIGH (strong historical performance over 30 days)

## Output Format:
{
  "ad_name": "...",
  "action": "SCALE|REDUCE|PAUSE",
  "current_spend": <number>,
  "change_percentage": <number>,
  "proposed_new_spend": <number>,
  "expected_impact": {
    "calculation": "<show the math>",
    "estimated_revenue_change": <number>
  },
  "confidence": "HIGH|MEDIUM|LOW",
  "rationale": "<cite specific metrics>"
}
"""
```

---

## Known Gaps & Mitigations

| Gap | Description | Mitigation |
|-----|-------------|------------|
| **Threshold tension** | LLM judgment vs validation layer may conflict (1.95× classified as GOOD but validation expects BAD) | Validation checks metric accuracy, not classification correctness. Allow reasoned deviations. |
| **No fallback strategy** | What if LLM produces invalid output after retry? | Add graceful degradation: after 2 retries, return raw data with "manual review needed" flag |
| **Funnel still Python** | `classify_funnel()` is hardcoded string matching | Acceptable for v1. Can move to LLM in future if patterns are ambiguous |
| **Multi-metric conflicts** | What if ROAS is great but CTR is terrible? | CoT step 6 (confidence) should note conflicting signals → MEDIUM confidence |

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
| OTB Prod API | Test fixtures only | Use response data to validate our classification logic |
| AI-first validation | Match production output schema | Analyze Agent should produce same fields as OTB API |

## Open Questions (Remaining)

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 6 | Meta OAuth scopes needed? | Hemanth | RESOLVED - see Meta API section |
| 7 | Meta Ad creatives access? | Hemanth | RESOLVED - see Meta API section |
| 8 | Demo scenario/script? | Jaidev | TL account showing $88k TikTok waste |

## Meta API Integration (RESOLVED)

### Facebook Login Pattern
From: `/Users/jaidevk/Work/dev/insights-dashboard/src/screens/LoginScreen.jsx`

**Frontend (simple redirect):**
```javascript
const handleFacebookLogin = () => {
  const facebookLoginUrl = buildUrl("auth/facebook", { redirectTo: returnUrl });
  window.open(facebookLoginUrl, "_self");
};
```

**Backend route needed:** `/auth/facebook` (Express/FastAPI OAuth handler)
- Redirects to Facebook OAuth
- Handles callback with token exchange
- Stores access token in session

### Meta Ad Creative Preview
From: `/Users/jaidevk/Work/dev/insights-dashboard/src/components/analytics/component-library/composites/AdPreview/`

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

**Backend endpoints needed:**
1. `GET /meta-ads/ads/{ad_id}` - Fetch ad details from Meta Marketing API
2. `GET /meta-ads/creative/{creative_id}/preview` - Fetch creative preview HTML

### Required Meta API Scopes
Based on the patterns, these scopes are needed:
- `ads_read` - Read ad account data
- `ads_management` - For Execute Agent (if doing real writes)
- `business_management` - Access business accounts

### Meta Marketing API Endpoints (Backend Implementation)
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

## Architecture (from requirements)

```
Meta OAuth → Agatha Orchestrator
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
ANALYZE         RECOMMEND        EXECUTE
(Meta/BQ read)  (AI analysis)   (Mock write)
```

## Team Feature Split

| Feature | Owner | Scope |
|---------|-------|-------|
| **Analyze flow** | Person A | BQ/Meta read → Analyze Agent → Analysis UI |
| **Recommend flow** | Person A | Recommend Agent → Recommendations UI |
| **Execute flow** | Person B | Execute Agent → Approval UI → Confirmation |
| **Foundation** | Person B | Scaffolding, session manager, base controller |
| **Auth/OAuth** | Person B | Meta OAuth integration |
| **Demo prep** | Both | Script, fallback, submission materials |

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

## BigQuery Data Access (RESOLVED)

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

### Sample Queries

**Ad Performance Query (Single Source):**
```sql
SELECT
    ad_name,
    ad_provider,
    SUM(spend) as total_spend,
    SUM(ROAS) as total_roas,
    SUM(ad_click) as clicks,
    AVG(CPC) as avg_cpc,
    AVG(CTR) as avg_ctr
FROM `otb-dev-platform.master.northstar_master_combined_tl`
WHERE data_source = 'Ad Providers'
  AND datetime_UTC >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY ad_name, ad_provider
ORDER BY total_spend DESC
```

**ROAS Calculation (Mixed Sources - Use CTEs):**
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

## AI-First Implementation Timeline

**Start:** Jan 31, 17:30 IST | **Demo:** Feb 1, 09:00 IST | **Available:** 15.5 hours

### Milestones & Gates

| Milestone | Target | Hours | Gate |
|-----------|--------|-------|------|
| Minimal setup + mock tool | Jan 31, 18:30 | 1h | - |
| **Analyze Agent + fixtures** | Jan 31, 21:00 | 2.5h | - |
| **GATE 1** | Jan 31, 21:30 | 0.5h | Grades match fixtures? |
| **Recommend Agent** | Jan 31, 23:30 | 2h | - |
| **GATE 2** | Feb 1, 00:00 | 0.5h | Recommendations sensible? |
| BigQuery tool + live data | Feb 1, 01:30 | 1.5h | - |
| **GATE 3** | Feb 1, 02:00 | 0.5h | Live data quality OK? |
| Execute Agent (mock) | Feb 1, 03:30 | 1.5h | - |
| FastAPI routes | Feb 1, 05:00 | 1.5h | - |
| Frontend basic UI | Feb 1, 06:30 | 1.5h | - |
| Integration & Testing | Feb 1, 07:30 | 1h | - |
| Demo ready | Feb 1, 08:30 | 1h | Buffer |
| **DEMO** | Feb 1, 09:00 | - | - |

### Gate Definitions (AI-First)

| Gate | Question | Pass Criteria | Fail Action |
|------|----------|---------------|-------------|
| **Gate 1** | Does Analyze Agent produce grounded, reasoned output? | (1) CoT reasoning chain complete (all 6 steps), (2) Cited metrics match source data, (3) Classifications are sensible given the reasoning | Fix prompt template, add more few-shot examples |
| **Gate 2** | Are recommendations grounded and actionable? | (1) Cites source metrics, (2) Shows calculation for impact, (3) Human review approves logic | Simplify recommendation prompt |
| **Gate 3** | Does live BigQuery data produce same quality? | Comparable output quality | Use fixtures for demo (fallback) |

**Key change from old gates:** We're testing LLM reasoning quality + grounding accuracy, not just whether output matches fixtures. The LLM should be able to handle novel data sensibly.

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

## Implementation Tasks (AI-First Order)

### Phase 1: AI Validation (17:30 - 00:00)

| Task | Description | Deliverable |
|------|-------------|-------------|
| **P1-1** | Minimal pyproject.toml + settings | Just enough to run agents |
| **P1-2** | Mock data tool (returns fixture JSON) | `get_ad_data()` tool |
| **P1-3** | Analyze Agent with AI-first prompts | See sub-tasks below |
| **P1-4** | GATE 1: Validate grounding + reasoning | CoT complete, metrics accurate |
| **P1-5** | Recommend Agent with grounded output | Budget recs with calculations |
| **P1-6** | GATE 2: Human review | Are recommendations actionable? |

#### P1-3 Sub-tasks (Analyze Agent)

| Sub-task | Description |
|----------|-------------|
| **P1-3a** | Create prompt templates with grounding rules, few-shot examples, CoT structure |
| **P1-3b** | Add validation layer: `validate_grounded_response()` in `backend/helpers/validators.py` |
| **P1-3c** | Update output schema to include `chain_of_thought` object |

#### P1-5 Sub-tasks (Recommend Agent)

| Sub-task | Description |
|----------|-------------|
| **P1-5a** | Recommendations must include source ad data + calculation |
| **P1-5b** | Dollar impact estimate for each recommendation |

### Phase 2: Data Integration (00:00 - 02:00)

| Task | Description | Deliverable |
|------|-------------|-------------|
| **P2-1** | BigQuery data tool | Real data connector |
| **P2-2** | Re-run agents with live data | Validate quality |
| **P2-3** | GATE 3: Quality check | Same output quality? |

### Phase 3: API & Execute (02:00 - 05:00)

| Task | Description | Deliverable |
|------|-------------|-------------|
| **P3-1** | Execute Agent (mock writes) | Confirmation messages |
| **P3-2** | FastAPI app + routes | `/analyze`, `/recommend`, `/execute` |
| **P3-3** | Session/state management | Request context |

### Phase 4: Frontend & Demo (05:00 - 08:30)

| Task | Description | Deliverable |
|------|-------------|-------------|
| **P4-1** | Minimal React frontend | Login, recommendations, execute |
| **P4-2** | Integration testing | E2E flow works |
| **P4-3** | Demo script + fallback | Prepared for anything |

## Legacy Task Mapping (Beads Issues)

For reference, original beads issues map to new phases:

| Original | New Phase | Status |
|----------|-----------|--------|
| HALO-E0 (Scaffolding) | P1-1, P1-2 | Minimal only |
| HALO-E1 (Foundation) | P2-1, P3-2, P3-3 | Deferred |
| HALO-E2 (Agents) | P1-3, P1-5, P3-1 | AI-first priority |
| HALO-E3 (Routes) | P3-2 | After agents validated |
| HALO-E4 (Frontend) | P4-1 | Last |
| HALO-E5 (Integration) | P4-2, P4-3 | Final |

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
│   │   ├── validators.py          # NEW: validate_grounded_response()
│   │   └── callback_helper.py     # Callbacks
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
    ├── requirements-agatha.md
    └── brainstorm-session-2025-01-31.md
```

## Key Patterns to Reuse (from otb-agents)

### Agent Definition
```python
from google.adk.agents import LlmAgent

class AnalyzeAgentModel:
    def __init__(self):
        self.agent = LlmAgent(
            name="analyze_agent",
            model="gemini-2.5-pro",
            description="...",
            instruction="...",
            tools=[get_ad_data_tool],
            before_agent_callback=transform_ad_data,
        )
```

### Controller Pattern
```python
class AgathaController(BaseController):
    async def run_analysis(self, request):
        return await self.run_agent_flow(
            agent_name="analyze_agent",
            agent=self.analyze_agent,
            message_content=json.dumps(request.dict()),
            initial_state={"account_id": request.account_id}
        )
```

### Tool Definition
```python
from google.adk.tools import FunctionTool

async def get_ad_data(account_id: str, days: int = 30) -> Dict:
    # Query BigQuery or Meta API
    ...

get_ad_data_tool = FunctionTool(func=get_ad_data)
```

## Good/Bad Spend Logic (AI-First)

**IMPORTANT:** Classification is done by the LLM, not Python functions. The thresholds below are GUIDELINES passed to the LLM prompt, not deterministic rules.

```python
# OLD APPROACH (WRONG - don't use):
# def classify_spend(ad_data, account_avg_roas):
#     if roas_ratio >= 2.0: return "GOOD"  # Rigid, no nuance

# NEW APPROACH (RIGHT):
# 1. Pass guidelines to LLM prompt (see ANALYZE_AGENT_PROMPT above)
# 2. LLM reasons about the data using CoT
# 3. Python validates that cited metrics match source data
# 4. Allow LLM judgment for edge cases

# Guidelines (not rules) for LLM:
CLASSIFICATION_GUIDELINES = {
    "GOOD": "ROAS >= 2× account avg, spend >= $1k, days >= 7",
    "OK": "ROAS 1-2× account avg, qualified",
    "WARNING": "ROAS 0.5-1× account avg, spend >= $10k",
    "BAD": "ROAS < 0.5× OR ROAS = 0 after $5k+",
    "WAIT": "spend < $1k OR days < 7"
}

# The LLM can deviate with reasoning, e.g.:
# "1.95× avg but strong upward trend → classifying as GOOD"
```

## Verification Steps

1. **Backend health**: `curl http://localhost:8000/`
2. **BigQuery connection**: Run analyze endpoint with test data
3. **Agent flow**: Check logs for Analyze → Recommend → Execute sequence
4. **Frontend**: Login → Dashboard → Recommendations → Execute flow
5. **Demo dry-run**: Full E2E with stopwatch (target < 60s)

## Dependencies Between Tasks (AI-First)

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
│   ├── test_grounding.py           # NEW: Test that responses cite accurate data
│   ├── test_cot_reasoning.py       # NEW: Test that reasoning chain is complete
│   ├── test_validators.py          # NEW: Test validate_grounded_response()
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
- Integration tests: Use `AsyncMock` for agent execution (like otb-agents)
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

### Deployment (Cloud Run - GCP)

```yaml
# cloudbuild.yaml
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

**Dockerfiles:**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install .
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

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

**Environment Variables (Cloud Run):**
- `AI_PROVIDER`: gemini | openai
- `GEMINI_MODEL`: gemini-2.5-pro
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `META_APP_ID`: Meta app credentials
- `META_APP_SECRET`: Meta app secret
- `FI_PROJECT_NAME`: Observability project name

## Test Fixtures (AI-First Validation)

The production OTB API responses serve as **target output format** for our Analyze Agent. Our classification logic should produce similar structures.

### Fixture Files
| File | Entity | Tenant | Use |
|------|--------|--------|-----|
| `tl_ad_performance_prod.json` | ads | ThirdLove | Expected output format for ad analysis |
| `wh_campaign_performance_prod.json` | campaigns | WhisperingHomes | Expected output format for campaign analysis |

### Target Output Schema (from production API)

Our Analyze Agent should produce output matching this structure:

```python
# Per-ad/campaign output
{
    # Identity
    "ad_name": str,
    "ad_id": str,
    "ad_provider": str,  # "Google Ads", "Facebook Ads", "TikTok Ads"

    # Raw metrics (from BigQuery)
    "Spend": float,
    "ROAS": float,
    "Purchases": int,
    "Conversion_Value": float,
    "CTR": float,
    "CPA": float,
    "days_active": int,

    # Computed classifications (Analyze Agent must produce these)
    "grade": str,                    # "A", "B", "C", "D"
    "performance_segment": str,      # "winners", "high_potential", "underperformers", "losers"
    "performance_detail": str,       # "top_5_percent", "top_20_percent", "above_median", "below_median"
    "recommended_action": str,       # "scale_budget", "continue_monitoring", "pause_and_review", "reduce_budget"

    # Statistical scores (Analyze Agent computes)
    "z_roas": float,                 # Z-score vs account average
    "z_ctr": float,
    "z_cpa": float,
    "Composite_Score": float,        # Multi-factor weighted score

    # Creative status (for fatigue detection)
    "creative_status": str,          # "multi_variant_winner", "needs_testing", "fatigued"
    "creative_variants": int,
}
```

### Classification Approach (AI-First)

**OLD (Rules Engine):** Python functions `assign_grade()`, `assign_segment()`, `assign_action()` with hardcoded thresholds.

**NEW (AI-First):** LLM reasons about the data and produces classifications. Python only validates that:
1. Cited metrics match source data
2. CoT reasoning chain is complete
3. Output schema is correct

```python
# These are OUTPUT FIELDS the LLM should produce, not Python functions to run:
OUTPUT_SCHEMA = {
    "grade": "A|B|C|D",                          # LLM assigns based on reasoning
    "performance_segment": "winners|high_potential|underperformers|losers",
    "recommended_action": "scale_budget|continue_monitoring|reduce_budget|pause_and_review",
    "chain_of_thought": {                        # Required for explainability
        "step_1_data": {},
        "step_2_comparison": {},
        "step_3_qualification": {},
        "step_4_classification": {},
        "step_5_recommendation": {},
        "step_6_confidence": {}
    }
}

# Validation function (runs AFTER LLM response):
def validate_analyze_output(llm_response: dict, source_data: dict) -> tuple[bool, list[str]]:
    """
    Checks:
    1. All required fields present
    2. Cited metrics match source data (within tolerance)
    3. CoT chain is complete

    Does NOT check:
    - Whether classification is "correct" (LLM judgment allowed)
    """
    # See backend/helpers/validators.py for implementation
    pass
```

### Test Strategy

1. **Unit tests**: Validate classification functions against fixture data
   ```python
   def test_grade_assignment():
       # From tl_ad_performance_prod.json, ad "Thirdlove® Bras"
       assert assign_grade(1.29) == "A"

   def test_segment_assignment():
       # From fixture, percentile_rank=0 (top performer)
       segment, detail = assign_segment(0.0)
       assert segment == "winners"
       assert detail == "top_5_percent"
   ```

2. **Integration tests**: Run Analyze Agent on BigQuery data, compare output structure to fixtures

3. **Golden tests**: Snapshot test agent output against fixture format (not exact values)

### Composite Score (Optional)

For compatibility with existing OTB API output format, we MAY include composite scores. However, the primary classification should come from LLM reasoning, not formula output.

```python
# If needed for API compatibility, this can be computed as a HELPER:
def calculate_composite_score(z_roas, z_ctr, z_cpa, confidence_weight=1.0):
    """Optional helper for API compatibility. NOT the primary classification method."""
    weights = {"roas": 0.5, "ctr": 0.3, "cpa": 0.2}
    raw_score = weights["roas"] * z_roas + weights["ctr"] * z_ctr - weights["cpa"] * z_cpa
    return round(raw_score * confidence_weight, 2)

# PRIMARY APPROACH: LLM reasons about all metrics holistically
# - Can weigh metrics differently based on context
# - Can note conflicting signals (high ROAS but dropping CTR)
# - Can incorporate trends, not just point-in-time values
```

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Meta API complexity | Use BigQuery as primary for dev, Meta for demo |
| Time pressure | Minimal UI, use component library (shadcn) |
| Integration bugs | Buffer time, fallback demo script |
| OAuth issues | Pre-authenticate test account |
| Cloud Run cold start | Keep backend warm with health checks |
| Secret management | Use GCP Secret Manager |
| LLM hallucination | Validation layer checks cited metrics match source data |
| Unexplainable decisions | CoT reasoning chain required in all outputs |

---

## AI-First Verification Checklist

Before demo, verify:

- [ ] Analyze Agent outputs include `chain_of_thought` object with all 6 steps
- [ ] Every metric cited in reasoning matches source data (within tolerance)
- [ ] Recommendations include dollar impact calculations
- [ ] `validate_grounded_response()` catches fabricated metrics (test with bad data)
- [ ] Few-shot examples produce expected classifications
- [ ] User-facing explanations are clear and cite specific numbers
- [ ] Edge cases handled sensibly (borderline thresholds, zero ROAS, new ads)

---

## Summary: AI-First vs Rules-Based

| Aspect | Rules-Based (Old) | AI-First (New) |
|--------|-------------------|----------------|
| Classification | Python `if/else` | LLM reasoning with guidelines |
| Edge cases | Falls through to default | LLM uses judgment |
| Explanations | Template strings | Natural language citing data |
| Validation | Match fixtures exactly | Grounding check + sensible reasoning |
| Extensibility | Change Python code | Update prompt guidelines |
| Trust | "The algorithm said so" | "Here's the reasoning, verify yourself" |
