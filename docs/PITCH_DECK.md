# Agatha - Ad Spend Optimization Agent
## Pitch Deck | AIBoomi Hackathon 2025

---

## Slide 1: Problem & Who's Affected

### The $198B Problem

**Ecommerce brands waste 20-30% of their ad spend** due to:

- **Delayed insights:** Manual analysis takes 48+ hours; by then, the damage is done
- **Information overload:** Thousands of ads, dozens of metrics, no clear action
- **Invisible waste:** Zero-conversion campaigns run for weeks unnoticed
- **Creative fatigue:** High-performing ads decay without timely alerts

### Who's Affected

| Segment | Pain Point |
|---------|------------|
| **SMB Brands** ($10K-$100K/month spend) | No dedicated analyst; rely on platform defaults |
| **Marketing Managers** | Drowning in dashboards; need actionable recommendations |
| **CFOs/Founders** | Can't tie ad spend to revenue outcomes |

**Market Size:** Digital advertising = $600B+ globally. 30% waste = $180B+ optimization opportunity.

---

## Slide 2: Our Insight (Why Now / Why You)

### Why Now

1. **LLMs can reason over data:** Gemini 2.5 Pro can interpret ad performance patterns and generate human-quality recommendations
2. **API maturity:** Meta Marketing API provides programmatic access to pause, scale, and adjust campaigns
3. **Cost of inaction is rising:** CPMs up 30% YoY; every dollar of waste hurts more

### Why Us (Consequential.io)

- **Domain expertise:** Team has built analytics platforms for $100M+ ad spend clients
- **Production-grade data:** Access to real BigQuery datasets with 298 days of ecommerce ad data
- **Full-stack AI capability:** From data pipeline to deployed agents in <72 hours

### Our Unfair Advantage

> We're not building another dashboard. We're building an **AI employee** that watches your ads 24/7 and takes action.

---

## Slide 3: Solution Demo

### Product: Agatha

**Live Demo:** [https://adspend.consequential.io](https://adspend.consequential.io)

### User Flow

```
[Login] --> [Analyze] --> [Recommend] --> [Execute]
   |            |              |              |
   v            v              v              v
 OAuth    AI detects       AI suggests    Human approves
          anomalies     budget changes   AI executes
```

### Key Screens

1. **Login:** Facebook OAuth or Demo Mode
2. **Analyze:** Date range selector, real-time anomaly detection
3. **Recommend:** Actionable cards with estimated $ impact
4. **Execute:** One-click approval with dry-run safety

### Demo Results (Real Data)

- **184 ads analyzed** in seconds
- **3 anomalies detected** (would have taken analyst 4+ hours)
- **$12K+ potential savings** identified

---

## Slide 4: Tech Approach

### Architecture

```
+------------------+     +-------------------+     +------------------+
|    Frontend      |     |   Backend API     |     |   Data Layer     |
|  (React/Vite)    |<--->|   (FastAPI)       |<--->|   (BigQuery)     |
|                  |     |                   |     |   (Meta API)     |
+------------------+     +-------------------+     +------------------+
                               |
                    +----------+----------+
                    |          |          |
               +----v---+ +----v----+ +---v-----+
               |Analyze | |Recommend| |Execute  |
               | Agent  | | Agent   | | Agent   |
               +--------+ +---------+ +---------+
                    \          |          /
                     \         |         /
                      +--------v--------+
                      | Google Gemini   |
                      | 2.5 Pro (ADK)   |
                      +-----------------+
```

### Models & Tools

| Component | Technology | Purpose |
|-----------|------------|---------|
| **LLM** | Gemini 2.0 Flash | Agent reasoning, recommendation generation |
| **Framework** | Google ADK | Multi-agent orchestration with FunctionTool |
| **Anomaly Detection** | Z-score statistical | Detect metric deviations (threshold: 2.5σ) |
| **RCA Agent** | LLM + 6 diagnostic tools | Root cause analysis for falling metrics |
| **Data Store** | BigQuery | Historical ad performance (77 days) |
| **Actions** | Meta Marketing API | Campaign modifications (dry-run) |

### Agentic Tool Use (Implemented)

Each agent has access to **data-fetching tools** and makes autonomous decisions:

| Agent | Tools | Output |
|-------|-------|--------|
| **AnalyzeAgent** | `get_ad_data` | Classifies ads as GOOD/OK/WARNING/BAD/WAIT |
| **RecommendAgent** | `get_top_performers`, `get_underperformers` | SCALE/REDUCE/PAUSE actions with $ impact |
| **RCA Agent** | 6 diagnostic checks | Root cause + confidence + recommended action |

**RCA Diagnostic Tools:**
- `check_cpm_spike` — Auction competition analysis
- `check_creative_fatigue` — CTR trend over time
- `check_landing_page` — Funnel conversion metrics
- `check_tracking` — Pixel/conversion verification
- `check_budget_exhaustion` — Spend vs budget caps
- `check_seasonality` — Historical comparisons (7d/30d)

**Agent Decision Flow:**
```
Input: "CPA spiked 261%"
  Agent decides which tool to call based on anomaly type
  Tool returns: {spiked: true, cpm_change: 46.8%}
  Agent interprets: "Root cause: CPM spike (auction competition)"
  Output: Confidence HIGH, Action: Adjust bids
```

### Quick Analysis Mode (Implemented)

Fast top/bottom performer identification without LLM:

| Feature | Implementation |
|---------|----------------|
| Data source | BigQuery with weighted ROAS aggregation |
| Filtering | CAMPAIGN_STATUS = ACTIVE, min spend threshold |
| Output | Top performers (scale), Underperformers (pause) |
| Speed | Seconds (no LLM latency) |

### Hallucination Prevention (Implemented)

**Chain-of-Thought Grounding:** LLM must show structured reasoning that we validate:

```json
{
  "data_extracted": {"spend": 212297, "roas": 29.58},  // ← Verified against source
  "comparison": {"roas_ratio": "4.3×"},                // ← Math checked
  "classification": "GOOD"                              // ← Must match logic
}
```

If validation fails → retry with feedback OR fallback to rule-based classification.

### Why This Approach

- **Gemini 2.0 Flash:** Fast inference with native tool calling support
- **Google ADK:** Production-ready agent framework with FunctionTool
- **Agentic tools:** LLM decides what to check based on anomaly type
- **Grounded reasoning:** Validate LLM output against source data to prevent hallucinations
- **Hybrid rules + LLM:** Rules for precision, LLM for nuance and explanation

---

## Slide 5: Value & GTM

### Value Proposition

| Metric | Current State | With Agatha |
|--------|---------------|-------------|
| Time to insight | 48+ hours | <5 minutes |
| Waste detection | 10-20% caught | 80%+ caught |
| Optimization frequency | Weekly/monthly | Daily/continuous |
| Cost | $5K+/month analyst | $500/month SaaS |

### Business Model

**SaaS Subscription:**
- **Starter:** $299/month (up to $50K ad spend)
- **Growth:** $599/month (up to $200K ad spend)
- **Enterprise:** Custom pricing + integrations

**Revenue Share Option:** 10% of documented savings (performance-based)

### Go-to-Market

1. **Phase 1 (Now):** Direct sales to Consequential.io existing clients
2. **Phase 2 (Q2):** Partnership with Meta Business Partners
3. **Phase 3 (Q3):** Self-serve product with Shopify/WooCommerce integration

### Target Customers

- D2C ecommerce brands ($1M-$50M revenue)
- Performance marketing agencies
- In-house marketing teams at mid-market companies

---

## Slide 6: Next Steps & Risks

### Roadmap

| Timeline | Milestone |
|----------|-----------|
| **Feb 2025** | Hackathon launch, seed customers |
| **Mar 2025** | Google Ads integration, production write APIs |
| **Q2 2025** | Multi-platform support (TikTok, Amazon) |
| **Q3 2025** | Predictive recommendations (before anomaly occurs) |
| **Q4 2025** | Autonomous mode (auto-execute with guardrails) |

### Key Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **API access revoked** | Low | Multiple platform integrations |
| **LLM hallucination** | Medium | Rule-based thresholds + human approval |
| **Customer trust** | Medium | Transparent recommendations with data sources |
| **Competition** | High | Speed to market, domain expertise, integration depth |

### The Ask

**For AIBoomi:** Feedback on product direction, potential pilot customers

**For Investors:** $500K seed to build sales team and expand platform coverage

### Contact

- **Website:** [consequential.io](https://consequential.io)
- **Demo:** [adspend.consequential.io](https://adspend.consequential.io)
- **GitHub:** [github.com/consequential-io/halo](https://github.com/consequential-io/halo)

---

*Built at AIBoomi Hackathon, Pune | February 2025*
