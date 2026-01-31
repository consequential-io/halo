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

### Epic: HALO-E1 - Backend Foundation
1. **HALO-1**: Project scaffolding (pyproject.toml, FastAPI app structure)
2. **HALO-2**: Session manager (singleton pattern from otb-agents)
3. **HALO-3**: Base controller with `run_agent_flow()`
4. **HALO-4**: BigQuery data connector tool
5. **HALO-5**: Meta API read connector tool (with OAuth)

### Epic: HALO-E2 - Agents
6. **HALO-6**: Analyze Agent - classify spend as good/bad/monitor
7. **HALO-7**: Recommend Agent - generate budget + creative recommendations
8. **HALO-8**: Execute Agent - mock write with confirmation
9. **HALO-9**: Agatha Orchestrator - coordinate agent flow

### Epic: HALO-E3 - API Routes
10. **HALO-10**: `/auth/meta` - OAuth flow
11. **HALO-11**: `/analyze` - trigger analysis
12. **HALO-12**: `/recommendations` - get recommendations
13. **HALO-13**: `/execute` - approve and execute

### Epic: HALO-E4 - Frontend (Minimal)
14. **HALO-14**: Login page with Meta OAuth button
15. **HALO-15**: Dashboard with account selector
16. **HALO-16**: Recommendations view with approve/reject
17. **HALO-17**: Execution confirmation view

### Epic: HALO-E5 - Integration & Demo
18. **HALO-18**: End-to-end integration testing
19. **HALO-19**: Demo script and fallback preparation
20. **HALO-20**: README and submission materials

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
HALO-1 (scaffolding)
    └── HALO-2 (session) + HALO-3 (base controller)
           └── HALO-4 (BQ tool) + HALO-5 (Meta tool)
                  └── HALO-6 (Analyze) → HALO-7 (Recommend) → HALO-8 (Execute)
                         └── HALO-9 (Orchestrator)
                                └── HALO-10-13 (Routes)
                                       └── HALO-14-17 (Frontend)
                                              └── HALO-18-20 (Integration)
```

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
