# Agatha: AI-Powered Ad Performance Platform

Agatha is an AI-first ad performance analysis platform that uses LLM agents to analyze, recommend, and diagnose ad performance issues.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Available Pipelines](#available-pipelines)
3. [Architecture Overview](#architecture-overview)
4. [Pipeline Details](#pipeline-details)
5. [Agent + Tools Design](#agent--tools-design)
6. [Configuration](#configuration)
7. [Data Sources](#data-sources)

---

## Quick Start

```bash
# Setup
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set environment variables
export GOOGLE_API_KEY="your-gemini-api-key"
export GOOGLE_CLOUD_PROJECT="your-gcp-project"

# Run quick analysis (no LLM, fast)
python run_pipeline.py --quick --bigquery --tenant wh --days 30

# Run full analysis (with LLM)
python run_pipeline.py --bigquery --tenant wh --days 30

# Run RCA pipeline (anomaly detection + diagnosis)
python run_rca.py --tenant wh --baseline-days 30 --threshold 2.5
```

---

## Available Pipelines

| Pipeline | Command | Purpose | Uses LLM? |
|----------|---------|---------|-----------|
| **Quick Analysis** | `run_pipeline.py --quick` | Top/bottom performers | No |
| **Full Analysis** | `run_pipeline.py` | Classify + recommend + execute | Yes |
| **RCA Detection** | `run_rca.py --detect-only` | Find anomalies | No |
| **Full RCA** | `run_rca.py` | Detect + diagnose root cause | Yes |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AGATHA PLATFORM                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │  run_pipeline.py │    │   run_rca.py    │    │    API Server   │     │
│  │  (CLI)           │    │   (CLI)         │    │    (FastAPI)    │     │
│  └────────┬─────────┘    └────────┬────────┘    └────────┬────────┘     │
│           │                       │                      │              │
│           ▼                       ▼                      ▼              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        CONTROLLERS                               │   │
│  │  agatha_controller.py          rca_controller (in run_rca.py)   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           │                       │                                     │
│           ▼                       ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                          AGENTS (LLM)                            │   │
│  │                                                                  │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌───────────────────────┐ │   │
│  │  │AnalyzeAgent  │  │RecommendAgent │  │      RCAAgent         │ │   │
│  │  │              │  │               │  │                       │ │   │
│  │  │Classifies ads│  │Suggests       │  │Investigates anomalies │ │   │
│  │  │GOOD/BAD/WAIT │  │SCALE/PAUSE    │  │using diagnostic tools │ │   │
│  │  └──────────────┘  └───────────────┘  └───────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           │                       │                                     │
│           ▼                       ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                          TOOLS & HELPERS                         │   │
│  │                                                                  │   │
│  │  helpers/tools.py        helpers/rca_checks.py                  │   │
│  │  - get_ad_data           - check_budget_exhaustion              │   │
│  │  - get_top_performers    - check_creative_fatigue               │   │
│  │  - get_underperformers   - check_cpm_spike                      │   │
│  │                          - check_landing_page                    │   │
│  │                          - check_tracking                        │   │
│  │                          - check_seasonality                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│           │                       │                                     │
│           ▼                       ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        DATA LAYER                                │   │
│  │                                                                  │   │
│  │  BigQuery (Production)              Fixtures (Testing)          │   │
│  │  - WhisperingHomes (wh)             - thirdlove_ads.json        │   │
│  │  - ThirdLove (tl)                                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Details

### 1. Quick Analysis Pipeline

**Purpose:** Fast top/bottom performer identification without LLM calls.

```bash
# Using fixture data
python run_pipeline.py --quick

# Using BigQuery
python run_pipeline.py --quick --bigquery --tenant wh --days 30

# Options
--limit 10        # Number of ads to show (default: 5)
--min-spend 1000  # Minimum spend threshold (default: 1000)
--output out.json # Save results to file
```

**Output:**
```
📈 TOP PERFORMERS (Scale Candidates)
1. ✅ Whispering Homes Brand Campaign
   ROAS: 8.12 (4.2× avg) | Spend: $426,496 | Days: 77

📉 UNDERPERFORMERS (Pause/Reduce Candidates)
1. ✅ Summer Sale Carousel
   ROAS: 0.00 (🔴 ZERO ROAS) | Spend: $33,000 | Days: 45
```

**Flow:**
```
run_pipeline.py --quick
       │
       ▼
get_top_performers()  ──────►  BigQuery / Fixture
get_underperformers()          │
       │                       │
       ◄───────────────────────┘
       │
       ▼
print_quick_results()
```

---

### 2. Full Analysis Pipeline

**Purpose:** LLM-powered classification and recommendations for each ad.

```bash
# Using fixture data
python run_pipeline.py

# Using BigQuery
python run_pipeline.py --bigquery --tenant wh --days 30 --limit 10

# Options
--output results.json  # Save full results
```

**Output:**
```
ANALYSIS RESULTS
================
✓ Thirdlove® Bras
   Classification: GOOD | Confidence: HIGH
   Action: SCALE
   ROAS: 29.58 (4.3× avg)

✗ Summer Sale Video
   Classification: BAD | Confidence: HIGH
   Action: PAUSE
   ROAS: 0.00 (zero conversions)
```

**Flow:**
```
run_pipeline.py
       │
       ▼
┌──────────────────┐
│ AgathaController │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────┐
│  AnalyzeAgent    │────►│  Gemini LLM     │
│                  │◄────│  (Classification)│
└────────┬─────────┘     └─────────────────┘
         │
         ▼
┌──────────────────┐     ┌─────────────────┐
│  RecommendAgent  │────►│  Gemini LLM     │
│                  │◄────│  (Actions)      │
└────────┬─────────┘     └─────────────────┘
         │
         ▼
┌──────────────────┐
│  ExecuteAgent    │  (Mock mode - no real API calls)
└────────┬─────────┘
         │
         ▼
    Final Report
```

**Classification Logic (AnalyzeAgent):**

| Classification | Criteria |
|----------------|----------|
| GOOD | ROAS > 1.5× account avg, spend > $1000, days > 7 |
| OK | ROAS between 0.8× and 1.5× avg |
| WARNING | ROAS between 0.5× and 0.8× avg |
| BAD | ROAS < 0.5× avg OR zero ROAS |
| WAIT | Days active < 7 (not enough data) |

---

### 3. RCA Pipeline (Root Cause Analysis)

**Purpose:** Detect anomalies in ad metrics and diagnose root causes using AI agent with diagnostic tools.

```bash
# Detection only (no LLM)
python run_rca.py --detect-only --tenant wh --baseline-days 30

# Full RCA (detect + investigate with LLM)
python run_rca.py --tenant wh --baseline-days 30 --threshold 2.5

# Investigate specific ad
python run_rca.py --ad "Summer Sale Video" --metric roas

# Options
--threshold 2.5      # Z-score threshold (default: 2.0)
--max-anomalies 5    # Max anomalies to investigate (default: 5)
--current-days 3     # Recent period to compare (default: 3)
--output rca.json    # Save results
```

**Output:**
```
📈 ACCOUNT METRICS TIMELINE (Last 30 Days)
======================================================================
🟢 CPM: $130 → $140 (+7% WoW)
🟢 ROAS: 1.16 → 2.37 (+104% WoW)

CPM Trend (last 21 days):
$  164 |            █     ▄
$  146 |       ▄    █ █   █
$  129 |       ██ ▄ █▄█▄█████
       +---------------------
        01-11           01-31

⚠️  CPM spike detected starting ~2026-01-18

📊 ROOT CAUSES (Grouped)
======================================================================
💰 CPM Spike (Increased Auction Competition)
   Affected Ads: 5
   💡 Action: Adjust bids or targeting to reduce costs
   --------------------------------------------------
   • Summer Sale Video
     CPA SPIKE 261% | Confidence: ✅ HIGH
```

**Flow:**
```
run_rca.py
       │
       ▼
┌──────────────────────┐
│ get_metric_timeline()│ ──► Shows CPM/ROAS trend chart
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   AnomalyDetector    │ ──► Z-score based detection
│                      │     Filters to BAD anomalies only
└──────────┬───────────┘     (ROAS drop, CPA spike, etc.)
           │
           ▼
     For each anomaly:
           │
           ▼
┌──────────────────────┐     ┌─────────────────────────────┐
│      RCAAgent        │────►│        Gemini LLM           │
│                      │     │                             │
│ Decides which tools  │◄────│  "I should check CPM first" │
│ to call based on     │     │                             │
│ anomaly type         │     └─────────────────────────────┘
└──────────┬───────────┘
           │
           ▼ calls tools
┌──────────────────────────────────────────────────────────┐
│                    DIAGNOSTIC TOOLS                       │
│                                                          │
│  check_cpm_spike()      → Queries BigQuery for CPM trend │
│  check_creative_fatigue() → Queries CTR over time        │
│  check_landing_page()   → Queries funnel metrics         │
│  check_tracking()       → Checks clicks vs conversions   │
│  check_budget_exhaustion() → Checks spend vs budget      │
│  check_seasonality()    → Compares to 7d/30d ago         │
└──────────────────────────────────────────────────────────┘
           │
           ▼ returns evidence
┌──────────────────────┐
│      RCAAgent        │ ──► Interprets results
│                      │     Determines root cause
│                      │     Assigns confidence
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Group by root cause │ ──► "5 ads affected by CPM Spike"
│  Show recommendations│
└──────────────────────┘
```

---

## Agent + Tools Design

### What Makes It "Agentic"

| Traditional Approach | Agentic Approach |
|---------------------|------------------|
| Code decides what to check | LLM decides what to check |
| Fixed if/else sequence | Dynamic based on evidence |
| Returns first match | Weighs multiple hypotheses |
| No reasoning visible | Chain-of-thought reasoning |

### How Agent Decides Which Tools to Call

The agent receives a decision table in its prompt:

```
| Anomaly      | Check First            | Then Check              |
|--------------|------------------------|-------------------------|
| ROAS dropped | check_cpm_spike        | check_creative_fatigue  |
| Spend dropped| check_budget_exhaustion| check_cpm_spike         |
| CTR dropped  | check_creative_fatigue | check_seasonality       |
| CPA spiked   | check_landing_page     | check_cpm_spike         |
| CPM spiked   | check_cpm_spike        | check_seasonality       |
```

### Tool Registration (Google ADK)

```python
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Wrap Python functions as tools
tools = [
    FunctionTool(func=check_cpm_spike),
    FunctionTool(func=check_creative_fatigue),
    # ...
]

# Create agent with tools
agent = LlmAgent(
    name="rca_agent",
    model="gemini-2.0-flash",
    instruction=RCA_AGENT_PROMPT,
    tools=tools,
)
```

### Example Tool Implementation

```python
async def check_cpm_spike(
    ad_name: str,
    days: int = 7,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """Check if CPM has spiked (auction competition increased)."""

    # Query BigQuery for CPM data
    query = """
    WITH recent AS (SELECT AVG(CPM) FROM last_3_days),
         baseline AS (SELECT AVG(CPM) FROM last_7_days)
    SELECT current_cpm, baseline_cpm
    """

    results = run_query(query)

    # Calculate change
    cpm_change = (current - baseline) / baseline * 100

    # Return structured result for LLM
    return {
        "spiked": cpm_change > 25,
        "cpm_change_pct": round(cpm_change, 1),
        "current_cpm": current_cpm,
        "baseline_cpm": baseline_cpm,
        "interpretation": f"CPM {'spiked' if spiked else 'normal'} ({cpm_change:+.1f}%)"
    }
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes | Gemini API key for LLM calls |
| `GOOGLE_CLOUD_PROJECT` | For BigQuery | GCP project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | For BigQuery | Path to service account JSON |

### Settings (config/settings.py)

```python
class Settings:
    google_cloud_project = "your-project"
    gemini_model = "gemini-2.0-flash"

    # BigQuery tables per tenant
    bq_tables = {
        "wh": "project.dataset.whispering_homes_ads",
        "tl": "project.dataset.thirdlove_ads",
    }
```

---

## Data Sources

### BigQuery Schema

The platform expects these columns in BigQuery:

| Column | Type | Description |
|--------|------|-------------|
| `AD_NAME` | STRING | Ad identifier |
| `ad_provider` | STRING | "Facebook Ads", "Google Ads", etc. |
| `spend` | STRING* | Daily spend (cast to FLOAT64) |
| `ROAS` | STRING* | Return on ad spend |
| `CTR` | STRING* | Click-through rate |
| `CPM` | STRING* | Cost per mille |
| `CPA` | STRING* | Cost per acquisition |
| `CAMPAIGN_STATUS` | STRING | "ACTIVE" or "INACTIVE" |
| `datetime_IST` | STRING | Timestamp |
| `data_source` | STRING | Filter: "Ad Providers" |

*Note: Some columns are stored as STRING and require SAFE_CAST.

### Fixture Data

For testing without BigQuery:

```bash
# Uses fixtures/thirdlove_ads.json
python run_pipeline.py --quick  # No --bigquery flag
```

---

## File Structure

```
backend/
├── run_pipeline.py          # Main analysis CLI
├── run_rca.py               # RCA pipeline CLI
├── main.py                  # FastAPI server
│
├── controllers/
│   └── agatha_controller.py # Orchestrates analysis pipeline
│
├── models/
│   ├── analyze_agent.py     # Classification agent
│   ├── recommend_agent.py   # Recommendation agent
│   ├── execute_agent.py     # Execution agent (mock)
│   ├── anomaly_agent.py     # Anomaly detection
│   └── rca_agent.py         # Root cause analysis agent
│
├── helpers/
│   ├── tools.py             # BigQuery queries, data fetching
│   ├── rca_checks.py        # Diagnostic check functions
│   └── validators.py        # Output validation
│
├── config/
│   └── settings.py          # Configuration
│
├── fixtures/
│   └── thirdlove_ads.json   # Test data
│
└── docs/
    └── RCA_PIPELINE_DESIGN.md
```

---

## Extending the Platform

### Adding a New RCA Check

1. Add function to `helpers/rca_checks.py`:

```python
async def check_new_issue(
    ad_name: str,
    days: int = 7,
    tenant: Literal["tl", "wh"] = "wh"
) -> Dict[str, Any]:
    """Check for new issue type."""
    # Query BigQuery
    # Return structured result
    return {
        "issue_detected": True/False,
        "metric_value": ...,
        "interpretation": "Human readable explanation"
    }
```

2. Register in `models/rca_agent.py`:

```python
from helpers.rca_checks import check_new_issue

self.tools = [
    # ... existing tools
    FunctionTool(func=check_new_issue),
]
```

3. Update agent prompt with when to use the new check.

### Adding a New Tenant

1. Add table mapping in `config/settings.py`:

```python
bq_tables = {
    "wh": "...",
    "tl": "...",
    "new_tenant": "project.dataset.new_tenant_ads",
}
```

2. Use with CLI:

```bash
python run_rca.py --tenant new_tenant
```
