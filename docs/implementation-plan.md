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
        "model": os.getenv("GEMINI_MODEL", "gemini-3.0"),
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
            model="gemini-3.0",
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
- `GEMINI_MODEL`: gemini-3.0
- `GOOGLE_CLOUD_PROJECT`: otb-dev-platform
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

### Approach: Anomaly Detection + RCA (SME Validated)

**Key Insight from SME:** "The goal is to find anomalies... there is no concept of leakage... it's spend RCA or CPA std deviation. The goal is to find ontology, not so much an idea of what the metrics are."

Instead of fixed classification rules, Agatha uses **statistical anomaly detection** with **deep RCA** and **ontology-based exploration**.

```
Ad Data → Statistical Analysis → Anomalies Surfaced → Deep RCA → Actionable Insights
```

### Agent Tools Architecture

| Tool | Purpose | When Used |
|------|---------|-----------|
| `detect_anomalies` | Find ads with metrics >Nσ from baseline | Initial analysis |
| `get_ontology` | Hierarchical breakdown by dimensions | Understanding structure |
| `run_rca` | Deep root cause analysis on anomaly | Explaining why |
| `get_ad_data` | Fetch raw ad data from BQ/fixtures | Data retrieval |

### Tool 1: Anomaly Detection

```python
async def detect_anomalies(
    ads: List[dict],
    metric: str,                    # "spend" | "cpa" | "roas" | "ctr" | "cvr"
    threshold_sigma: float = 2.0,   # Standard deviations from mean
    direction: str = "both",        # "high" | "low" | "both"
    min_spend: float = 100,         # Minimum spend to consider
    config: dict = ANOMALY_CONFIG
) -> dict:
    """
    Find ads where metric deviates significantly from baseline.

    Returns:
        {
            "anomalies": [
                {
                    "ad": {...},
                    "metric": "cpa",
                    "value": 45.2,
                    "baseline": 19.1,
                    "z_score": 2.3,
                    "direction": "high",
                    "severity": "significant"  # "mild" | "significant" | "extreme"
                }
            ],
            "baseline_stats": {
                "mean": 19.1,
                "std": 11.3,
                "median": 17.5,
                "count": 128
            }
        }
    """
```

### Tool 2: Ontology (Expanded Scope)

```python
async def get_ontology(
    ads: List[dict],
    group_by: List[str],            # Dimensions to group by
    metrics: List[str] = None,      # Metrics to aggregate
    config: dict = ONTOLOGY_CONFIG
) -> dict:
    """
    Return hierarchical breakdown of ad data by dimensions.

    Supported dimensions (expanded scope):
    - "ad_provider"     # Google Ads, Facebook Ads, TikTok Ads
    - "store"           # US, IND (market)
    - "ad_type"         # Static, Video, Shopping, Performance Max
    - "creative_status" # multi_variant_winner, needs_testing, fatigued
    - "spend_tier"      # High, Medium, Low
    - "campaign_status" # ACTIVE, PAUSED, REMOVED
    - "performance_segment"  # winners, high_potential, underperformers, losers

    Returns:
        {
            "breakdown": {
                "Google Ads": {
                    "count": 45,
                    "total_spend": 125000,
                    "avg_roas": 2.3,
                    "avg_cpa": 18.5,
                    "anomaly_count": 3
                },
                "Facebook Ads": {...},
                "TikTok Ads": {...}
            },
            "dimensions_used": ["ad_provider"],
            "total_ads": 128
        }
    """
```

### Tool 3: Deep RCA (Root Cause Analysis)

```python
async def run_rca(
    anomaly_ad: dict,
    all_ads: List[dict],
    anomaly_metric: str,
    config: dict = RCA_CONFIG
) -> dict:
    """
    Deep root cause analysis for an anomalous ad.

    Analysis dimensions:
    1. Placement analysis (where is spend going?)
    2. Audience analysis (audience_engagement_score, competitive_pressure)
    3. Creative analysis (creative_variants, unique_creatives, creative_status)
    4. Budget analysis (budget_utilization, daily_spend_velocity, avg_daily_budget)
    5. Comparison to similar ads (same provider, same store, same ad_type)

    Returns:
        {
            "anomaly_summary": {
                "ad_name": "Floor Lamps Campaign",
                "metric": "cpa",
                "value": 45.2,
                "baseline": 19.1,
                "deviation": "+137%"
            },
            "root_causes": [
                {
                    "factor": "audience_engagement",
                    "finding": "Audience engagement score is 12.3 vs platform avg 25.5",
                    "impact": "high",
                    "suggestion": "Review audience targeting"
                },
                {
                    "factor": "creative_fatigue",
                    "finding": "Single creative variant running for 45 days",
                    "impact": "medium",
                    "suggestion": "Test new creative variants"
                },
                {
                    "factor": "competitive_pressure",
                    "finding": "Competitive pressure 0.85 (high) vs avg 0.45",
                    "impact": "medium",
                    "suggestion": "Consider different auction times or placements"
                }
            ],
            "comparison_to_similar": {
                "same_provider_avg_cpa": 22.1,
                "same_store_avg_cpa": 20.5,
                "same_ad_type_avg_cpa": 18.9
            },
            "recommended_actions": [
                "Review audience targeting settings",
                "Add 2-3 new creative variants",
                "Consider reducing daily budget until CPA stabilizes"
            ]
        }
    """
```

### Config (Anomaly Detection)

```python
# config/anomaly_config.py

ANOMALY_CONFIG = {
    "default_threshold_sigma": 2.0,
    "severity_levels": {
        "mild": 1.5,       # 1.5-2σ
        "significant": 2.0, # 2-3σ
        "extreme": 3.0,     # >3σ
    },
    "metrics": {
        "spend": {"direction": "high", "min_value": 100},
        "cpa": {"direction": "high", "min_value": 0},
        "roas": {"direction": "low", "min_value": 0},
        "ctr": {"direction": "both", "min_value": 0},
        "cvr": {"direction": "both", "min_value": 0},
    },
    "min_sample_size": 10,  # Minimum ads for meaningful σ calculation
}

ONTOLOGY_CONFIG = {
    "dimensions": [
        "ad_provider",
        "store",
        "ad_type",
        "creative_status",
        "spend_tier",
        "campaign_status",
        "performance_segment",
    ],
    "default_metrics": ["Spend", "ROAS", "CPA", "CTR"],
}

RCA_CONFIG = {
    "analysis_dimensions": [
        "audience_engagement_score",
        "competitive_pressure",
        "creative_variants",
        "unique_creatives",
        "creative_status",
        "budget_utilization",
        "daily_spend_velocity",
        "days_active",
        "recency",
    ],
    "comparison_dimensions": ["ad_provider", "store", "ad_type"],
    "impact_thresholds": {
        "high": 0.5,    # >50% deviation from baseline
        "medium": 0.25, # 25-50% deviation
        "low": 0.1,     # 10-25% deviation
    },
}
```

### Example Agent Flow

```
User: "Analyze my ad account for waste"

Analyze Agent:
1. get_ad_data(account_id="tl", days=30)
2. detect_anomalies(ads, metric="cpa", direction="high")
   → Found 5 ads with CPA >2σ above baseline
3. detect_anomalies(ads, metric="roas", direction="low")
   → Found 3 ads with ROAS >2σ below baseline (1 overlap)
4. get_ontology(ads, group_by=["ad_provider"])
   → TikTok Ads: 4 of 7 anomalies (57%)
5. run_rca(worst_anomaly, all_ads, "cpa")
   → Root cause: Low audience engagement + single creative

Agent Response:
"Found 7 anomalous ads representing potential waste:
- 4 TikTok ads with CPA 2-3x higher than baseline ($45 vs $19 avg)
- Root cause analysis shows low audience engagement and creative fatigue
- Recommendation: Pause 'Floor Lamps TikTok' campaign, test new creatives"
```

### Anomaly Output Schema

```python
# What the Analyze Agent surfaces (not fixed classifications)
{
    "anomalies": [
        {
            "ad_id": "12345",
            "ad_name": "Floor Lamps TikTok",
            "anomaly_type": "high_cpa",
            "severity": "significant",
            "metrics": {
                "cpa": {"value": 45.2, "baseline": 19.1, "z_score": 2.3},
                "roas": {"value": 0.3, "baseline": 2.1, "z_score": -1.8},
            },
            "rca_summary": "Low audience engagement + creative fatigue",
            "suggested_actions": ["Pause campaign", "Test new creatives"],
            "potential_waste": 8500  # Estimated $ waste if continued
        }
    ],
    "ontology_insights": {
        "worst_provider": "TikTok Ads",
        "worst_dimension_breakdown": {...}
    },
    "summary": {
        "total_anomalies": 7,
        "total_potential_waste": 28500,
        "top_recommendation": "Review TikTok ad targeting"
    }
}

### Test Strategy

1. **Unit tests**: Validate anomaly detection against fixture data
   ```python
   def test_detect_cpa_anomalies():
       # From tl_ad_performance_prod.json
       ads = load_fixture("tl_ad_performance_prod.json")
       result = detect_anomalies(ads, metric="cpa", threshold_sigma=2.0)
       # Should find ads with z_cpa > 2.0
       assert len(result["anomalies"]) > 0
       for anomaly in result["anomalies"]:
           assert abs(anomaly["z_score"]) >= 2.0

   def test_ontology_by_provider():
       ads = load_fixture("tl_ad_performance_prod.json")
       result = get_ontology(ads, group_by=["ad_provider"])
       assert "Google Ads" in result["breakdown"]
       assert "total_spend" in result["breakdown"]["Google Ads"]

   def test_rca_identifies_factors():
       ads = load_fixture("tl_ad_performance_prod.json")
       anomaly = detect_anomalies(ads, metric="cpa", direction="high")["anomalies"][0]
       rca = run_rca(anomaly["ad"], ads, "cpa")
       assert "root_causes" in rca
       assert len(rca["recommended_actions"]) > 0
   ```

2. **Integration tests**: Run Analyze Agent on fixture data, verify anomalies match production z-scores

3. **Golden tests**: Validate that high z_cpa ads are surfaced as anomalies

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
