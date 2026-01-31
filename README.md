# Agatha - Ad Spend Optimization Agent

## Problem Statement

Ecommerce brands waste 20-30% of ad spend because they lack visibility into which campaigns generate positive ROI. By the time insights are gathered manually, the opportunity window has passed. The industry loses **$198B annually** to inefficient ad spend, with 56% of digital ads never seen by humans and critical errors taking 48+ hours to detect.

## Users & Context

**Primary Users:** Ecommerce Marketing Managers at SMB to mid-market brands with $10K-$500K monthly ad spend across Google Ads and Meta Ads.

**Use Case:** Marketing teams need to quickly identify:
- **Winners to scale:** High-ROAS campaigns that should receive more budget
- **Losers to cut:** Wasteful spend on zero-conversion campaigns
- **Fatigued creatives:** Ads showing declining performance due to audience overexposure

**Context:** Built for the AIBoomi Hackathon (Pune, Feb 2025) in the Commerce/Shopping category.

## Solution Overview

Agatha is a multi-agent AI system that analyzes ad performance, generates optimization recommendations, and executes approved changes.

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
│ BigQuery / Meta   │         │ Meta API  │
│ (Read)            │         │ (Write)   │
└───────────────────┘         └───────────┘
```

**Agent Responsibilities:**
- **Analyze Agent:** Classifies ad spend as GOOD/BAD/OK based on ROAS thresholds relative to account average
- **Recommend Agent:** Generates actionable budget and creative recommendations with estimated $ impact
- **Execute Agent:** Executes approved changes via platform APIs (mock write for hackathon)

## Setup & Run

### Prerequisites
- Python 3.11+
- Node.js 20+
- Google Cloud SDK (for BigQuery)
- Meta Developer Account (for OAuth)

### Backend Setup
```bash
cd backend
cp .env.example .env
# Edit .env with your credentials

pip install -e .
uvicorn main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
cp .env.local.example .env.local
# Edit .env.local with API URL

npm install
npm run dev
```

### Environment Variables
```env
# AI Provider
AI_PROVIDER=gemini              # gemini | openai
GEMINI_API_KEY=your_key
OPENAI_API_KEY=your_key

# BigQuery
GOOGLE_CLOUD_PROJECT=otb-dev-platform

# Meta API
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
META_REDIRECT_URI=http://localhost:3000/auth/callback
```

### Verify Setup
```bash
# Backend health check
curl http://localhost:8000/

# Run tests
pytest tests/ -v
```

## Models & Data

### AI Models
| Provider | Model | Use Case |
|----------|-------|----------|
| Google | Gemini 2.5 Pro | Primary - Agent reasoning |
| OpenAI | GPT-4 Turbo | Fallback option |

Model selection is config-driven via `AI_PROVIDER` environment variable.

### Data Sources
| Source | Type | Data |
|--------|------|------|
| BigQuery | Primary (dev/test) | Historical ad performance (TL: 298 days, WH: 76 days) |
| Meta Marketing API | Primary (demo) | Live ad data with OAuth |

**BigQuery Views:**
- ThirdLove: `otb-dev-platform.master.northstar_master_combined_tl`
- WhisperingHomes: `otb-dev-platform.master.northstar_master_combined_wh`

### Data Licensing
- BigQuery data: Proprietary (Out of the Blue client data, used with permission)
- Meta API data: Subject to Meta Platform Terms of Service

## Evaluation & Guardrails

### Recommendation Accuracy
| Metric | Target | Measurement |
|--------|--------|-------------|
| Recommendation approval rate | 80%+ | Approved / Total recommendations |
| False positive rate | <10% | User overrides "bad spend" classification |

### Classification Thresholds
```python
# GOOD spend (scale 30-100%)
ROAS >= 2x account_avg AND spend >= $1,000 AND days >= 7

# BAD spend (pause or reduce)
ROAS = 0 after $5,000+ spend AND 7+ days
OR ROAS < 0.5x account_avg after $10,000+

# WAIT (learning phase)
days < 7 OR spend < $1,000
```

### Guardrails
| Risk | Mitigation |
|------|------------|
| **Hallucination** | All recommendations include source data references; thresholds are rule-based, not generated |
| **Bias** | ROAS thresholds are relative to account average, not fixed values; works across different industries |
| **Unauthorized actions** | Human-in-the-loop approval required for all executions; mock writes for hackathon |
| **Data privacy** | OAuth tokens stored in session only; no persistent credential storage |
| **Runaway spend** | Scale recommendations capped at 100% increase; requires explicit approval |

### Confidence Levels
Recommendations include confidence based on data quality:
- **High:** 30+ days data, $10k+ spend, consistent ROAS
- **Medium:** 7-30 days data, $1k-$10k spend
- **Low:** Near threshold boundaries, flagged for review

## Known Limitations & Risks

### Current Limitations
1. **No conversion count data** - ROAS available but not raw conversion counts (limits CPA/CVR analysis)
2. **Mock execution only** - Real Meta API writes not implemented for hackathon safety
3. **Single-platform focus** - Meta Ads primary; Google Ads integration is stretch goal
4. **No cross-channel attribution** - Each platform analyzed independently

### Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Meta API rate limits | Medium | Demo slowdown | BigQuery fallback |
| OAuth token expiry | Low | Auth failure | Long-lived token exchange |
| LLM latency | Medium | >60s analysis | Caching, streaming responses |

### Not In Scope
- Cross-channel attribution modeling
- Long-term brand marketing effectiveness
- Organic marketing channels
- Audience discovery/targeting strategy
- AI-generated creative assets (flagging only)

## Team

| Role | Name | GitHub | Contact |
|------|------|--------|---------|
| Product Manager | Jaidev | [@jaidevk](https://github.com/jaidevk) | - |
| Engineering Lead | Hemanth | [@hemanthj](https://github.com/hemanthj) | - |

**Hackathon:** AIBoomi, Pune
**Category:** Commerce / Shopping / Consumer
**Demo Deadline:** Feb 1, 2025, 09:00 IST

---

Built with Google ADK, FastAPI, Next.js, and Gemini 2.5 Pro.
