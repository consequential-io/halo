# Agatha Implementation Plan

## Overview
Multi-agent ad spend optimization system for hackathon demo (Feb 1, 09:00 IST)

**Approach:** AI-First Implementation (validate AI value before infrastructure)

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

### Gate Definitions

| Gate | Question | Pass | Fail Action |
|------|----------|------|-------------|
| **Gate 1** | Does Analyze Agent produce correct grades vs fixtures? | Grades/segments match production API | Fix classification logic before proceeding |
| **Gate 2** | Are recommendations actionable and sensible? | Human review approves | Simplify recommendation logic |
| **Gate 3** | Does live BigQuery data produce same quality? | Comparable output | Use fixtures for demo (fallback) |

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
| **P1-3** | Analyze Agent with classification logic | Grades, segments, scores |
| **P1-4** | GATE 1: Validate vs fixtures | Compare output to production API |
| **P1-5** | Recommend Agent | Budget + creative recommendations |
| **P1-6** | GATE 2: Human review | Are recommendations actionable? |

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

## Good/Bad Spend Logic (from brainstorm)

```python
def classify_spend(ad_data, account_avg_roas):
    roas_ratio = ad_data['roas'] / account_avg_roas
    spend = ad_data['spend']
    days = ad_data['days_running']

    if days < 7 or spend < 1000:
        return "WAIT"  # Learning phase

    if ad_data['roas'] == 0 and spend >= 5000:
        return "BAD"   # Pause

    if roas_ratio >= 2.0:
        return "GOOD"  # Scale 30-100%
    elif roas_ratio >= 1.0:
        return "OK"    # Monitor
    elif roas_ratio >= 0.5:
        return "WARNING"  # Review
    else:
        return "BAD"   # Reduce 50%
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

### Classification Mapping (AI-First Logic)

The Analyze Agent should implement these mappings:

```python
# Grade assignment based on Composite_Score
def assign_grade(composite_score: float) -> str:
    if composite_score >= 1.0:
        return "A"
    elif composite_score >= 0.7:
        return "B"
    elif composite_score >= 0.4:
        return "C"
    else:
        return "D"

# Performance segment based on percentile rank
def assign_segment(percentile_rank: float) -> tuple[str, str]:
    if percentile_rank <= 0.05:
        return ("winners", "top_5_percent")
    elif percentile_rank <= 0.20:
        return ("winners", "top_20_percent")
    elif percentile_rank <= 0.50:
        return ("high_potential", "above_median")
    elif percentile_rank <= 0.80:
        return ("underperformers", "below_median")
    else:
        return ("losers", "bottom_20_percent")

# Recommended action based on grade + segment
def assign_action(grade: str, segment: str, days_active: int) -> str:
    if days_active < 7:
        return "learning_phase"
    if grade == "A" and segment == "winners":
        return "scale_budget"
    elif grade in ("A", "B"):
        return "continue_monitoring"
    elif grade == "C":
        return "optimize_creative"
    else:  # D
        return "pause_and_review"
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

### Composite Score Calculation

Reverse-engineered from production API patterns:

```python
def calculate_composite_score(
    z_roas: float,
    z_ctr: float,
    z_cpa: float,
    confidence_weight: float = 1.0
) -> float:
    """
    Weighted combination of z-scores.
    Higher ROAS and CTR are good, lower CPA is good.
    """
    weights = {
        "roas": 0.5,   # Revenue efficiency most important
        "ctr": 0.3,    # Engagement signal
        "cpa": 0.2,    # Cost efficiency (inverted)
    }

    raw_score = (
        weights["roas"] * z_roas +
        weights["ctr"] * z_ctr -
        weights["cpa"] * z_cpa  # Subtract because lower CPA is better
    )

    return round(raw_score * confidence_weight, 2)
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
| Classification drift | Validate against production API fixtures |
