# RCA Pipeline Design: Ads Metrics Root Cause Analysis

## Status: Design Phase

---

## Overview

Automated Root Cause Analysis pipeline for detecting and diagnosing falling ad performance metrics.

---

## Workflow Summary

### Step 1: Classify the Problem
Which metric triggered the anomaly?

| Metric | Problem Type | Indicates |
|--------|--------------|-----------|
| Spend ↓ | Delivery Problem | Ads not spending budget |
| Conversions ↓ | Funnel Problem | Traffic not converting |
| CTR ↓ | Creative/Audience | Ads not engaging |
| CPA ↑ | Efficiency Problem | Conversions too expensive |
| ROAS ↓ | Revenue Problem | Revenue per spend dropping |

### Step 2: Isolate Location (Drill Down)
Find the largest contributor by drilling down dimensions:

```
Channel → Campaign Type → Campaign → Ad Set → Ad/Segment
(Meta)    (Prospecting)   (Summer)   (LAL_1%)  (Video_A)
```

### Step 3: Run Diagnostic Checks
Sequential checks to identify root cause:

| # | Check | Condition | Query |
|---|-------|-----------|-------|
| 1 | Budget Exhausted? | Daily/lifetime cap reached | `spend / daily_budget > 0.95` |
| 2 | Bid Cap Too Low? | Losing auctions | `avg_cpm > bid_cap × 0.9` |
| 3 | Audience Exhausted? | High frequency, small pool | `frequency > 3.5 OR reach/audience_size > 0.8` |
| 4 | Creative Fatigue? | CTR declining | `ctr_7d_trend < -15%` |
| 5 | Landing Page Issue? | CTR stable, CVR crashed | `ctr stable AND cvr_change < -30%` |
| 6 | Tracking Broken? | Pixel/CAPI not firing | `clicks > 0 AND conversions = 0 (48h)` |
| 7 | CPM Spiked? | Auction competition up | `cpm_change > 25%` |
| 8 | Recent Changes? | Edits in 24-48h | `change_log WHERE ts > now() - 48h` |
| 9 | Seasonality? | Expected pattern | `metric vs metric_7d_ago, metric_364d_ago` |

### Step 4: Recommended Actions
Each root cause maps to a specific action:

| Root Cause | Recommended Action |
|------------|-------------------|
| Budget Exhausted | Increase budget or redistribute from underperforming campaigns |
| Bid Too Low | Raise bid cap 15-20% or switch to auto-bidding |
| Audience Exhausted | Expand audience, add lookalikes, exclude past converters |
| Creative Fatigue | Refresh creatives, pause worst performers, test new angles |
| Landing Page Issue | Check page load speed, mobile UX, form functionality |
| Tracking Broken | Debug pixel/CAPI, check Events Manager, wait for attribution |
| CPM Spike | Adjust targeting, wait out competition, shift budget |
| Recent Change | Rollback change or monitor for 48h |
| Seasonality | No action - expected behavior, document for future |

---

## Architecture Options

### Option A: Single RCA Agent + Many Tools (Recommended Start)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         RCA AGENT                                    │
│  • Detects anomalies                                                │
│  • Decides which checks to run                                      │
│  • Interprets results                                               │
│  • Recommends actions                                               │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
            ┌─────────────────────────────────────┐
            │              TOOLS                   │
            │  • detect_anomaly                   │
            │  • drill_down_by_dimension          │
            │  • check_budget_exhaustion          │
            │  • check_bid_cap                    │
            │  • check_audience_exhaustion        │
            │  • check_creative_fatigue           │
            │  • check_landing_page               │
            │  • check_tracking                   │
            │  • check_cpm_spike                  │
            │  • get_recent_changes               │
            │  • compare_seasonality              │
            └─────────────────────────────────────┘
```

**Pros:** Simple, one agent decides everything
**Cons:** May be overwhelming for LLM with many tools

### Option B: Multi-Agent Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        RCA ORCHESTRATOR                              │
│  (Coordinates agents, decides when to stop)                         │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │  DETECT   │ │  LOCALIZE │ │ DIAGNOSE  │
            │  AGENT    │ │  AGENT    │ │  AGENT    │
            │           │ │           │ │           │
            │ Finds     │ │ Drills    │ │ Runs      │
            │ anomalies │ │ down to   │ │ diagnostic│
            │ in metrics│ │ find root │ │ checks    │
            └───────────┘ └───────────┘ └───────────┘
                                              │
                                              ▼
                                     ┌───────────────┐
                                     │  RECOMMEND    │
                                     │  AGENT        │
                                     │               │
                                     │ Maps cause    │
                                     │ to action     │
                                     └───────────────┘
```

**Pros:** Specialized agents, cleaner separation
**Cons:** More complex orchestration

### Option C: Hybrid - LLM Orchestrator + Rule-based Checks

```
┌─────────────────────────────────────────────────────────────────────┐
│                     LLM ORCHESTRATOR                                 │
│  • Decides which checks to run                                      │
│  • Interprets ambiguous results                                     │
│  • Generates human-readable explanations                            │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
            ┌─────────────────────────────────────┐
            │       RULE-BASED CHECK ENGINE        │
            │  (Deterministic, fast, no LLM)      │
            │                                      │
            │  if spend/budget > 0.95:            │
            │      return "BUDGET_EXHAUSTED"      │
            │  if frequency > 3.5:                │
            │      return "AUDIENCE_EXHAUSTED"    │
            │  ...                                │
            └─────────────────────────────────────┘
```

**Pros:** Fast checks, LLM only for orchestration/interpretation
**Cons:** Less flexible for edge cases

---

## Data Requirements

| Data Point | Needed For | BigQuery Column | Status |
|------------|------------|-----------------|--------|
| Daily spend | Budget check | `spend` | ✅ Have |
| Daily budget | Budget check | `daily_budget` | ❓ Need |
| CPM | Bid/CPM checks | `cpm` | ❓ Need |
| Bid cap | Bid check | `bid_cap` | ❓ Need |
| Frequency | Audience check | `frequency` | ❓ Need |
| Reach | Audience check | `reach` | ❓ Need |
| Audience size | Audience check | `audience_size` | ❓ Need |
| CTR | Creative fatigue | `ctr` or compute | ❓ Need |
| Impressions | CTR calculation | `total_ad_impression` | ✅ Have |
| Clicks | CTR/tracking | `clicks` | ❓ Need |
| Conversions | CVR/tracking | `conversions` | ❓ Need |
| CVR | Landing page | `cvr` or compute | ❓ Need |
| Change logs | Recent changes | External API | ❓ Need |
| Historical data | Seasonality | Same table, date filter | ✅ Have |

---

## Example Output

```
🚨 ANOMALY DETECTED

Metric: CPA +47% ($32 → $47)
Location: Meta → Prospecting → Summer_Sale → Lookalike_US_1%
Root Cause: Creative Fatigue (CTR dropped 23% over 5 days)
Impact: $2,400 excess spend in last 72h

💡 RECOMMENDED ACTION:
Pause ad creatives running >7 days, introduce 2-3 new variants
```

---

## Implementation Plan

### Phase 1: Foundation
- [ ] Audit BigQuery schema for available columns
- [ ] Implement `detect_anomaly` tool (find metric drops)
- [ ] Implement `drill_down_by_dimension` tool
- [ ] Create RCA agent with basic tools

### Phase 2: Diagnostic Checks
- [ ] Implement checks that work with available data:
  - [ ] `check_creative_fatigue` (if CTR available)
  - [ ] `check_tracking` (clicks vs conversions)
  - [ ] `compare_seasonality` (historical comparison)
- [ ] Add checks that need additional data sources:
  - [ ] `check_budget_exhaustion` (needs budget data)
  - [ ] `check_audience_exhaustion` (needs frequency/reach)

### Phase 3: Integration
- [ ] Connect to ad platform APIs for change logs
- [ ] Add alerting/notification system
- [ ] Build dashboard for RCA results

---

## Files to Create

| File | Purpose |
|------|---------|
| `models/rca_agent.py` | Main RCA agent |
| `helpers/rca_tools.py` | Diagnostic check tools |
| `helpers/anomaly_detection.py` | Anomaly detection logic |
| `controllers/rca_controller.py` | RCA pipeline orchestration |
| `run_rca.py` | CLI for running RCA |

---

## Questions to Resolve

1. **What data is available in BigQuery?** Need to audit schema for CTR, CVR, frequency, etc.
2. **Do we have access to ad platform APIs?** For change logs, budget caps, bid settings
3. **What's the alerting mechanism?** Slack, email, dashboard?
4. **How often should RCA run?** Real-time, hourly, daily?
5. **What's the threshold for "anomaly"?** -15%, -20%, statistical significance?

---

## Reference: Original HTML Mockup

The visual workflow design is saved at:
`/Users/hemanthjills/project/halo/backend/docs/rca_workflow_mockup.html`
