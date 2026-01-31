# Agatha - Ad Spend Optimization Agent

## Session Context
- **Date:** 2025-01-31
- **Demo deadline:** 9am IST, Feb 1st (~22.5 hours from session start)
- **Team:** 2 people (Jaidev + 1 teammate)
- **Hackathon:** AIBoomi, Pune
- **Category:** Commerce / Shopping / Consumer

---

## Project Overview

**Problem:** Ecommerce brands struggle to optimize ad spend across platforms. They need to know where to increase spend (good ROI) and where to cut (wasteful spend).

**Solution:** Agatha - an AI agent that analyzes ad spend, evaluates performance, and recommends/executes optimizations.

**Target Users:** Ecommerce brands scaling via paid ad channels (Google Ads, Meta Ads)

---

## Requirements Gathered

### Data Sources
- **BigQuery:** Test data available for Google & Meta ads
- **Live API:** Meta direct integration OR via Supermetrics for demo
- **Schema:** TBD - need to confirm available fields

### Architecture - Multi-Agent System

```
User Login (Meta OAuth)
        │
        ▼
┌───────────────────┐
│   Analyze Agent   │ ← Analyzes ad performance data
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  Recommend Agent  │ ← Generates optimization recommendations
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   User Review     │ ← Human-in-the-loop approval
│   (Aha Moment)    │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   Execute Agent   │ ← Executes approved changes via API
└───────────────────┘

Agatha = Orchestrator coordinating the above agents
```

### "Aha Moment" Priorities
1. **Primary:** Identify "good" ad spend - opportunities to increase conversions by increasing spend
2. **Secondary:** Identify "bad" ad spend - wasteful spend not resulting in conversions (should be stopped)

### Tech Stack (Confirmed)
- **Backend:** Python + FastAPI + Google ADK (reuse patterns from `/Users/jaidevk/Work/dev/otb-agents`)
- **Frontend:** TypeScript (Next.js likely)
- **Models:** Gemini or OpenAI (have OpenAI credits)
- **Observability:** OpenTelemetry (from existing patterns)

### Agent Capabilities
| Agent | Input | Output | Actions |
|-------|-------|--------|---------|
| Analyze | Ad data from BigQuery/API | Performance analysis, spend classification | Read-only |
| Recommend | Analysis output | Actionable recommendations (increase/decrease/pause) | Read-only |
| Execute | Approved recommendations | Execution status | Write to Meta/Google APIs |

### Implementation Phases
1. **Phase 1:** Option 2 - Analyze + Execute with human approval
2. **Phase 2:** Option 3 - Fully autonomous (stretch goal if time permits)

---

## Open Questions (To Resolve)

### Data Schema ✅ (Validated from BigQuery exports)

**Available fields:**
- [x] spend, return_on_ad_spend_roas, impressions, clicks, ctr, cpc, cpm
- [x] datetime_PST/IST, ad_name, ad_group_name, customer_lastVisit_campaign
- [x] ad_provider (Google Ads, Facebook Ads, TikTok Ads)
- [x] creative_object_type (Search, Shopping, Video, SHARE, Performance Max)
- [x] store (market: US, IND)
- [x] customer_entry_page (landing page URL)
- [ ] ❌ conversion count — NOT available (limits CVR/CPA analysis)

**Granularity:** Ad level (daily)

**Historical data:**
- WH: 76 days (Nov 2025 - Jan 2026)
- TL: 298 days (Apr 2025 - Jan 2026)

**Conversion tracking:** ROAS available but not conversion count

### "Good" vs "Bad" Ad Spend Definition ✅ (Data-Validated)

> **Key Insight:** Good/bad is relative to account average, not fixed numbers.

**🟢 GOOD SPEND** (Scale up 30-100%)
```
ROAS >= 2× account average
AND spend >= $1,000
AND running >= 7 days
```

Examples validated:
- TL: "Thirdlove® Bras" — $212k spend, 29.58 ROAS (4.3× avg)
- WH: "Whispering Homes" — ₹426k spend, 8.12 ROAS (4.5× avg)

**🔴 BAD SPEND** (Pause or reduce 50-100%)
```
ROAS = 0 after $5k+ spend AND 7+ days
OR ROAS < 0.5× account average after $10k+
OR ROAS declining 3+ consecutive weeks
```

Examples validated:
- TL: TikTok ads — $88k spend, 0.00 ROAS (entire channel failing)
- WH: Floor Lamps Carousel — ₹55k spend, 0.00 ROAS after 28 days

**Decision Matrix:**
| ROAS vs Avg | Spend | Days | Status | Action |
|-------------|-------|------|--------|--------|
| >= 2× | >= $1k | >= 7 | 🟢 GOOD | Scale 30-100% |
| 1× - 2× | >= $1k | >= 7 | 🟡 OK | Monitor |
| 0.5× - 1× | >= $10k | >= 7 | 🟠 WARNING | Review |
| < 0.5× | >= $10k | >= 7 | 🔴 BAD | Reduce 50% |
| = 0 | >= $5k | >= 7 | 🔴 BAD | Pause |
| Any | < $1k | < 7 | ⚪ WAIT | Need more data |

**Available Metrics:**
- ✅ spend, ROAS, impressions, clicks, CTR, CPC
- ❌ conversion count, CVR, CPA (not in BigQuery data)

**Thresholds:**
- Learning phase: 7 days (don't judge too early)
- Significant change: z-score 1.5 (not 7% — too sensitive given volatility)
- Zero ROAS alert: after $5k spend AND 7 days

### Meta Integration
- [ ] Direct Meta Marketing API vs Supermetrics?
- [ ] What OAuth scopes needed?
- [ ] What actions can Execute agent perform? (pause ads? adjust budget? change bids?)

### Team Division
- [ ] How to split work between 2 teammates?
- [ ] Who handles backend vs frontend?

### Demo Flow
- [ ] What's the demo scenario/script?
- [ ] Sample account/data for live demo?
- [ ] Fallback if live API fails?

---

## Reference Architecture (from otb-agents)

The existing codebase at `/Users/jaidevk/Work/dev/otb-agents` provides:

### Patterns to Reuse
- **Agent Definition:** `LlmAgent` with tools and callbacks
- **Controller Pattern:** `BaseController` with `run_agent_flow()`
- **Session Management:** `InMemorySessionService` singleton
- **Tool Definition:** `FunctionTool` wrapping async functions
- **Callback Pattern:** `before_agent_callback` for data transformation
- **API Structure:** FastAPI routes → controllers → agent models
- **Testing:** pytest with AsyncMock for integration tests
- **Observability:** OpenTelemetry with Google ADK instrumentation

### Key Files to Reference
- `models/*_agent.py` - Agent definitions
- `controllers/base_controller.py` - Common execution flow
- `helpers/tools.py` - Tool definitions
- `helpers/callback_helper.py` - Callback utilities
- `config/session_manager.py` - Session handling
- `main.py` - App initialization

---

## Next Steps

1. **Resolve open questions** (data schema, metrics definitions, team split)
2. **Set up MCP connections** for BigQuery and Meta APIs
3. **Create detailed implementation plan**
4. **Begin implementation** with agreed approach

---

## Branch Strategy (Proposed)

```
main
  └── develop
        ├── feature/analyze-agent
        ├── feature/recommend-agent
        ├── feature/execute-agent
        ├── feature/ui-dashboard
        └── feature/meta-oauth
```

- **main:** Production-ready code only
- **develop:** Integration branch
- **feature/*:** Individual features (enables parallel work)

### Foundational Elements Needed
- [ ] Logging setup (structured JSON logs)
- [ ] Testing framework (pytest + fixtures)
- [ ] Observability (OpenTelemetry traces)
- [ ] Error handling patterns
- [ ] Environment configuration (.env + secrets)
- [ ] CI/CD (optional for hackathon)

---

## Session Resume Instructions

To continue this brainstorming session:

1. Open this file for context
2. Resume from "Open Questions" section
3. Key decisions made:
   - 3 agents: Analyze, Recommend, Execute
   - Google ADK + FastAPI backend
   - TypeScript frontend
   - Gemini/OpenAI models
   - BigQuery for data, Meta API for live integration
