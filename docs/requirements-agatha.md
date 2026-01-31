# Agatha - Ad Spend Optimization Agent

## Requirements Document v1.3

| Field | Value |
|-------|-------|
| **Created** | 2025-01-31 |
| **Demo Deadline** | 2025-02-01 09:00 IST |
| **Hackathon** | AIBoomi, Pune |
| **Category** | Commerce / Shopping / Consumer |

---

## The Team

| Role | Person | GitHub |
|------|--------|--------|
| Product Manager | Jaidev | jaidevk |
| Engineering Lead | Hemanth | hemanthj |
| Designer | - | - |

---

## Quick Links

| Link | URL |
|------|-----|
| Repository | [consequential-io/halo](https://github.com/consequential-io/halo) |
| Brainstorm Session | [docs/brainstorm-session-2025-01-31.md](./brainstorm-session-2025-01-31.md) |
| Reference Codebase | `/Users/jaidevk/Work/dev/otb-agents` |

---

## The Problem

**Problem Statement:**
Ecommerce brands struggle to optimize ad spend across platforms because they lack visibility into which campaigns are generating positive ROI and which are wasting budget, and even when they identify issues, acting on them is slow and error-prone.

**Hypothesis:**
Marketing teams make suboptimal ad spend decisions because:
1. Data is fragmented across platforms (Google Ads, Meta Ads)
2. Manual analysis is time-consuming and error-prone
3. By the time insights are gathered, the opportunity window has passed
4. Knowing what to change is hard; actually executing changes is even harder
5. Creative fatigue goes undetected until performance tanks

**What we are NOT solving:**
- Cross-channel attribution modeling
- Long-term brand marketing effectiveness
- Organic marketing channels
- Audience discovery/targeting strategy

**What we ARE solving (expanded scope):**
- Budget optimization (increase/decrease/pause spend)
- **Creative recommendations** (suggest refreshing underperforming creatives)

---

## Why

**How do we know this is a real problem worth solving?**

### Industry Benchmarks (Source: Growth Ceiling Report)

| Metric | Value | Impact |
|--------|-------|--------|
| Hidden tax on eCommerce | **$198B** | Industry-wide inefficiency |
| Digital ads never seen by humans | **56%** | Over half of spend is invisible |
| Spend bloated by poor attribution | **+15%** | Misallocation compounds |
| ROI reduction from signal loss | **40%** | iOS/privacy changes broke tracking |
| Average time to detect critical errors | **48 hours** | Slow detection = bleeding money |
| Lost revenue per hour (single broken pixel) | **$8,000+** | Technical issues are expensive |

### Business Impact

- Brands invest **20-30% of revenue** into advertising, yet operate in a fog
- Signal loss from privacy changes (iOS updates) destroyed traditional tracking
- Ad platforms claim credit for the same sale, creating attribution chaos
- Teams waste **weeks** in analysis paralysis debating: "Is it the creative? The landing page? A broken pixel?"

### Customer Impact

- Marketing managers spend hours in dashboards instead of strategy
- Missed opportunities to scale winning campaigns
- Budget burned on underperforming ads before they're caught
- Creative fatigue goes undetected until performance tanks
- Manual human guesswork is slow, costly, and often wrong

---

## Success Metrics

**How do we know if we've solved this problem?**

### Demo Success Metrics (Hackathon)

**Approach:** "Money Found" + Full Loop Demo
- Lead with dramatic $ number, then show the workflow that found it
- Hybrid execution: Real read (pull data), mock write (simulate execution)

#### Must-Have (Demo Fails Without These)

| # | Metric | Target | How to Verify |
|---|--------|--------|---------------|
| D1 | Identify scaling opportunity | ≥ 1 "good spend" recommendation | Shows $ amount + reasoning |
| D2 | Identify waste | ≥ 1 "bad spend" recommendation | Shows $ amount + reasoning |
| D3 | Full agent loop | Analyze → Recommend → Execute | All 3 agents fire in sequence |
| D4 | Human approval UI | Working approve/reject | Buttons trigger execution |
| D5 | Mock execution confirmation | Shows "Campaign paused" or "Budget increased" | Confirmation message displayed |

#### Should-Have (Strengthens Demo)

| # | Metric | Target | How to Verify |
|---|--------|--------|---------------|
| D6 | Real data pull | Live BigQuery or Meta read | Shows fresh data, not hardcoded |
| D7 | Time-to-insight | < 60 seconds from login | Stopwatch during demo |
| D8 | Creative recommendation | ≥ 1 "refresh creative" suggestion | Shows fatigued ad flagged |

#### Nice-to-Have (Wow Factor)

| # | Metric | Target | How to Verify |
|---|--------|--------|---------------|
| D9 | Multi-account view | Show 2 brands (TL + WH) | Dropdown to switch |
| D10 | Total $ impact summary | "Agatha found $X in opportunities" | Single headline number |

### Product Success Metrics (Post-Hackathon)

**Focus:** ROI + Recommendation Accuracy

#### Primary (ROI-Focused)

| # | Metric | Target | How to Measure |
|---|--------|--------|----------------|
| P1 | $ waste prevented | Track monthly | Sum of paused/reduced bad spend |
| P2 | $ scaled into winners | Track monthly | Sum of increased good spend |
| P3 | ROAS lift | +15% in 30 days | Before/after avg ROAS comparison |
| P4 | Payback period | < 1 month | (Subscription cost) / ($ optimized) |

#### Supporting (Trust & Adoption)

| # | Metric | Target | How to Measure |
|---|--------|--------|----------------|
| P5 | Recommendation accuracy | 80%+ approval | Approved / Total recommendations |
| P6 | False positive rate | < 10% | User overrides "bad spend" call |

### Example Pitch Numbers (Based on Validated Data)

| Brand | $ Waste Found | $ Scale Opportunity | Potential Impact |
|-------|---------------|---------------------|------------------|
| TL | $88k (TikTok @ 0 ROAS) | $212k → scale 30% = +$64k | $152k optimized |
| WH | ₹55k (Floor Lamps @ 0 ROAS) | ₹426k → scale 30% = +₹128k | ₹183k optimized |

**Pitch headline:** *"Agatha identified $150k+ in optimization opportunities in under 60 seconds"*

---

## Target Audience

**Who are we building for?**

### Primary Persona: Ecommerce Marketing Manager

| Attribute | Description |
|-----------|-------------|
| Role | Marketing Manager / Performance Marketer |
| Company Size | SMB to Mid-market ecommerce brands (8-figure revenue) |
| Ad Spend | $10K - $500K/month across platforms |
| Pain Point | Manually monitoring and optimizing campaigns |
| Current Tools | Google Ads, Meta Ads Manager, spreadsheets |
| Frustration | "Scaling is a gamble, not a science" |

### User Journey

```
1. User logs in via Meta OAuth
2. System pulls ad data from connected accounts
3. AI analyzes performance and identifies opportunities
4. User reviews recommendations (the "Aha moment"):
   - Budget changes (increase/decrease/pause)
   - Creative refresh suggestions
5. User approves/rejects each recommendation
6. System executes approved changes via API
7. User sees confirmation of executed changes
```

---

## What

**Roughly, what does this look like in the product?**

### Multi-Agent Architecture

```
                    ┌─────────────┐
                    │  Meta OAuth │
                    │   (Login)   │
                    └──────┬──────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                      AGATHA                              │
│                   (Orchestrator)                         │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────┐   ┌───────────┐   ┌───────────┐
│  ANALYZE  │   │ RECOMMEND │   │  EXECUTE  │
│   Agent   │──▶│   Agent   │──▶│   Agent   │
└───────────┘   └───────────┘   └───────────┘
     │                               │
     ▼                               ▼
┌───────────────────┐         ┌───────────┐
│ Meta API (Read)   │         │ Meta API  │
│ PRIMARY - 30 days │         │ (Mock Write) │
├───────────────────┤         └───────────┘
│ BigQuery          │
│ FALLBACK - test   │
└───────────────────┘
```

### Agent Specifications

#### Analyze Agent
| Attribute | Value |
|-----------|-------|
| **Input** | Ad performance data (see Data Sources below) |
| **Output** | Structured analysis with spend classification |
| **Actions** | Read-only |
| **Key Metrics** | ROAS, CPA, CTR, Conversion Rate, Frequency, Creative Performance |

**Data Sources (Priority Order):**

| Priority | Source | Use Case | Data Range |
|----------|--------|----------|------------|
| **Primary** | Meta Ads API | Live demo - login via OAuth, pull real data | 1 month historical |
| **Fallback** | BigQuery | Testing & demo backup if Meta fails | Pre-loaded test data |

**Demo Flow:**
1. User authenticates via Meta OAuth
2. Analyze Agent calls Meta Marketing API
3. Pulls last 30 days of ad performance data
4. If Meta API fails → fallback to BigQuery test data

#### Recommend Agent
| Attribute | Value |
|-----------|-------|
| **Input** | Analysis output from Analyze Agent |
| **Output** | Actionable recommendations |
| **Actions** | Read-only |
| **Recommendation Types** | Budget (increase/decrease/pause), Creative (refresh/retire) |

#### Execute Agent
| Attribute | Value |
|-----------|-------|
| **Input** | User-approved recommendations |
| **Output** | Execution status and confirmation |
| **Actions** | Write to Meta/Google Ads APIs |
| **Capabilities** | Pause ads, adjust budgets, (creative changes require manual action) |

### Recommendation Types

| Type | Action | Automated? |
|------|--------|------------|
| **Scale Winner** | Increase budget on high-ROAS campaigns | Yes |
| **Cut Loser** | Pause/reduce budget on wasteful spend | Yes |
| **Refresh Creative** | Flag creative fatigue + actionable suggestions | Manual (suggestion only) |
| **Fix Frequency** | Reduce budget when frequency too high | Yes |

### Creative Recommendation Levels

| Level | Description | Scope |
|-------|-------------|-------|
| 1. Flag only | "This creative is underperforming" | - |
| 2. Flag + reason | "High frequency (5x avg) causing fatigue" | - |
| **3. Flag + actionable suggestion** | "Refresh headline, try shorter video, test new CTA" | **Hackathon** |
| 4. AI-generated creative | Generate new ad copy/image suggestions | Product roadmap |

#### Creative Fatigue Detection Signals

| Signal | Threshold | Action Suggested |
|--------|-----------|------------------|
| High frequency | > 3x account avg | "Audience seeing ad too often - refresh or expand targeting" |
| CTR decline | > 30% drop over 7 days | "Click-through dropping - test new headline/image" |
| Rising CPC | > 50% increase over 7 days | "Cost per click rising - creative losing relevance" |
| Stale runtime | > 30 days same creative | "Creative running 30+ days - test fresh variation" |

#### Example Creative Recommendations (Demo)

```
CREATIVE REFRESH NEEDED

Ad: "Summer Sale - 50% Off"
Campaign: TL_US_Prospecting
Status: Running 45 days, CTR down 35%

Issue: Creative fatigue detected
- Frequency: 4.2 (3x account average)
- CTR: 1.2% → 0.78% (down 35% in 14 days)
- CPC: $0.45 → $0.72 (up 60%)

Suggestions:
1. Test new headline emphasizing urgency or new benefit
2. Swap hero image - current image seen 4.2x per user
3. Try video format (your video ads avg 2x higher CTR)
4. Refresh CTA: "Shop Now" → "Get My Discount"
```

### UI Screens (Minimal for Demo)

1. **Login Screen** - Meta OAuth button
2. **Dashboard** - Overview of connected accounts
3. **Analysis View** - Display of insights from Analyze Agent
4. **Recommendations View** - List of recommendations with approve/reject buttons
5. **Execution Status** - Confirmation of changes made

---

## How

**What is the experiment/implementation plan?**

### Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python + FastAPI + Google ADK |
| Frontend | TypeScript + Next.js |
| AI Models | Gemini or OpenAI |
| Data | BigQuery (test data) + Meta API (live) |
| Auth | Meta OAuth |
| Observability | OpenTelemetry |

### Implementation Phases

**Phase 1: MVP (Hackathon Demo)**
- Analyze Agent + Recommend Agent
- Human-in-the-loop approval
- Execute Agent for Meta only
- BigQuery for data (pre-loaded test data)
- Recommendations: Budget + Creative suggestions

**Phase 2: Stretch Goals (If Time Permits)**
- Fully autonomous mode (no human approval)
- Google Ads integration
- Real-time data via API

---

## Milestones

| Milestone | Target Time | Risks | Mitigations |
|-----------|-------------|-------|-------------|
| Requirements finalized | Jan 31, 14:00 IST | Open questions unresolved | Make assumptions, document them |
| Backend scaffolding | Jan 31, 16:00 IST | Unfamiliarity with ADK | Reference otb-agents patterns |
| Analyze Agent working | Jan 31, 20:00 IST | Data schema unclear | Use sample data, mock if needed |
| Recommend Agent working | Jan 31, 23:00 IST | Logic definition unclear | Start with simple rules |
| Execute Agent working | Feb 1, 02:00 IST | Meta API complexity | Limit to budget changes only |
| Frontend basic UI | Feb 1, 05:00 IST | Time pressure | Use minimal UI, component library |
| Integration & Testing | Feb 1, 07:00 IST | Integration bugs | Buffer time for fixes |
| Demo ready | Feb 1, 08:30 IST | Last-minute issues | Have fallback demo script |
| **DEMO** | Feb 1, 09:00 IST | - | - |

---

## Open Questions Summary

### Critical (Block implementation)

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 1 | What fields are available in BigQuery test data? | Jaidev | RESOLVED - see brainstorm doc |
| 2 | What defines "good" spend? (ROAS > X? CPA < Y?) | Jaidev | RESOLVED - ROAS ≥ 2× avg, spend ≥ $1k, ≥ 7 days |
| 3 | What defines "bad" spend? (Zero conversions? ROAS < 1?) | Jaidev | RESOLVED - ROAS = 0 after $5k+/7d, or < 0.5× avg |
| 4 | What Execute actions are possible via Meta API? | Hemanth | OPEN |

### Important (Affect scope)

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 5 | Direct Meta API vs Supermetrics? | Hemanth | OPEN |
| 6 | What OAuth scopes are needed for Meta? | Hemanth | OPEN |
| 7 | Team work division (backend/frontend)? | Jaidev/Hemanth | OPEN |

### Nice to Know (Demo polish)

| # | Question | Owner | Status |
|---|----------|-------|--------|
| 8 | Demo scenario/script? | Jaidev | OPEN |
| 9 | Sample account for live demo? | Jaidev | OPEN |
| 10 | Fallback if live API fails? | Jaidev | OPEN |

---

## References

- [Brainstorm Session](./brainstorm-session-2025-01-31.md)
- [Growth Ceiling: The $198B Hidden Tax](~/Downloads/Growth_Ceiling_The_$198B_Hidden_Tax.pdf)
- Reference Architecture: `/Users/jaidevk/Work/dev/otb-agents`
- Meta Marketing API: https://developers.facebook.com/docs/marketing-apis/
- Google Ads API: https://developers.google.com/google-ads/api/docs/start
