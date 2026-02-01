# AI Impact Statement

**Project:** Agatha - Ad Spend Optimization Agent
**Date:** February 2025
**Organization:** Consequential.io

---

## What the AI Does

Agatha is a multi-agent system that analyzes advertising performance data, detects spending anomalies, and generates optimization recommendations. Three specialized agents work sequentially: **Analyze** (classifies ad spend as good/bad/ok based on ROAS), **Recommend** (suggests budget adjustments with estimated impact), and **Execute** (applies approved changes via APIs).

## Models Used

**Primary:** Google Gemini 2.5 Pro via Google ADK (Agent Development Kit). Selected for superior structured data reasoning, long context window (1M tokens), and native tool-calling support. The model interprets performance patterns and generates human-readable recommendations with confidence scores.

## Data Provenance & Licenses

- **BigQuery data:** Proprietary ecommerce ad performance data from Out of the Blue clients, used with explicit permission for development and demonstration
- **Meta Marketing API:** Live data accessed via OAuth with user consent, subject to Meta Platform Terms of Service
- No training data is extracted; all inference is on production models

## Hallucination/Bias Mitigations

- **Rule-based thresholds:** Classification logic (GOOD/BAD/OK) uses deterministic rules, not LLM generation
- **Source citations:** All recommendations include underlying data references
- **Relative benchmarks:** ROAS thresholds are relative to account averages, avoiding industry bias
- **Human-in-the-loop:** All execution actions require explicit user approval
- **Dry-run mode:** Production writes disabled during hackathon; mock execution only

## Expected Outcomes

- **User:** Reduced time-to-insight from 48 hours to <5 minutes; actionable recommendations vs. raw data
- **Business:** 10-30% reduction in wasted ad spend; higher ROI on marketing investment
- **Safety:** No autonomous actions; transparent reasoning; reversible recommendations only

---

*Word count: 198*
