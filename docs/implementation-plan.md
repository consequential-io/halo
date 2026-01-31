# Agatha Implementation Plan

## Overview
Multi-agent ad spend optimization system for hackathon demo (Feb 1, 09:00 IST)

## Decisions Made

| # | Question | Decision |
|---|----------|----------|
| Team split | Both fullstack, split by feature | Each owns E2E features |
| Data source | Meta API (demo) + BigQuery (dev/test/fallback) | BQ has both Meta & Google data |
| AI Model | Config-driven | Switch between Gemini/OpenAI via env var |
| Execute actions | Mock write for hackathon | Real API stretch goal |

## Open Questions (Remaining)

| # | Question | Owner | Suggested Default |
|---|----------|-------|-------------------|
| 6 | Meta OAuth scopes needed? | Hemanth | `ads_read`, `ads_management` |
| 8 | Demo scenario/script? | Jaidev | TL account showing $88k TikTok waste |

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

## Implementation Tasks (Beads Issues)

### Epic: HALO-E0 - Project Scaffolding (Create Extensible Structure)

| Task | Description | Deliverable | Open Questions |
|------|-------------|-------------|----------------|
| **HALO-0.1** | Create backend directory structure | All `__init__.py` files, empty modules | None |
| **HALO-0.2** | Create `pyproject.toml` with dependencies | google-adk, fastapi, uvicorn, httpx, pydantic | Which google-adk version? Check otb-agents |
| **HALO-0.3** | Create `.env.example` with all env vars | Template for local dev | Need full list of secrets |
| **HALO-0.4** | Create frontend with Next.js scaffold | `npx create-next-app@latest` | Use App Router or Pages? (App Router recommended) |
| **HALO-0.5** | Create stub files for all modules | Empty classes/functions with docstrings | None |
| **HALO-0.6** | Setup pytest and test directory structure | `conftest.py`, sample test | None |
| **HALO-0.7** | Create Dockerfiles (backend + frontend) | Working docker build | Base image versions? |
| **HALO-0.8** | Create `cloudbuild.yaml` | Deploy config | Which GCP project? Region? |

### Epic: HALO-E1 - Backend Foundation

| Task | Description | Deliverable | Open Questions |
|------|-------------|-------------|----------------|
| **HALO-1** | Implement `config/settings.py` | Pydantic Settings with env vars | Full list of config keys needed? |
| **HALO-2** | Implement `config/session_manager.py` | Singleton SessionManager class | Same pattern as otb-agents? |
| **HALO-3** | Implement `config/logging_config.py` | JSON formatter, setup function | Log level configurable via env? |
| **HALO-4** | Implement `controllers/base_controller.py` | `run_agent_flow()` method | Copy from otb-agents or adapt? |
| **HALO-5** | Implement `main.py` | FastAPI app with health endpoint | CORS settings for frontend? |

**Open Questions for E1:**
- [ ] Do we need authentication middleware for API routes?
- [ ] Should we add rate limiting?
- [ ] Error response schema - match otb-agents or custom?

### Epic: HALO-E2 - Data Tools

| Task | Description | Deliverable | Open Questions |
|------|-------------|-------------|----------------|
| **HALO-6** | Implement BigQuery connector tool | `get_ad_data_from_bq()` function | Which BQ dataset/table? Need credentials path |
| **HALO-7** | Implement Meta API read tool | `get_ad_data_from_meta()` function | OAuth token storage? Refresh flow? |
| **HALO-8** | Implement data source router | Auto-select Meta vs BQ based on availability | Fallback logic - timeout or error-based? |
| **HALO-9** | Create test fixtures from BQ data | JSON files with sample ad data | Which accounts to export? TL + WH? |

**Open Questions for E2:**
- [ ] BigQuery: Which project/dataset/table contains the ad data?
- [ ] BigQuery: Service account key or ADC for auth?
- [ ] Meta API: App ID and App Secret - where stored?
- [ ] Meta API: Which API version? (v18.0, v19.0?)
- [ ] Data schema: Need to map BQ fields to Meta API fields?

### Epic: HALO-E3 - Agents

| Task | Description | Deliverable | Open Questions |
|------|-------------|-------------|----------------|
| **HALO-10** | Implement Analyze Agent | `AnalyzeAgentModel` class with prompt | Prompt template - where to store? |
| **HALO-11** | Implement `classify_spend()` logic | Pure function with thresholds | Thresholds configurable via env? |
| **HALO-12** | Implement Recommend Agent | `RecommendAgentModel` class with prompt | How detailed should recommendations be? |
| **HALO-13** | Implement creative fatigue detection | Function to flag fatigued creatives | CTR decline threshold - 30% correct? |
| **HALO-14** | Implement Execute Agent | `ExecuteAgentModel` with mock write | Mock response format? |
| **HALO-15** | Implement Agatha Orchestrator | `AgathaController` coordinating all agents | Sequential or can agents run in parallel? |

**Open Questions for E3:**
- [ ] Prompt storage: Inline in code, or external files/service (like fi.prompt)?
- [ ] Agent instructions: How detailed? Include examples in prompt?
- [ ] Output format: JSON schema for each agent's response?
- [ ] Error handling: What if one agent fails mid-flow?
- [ ] Session state: What data passes between agents?

### Epic: HALO-E4 - API Routes

| Task | Description | Deliverable | Open Questions |
|------|-------------|-------------|----------------|
| **HALO-16** | Implement `/auth/meta/login` | Redirect to Meta OAuth | Callback URL for hackathon? |
| **HALO-17** | Implement `/auth/meta/callback` | Handle OAuth callback, store token | Token storage - session? DB? Memory? |
| **HALO-18** | Implement `/api/analyze` | Trigger analysis, return results | Sync or async? Polling for results? |
| **HALO-19** | Implement `/api/recommendations` | Get recommendations for account | Pagination needed? |
| **HALO-20** | Implement `/api/execute` | Execute approved recommendations | Request body schema? |
| **HALO-21** | Implement `/api/accounts` | List connected ad accounts | Cache account list? |

**Open Questions for E4:**
- [ ] Auth: Protect routes with OAuth token validation?
- [ ] CORS: Allow frontend origin only?
- [ ] Response schema: Pydantic models for all responses?
- [ ] Async execution: Long-running analysis - websocket or polling?

### Epic: HALO-E5 - Frontend (Minimal)

| Task | Description | Deliverable | Open Questions |
|------|-------------|-------------|----------------|
| **HALO-22** | Setup shadcn/ui components | Install and configure | Which components needed? |
| **HALO-23** | Implement Login page | Meta OAuth button, redirect | Branding/logo for demo? |
| **HALO-24** | Implement Dashboard layout | Header, sidebar, main content area | Show account selector in header? |
| **HALO-25** | Implement Analysis view | Display analysis results | Visualization - charts or tables? |
| **HALO-26** | Implement Recommendations list | Cards with approve/reject buttons | Bulk approve option? |
| **HALO-27** | Implement Execution confirmation | Success/failure messages | Animation/celebration on success? |
| **HALO-28** | Implement API client | Fetch wrapper with auth headers | Use SWR or React Query? |

**Open Questions for E5:**
- [ ] Styling: Tailwind default or custom theme?
- [ ] State management: React Context sufficient or need Zustand?
- [ ] Loading states: Skeleton loaders or spinners?
- [ ] Error handling: Toast notifications or inline errors?

### Epic: HALO-E6 - Integration & Demo

| Task | Description | Deliverable | Open Questions |
|------|-------------|-------------|----------------|
| **HALO-29** | Write unit tests for classify_spend | pytest tests with edge cases | Coverage target? |
| **HALO-30** | Write integration tests for agent flow | AsyncMock-based tests | Which scenarios to test? |
| **HALO-31** | Create demo script | Step-by-step demo walkthrough | Demo duration target? |
| **HALO-32** | Record fallback demo video | Screen recording if live fails | Loom or local recording? |
| **HALO-33** | Write README.md | Project overview, setup instructions | Include architecture diagram? |
| **HALO-34** | Create pitch deck (6 slides) | Problem, Insight, Demo, Tech, Value, Next | Use existing template? |
| **HALO-35** | Write AI Impact Statement | 200 words on AI usage | Guardrails section - what to include? |

**Open Questions for E6:**
- [ ] Demo account: Use real TL/WH data or synthetic?
- [ ] Demo scenario: Show $88k TikTok waste discovery?
- [ ] Fallback: Pre-recorded or BigQuery-backed live?

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

## Dependencies Between Tasks

```
HALO-E0 (Scaffolding: 0.1-0.8)
    │
    ├── HALO-E1 (Foundation: 1-5)
    │       │
    │       └── HALO-E2 (Data Tools: 6-9)
    │               │
    │               └── HALO-E3 (Agents: 10-15)
    │                       │
    │                       └── HALO-E4 (Routes: 16-21)
    │
    └── HALO-E5 (Frontend: 22-28) ──── depends on E4 routes
            │
            └── HALO-E6 (Integration: 29-35)
```

**Parallel Work Opportunities:**
- E0 (Scaffolding) → can split between team members
- E1 + E5 initial setup → can run in parallel
- E2 (BQ tool) + E2 (Meta tool) → can run in parallel
- E3 (Agents) → sequential (Analyze → Recommend → Execute)
- E6 (Tests + Demo prep) → can start once E3 is done

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

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Meta API complexity | Use BigQuery as primary for dev, Meta for demo |
| Time pressure | Minimal UI, use component library (shadcn) |
| Integration bugs | Buffer time, fallback demo script |
| OAuth issues | Pre-authenticate test account |
| Cloud Run cold start | Keep backend warm with health checks |
| Secret management | Use GCP Secret Manager |
