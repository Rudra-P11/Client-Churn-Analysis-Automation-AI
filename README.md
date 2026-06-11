# Renewal Intelligence Engine

A production-quality renewal risk scoring and explanation tool that ingests 5 messy, multi-modal data sources, scores every account renewing in the next 90 days, and uses Gemini AI to generate actionable plain-English explanations and surface non-obvious portfolio insights.

---

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Add your Gemini API key
```bash
cp .env.example .env
# Open .env and add your key:
# GEMINI_API_KEY=your_gemini_key_here
```

### 3. Run the pipeline (generates risk report)
```bash
python pipeline.py
# Optional: specify a reference date
python pipeline.py --reference-date 2026-06-09 --window-days 90
```

### 4. Launch the dashboard
```bash
streamlit run app.py
```

The dashboard also has a **▶ Run Pipeline** button in the sidebar that runs everything in one click.

---

## Architecture

```
Data Sources → Data Loader → Feature Engine → Risk Scorer → LLM Analyst → Streamlit Dashboard
```

### Layer-by-layer

| Layer | File | What it does |
|---|---|---|
| **Ingestion** | `src/data_loader.py` | Loads all 5 sources, fuzzy-matches CSM note accounts to IDs, normalises 6 date formats |
| **Features** | `src/feature_engine.py` | Computes usage trend slopes, ticket health scores, SDK risk, NPS risk, renewal urgency |
| **Scoring** | `src/risk_scorer.py` | Weighted 6-signal composite score with binary boosters for compounding risks |
| **LLM** | `src/llm_analyst.py` | 4 distinct Gemini tasks (see below) |
| **Dashboard** | `app.py` | Streamlit app with 3 tabs: Account List, Analytics, Portfolio Insights |
| **CLI** | `pipeline.py` | End-to-end orchestrator, saves `output/risk_report.json` |

---

## How LLMs Are Used (Meaningfully, Not as a Gimmick)

The LLM (Google Gemini 1.5 Flash) performs **4 distinct tasks** that a rule-based system fundamentally cannot do:

### Task 1: CSM Note Sentiment Extraction
CSM notes are messy, informal, and full of implicit signals. The LLM extracts:
- **sentiment_score** (0=high churn risk, 1=likely to renew)
- **risk_flags**: specific signals like "Competitor POC with Kontent.ai underway"
- **key_stakeholder_concern**: what did the executive on the call raise?
- **recommended_action**: one concrete next step

*Why LLM?* Rules can't understand context. "They're fine" = low risk. "They're fine on the product side but the billing team is furious" = high risk. Only semantic understanding catches this.

### Task 2: Non-English NPS Comment Translation
Accounts 1013, 1014, 1017 have NPS comments in Spanish, French, and Mandarin. A rule-based system reads these as noise. The LLM:
- Detects the language
- Translates to English
- Identifies key themes
- Flags when the verbatim sentiment is **misaligned** with the numeric score (a hidden risk signal)

*Account 1017 example*: The Mandarin comment says the customer requested a new CSM twice with no response — the CSM notes confirm this explicitly. A system that can't read Mandarin would miss this entirely.

### Task 3: Per-Account Risk Narratives
For every account renewing in the next 90 days, the LLM generates a structured briefing:
- 2-3 sentence plain-English summary for a BizOps analyst
- Specific risk drivers (not generic categories)
- Concrete action items with urgency
- One-line urgency note

### Task 4: Portfolio-Level Non-Obvious Insights
The LLM analyzes the full at-risk portfolio and surfaces 4 patterns a rule-based system would miss — such as CSM workload concentration, SDK deadline + renewal = "double jeopardy", or silent churn clusters by industry.

---

## Risk Scoring Model

### Signals & Weights (tunable in `risk_scorer.py`)

| Signal | Weight | Rationale |
|---|---|---|
| Usage decline (6-month trend) | 25% | Leading indicator — customers reduce usage before churning |
| Support ticket burden | 20% | Open/escalated P1s signal active pain |
| NPS risk score | 15% | Lagging but important — detractors rarely renew |
| SDK deprecation risk | 15% | Structural/technical cliff — v3.x sunset is April 30, 2026 |
| CSM sentiment (LLM-extracted) | 15% | Qualitative signal from the people closest to the account |
| Renewal urgency | 10% | <30 days compounds all other risks |

### Binary Boosters (stacked on top of weighted score)
- **+0.10**: Any open/escalated P1 tickets
- **+0.10**: Silent churn pattern (NPS ≥ 7 + declining usage)
- **+0.08**: SDK on sunset-critical v3.x

### Tier Thresholds
- **High**: ≥ 0.60
- **Medium**: 0.35 – 0.59
- **Low**: < 0.35

---

## Key Data Decisions

### Reconciling Inconsistencies

| Problem | Solution |
|---|---|
| CSM notes use typos ("Pinacle", "BritePath") | `rapidfuzz` token_set_ratio fuzzy matching, score_cutoff=55 |
| Mixed date formats (6 different formats in notes) | Multi-pattern regex parser with fallbacks |
| Some notes reference accounts by first name only | Scan for first word of company name as last resort |
| Account 1099 called "Harbourside Dining" in notes but is "Oakridge Retail" in data | Fuzzy match correctly identifies via account ID mention |
| Non-English NPS comments | Gemini Task 2 translates before analysis |
| Null resolution times for open tickets | Excluded from avg, still counted in health score |
| Contradictory signals (high NPS + bad usage) | Explicitly flagged as silent_churn_flag, LLM contextualises |

### The Changelog is the Hidden Weapon

The `changelog.md` reveals compounding technical risks that don't appear in structured data:

1. **SDK v3.x sunset (April 30, 2026)**: Accounts 1000–1007 are still on v3.x. They face forced migration AND renewals. This is a "double jeopardy" that a rule-based system treating SDK version as a simple category would score the same as a 3-month-old deprecation.

2. **Legacy editor removal (May 2026)**: Acme Corp's NPS comment says "The new editor is a downgrade." The changelog shows the old editor is being removed — this is existential for that account.

3. **Breaking API change in v4.2.0**: Accounts on SDK v4.0 and v4.1 missed this and are hitting the breaking change. The locale bug (also fixed in v4.2.3) further compounds this.

---

## Non-Obvious Insights (What a Rule-Based System Misses)

1. **Silent churn detection**: Meridian Health (1003) has NPS 8 but usage dropped 40% — the CSM note explicitly describes this as "classic silent churn pattern." The LLM detects similar patterns in other accounts by comparing NPS sentiment against actual usage trends.

2. **Non-English comment gaps**: Pacific Rim Trading (1017) has a Mandarin NPS comment expressing frustration about CSM responsiveness. The CSM notes independently flag this same issue. A system that ignores non-ASCII text would miss the corroboration.

3. **Regulatory risk as a hard deadline**: RedLeaf Healthcare (1013) needs a vendor security questionnaire by May 15 or *by company policy cannot renew*. Atlas Financial (1006) needs SOC 2 compliance they can't get on their plan. These hard deadlines don't appear in any structured field.

4. **CSM relationship risk**: Northstar Logistics (1016) lost their champion — the ops manager who "used to be our biggest champion" is now disillusioned. Orion Education (1009) is at risk because the merger may eliminate the Director of Content who is their main advocate. Champion departure is invisible to structured data.

---

## What I'd Do With More Time

1. **Historical renewal data as labels**: Train a proper ML model (XGBoost, logistic regression) on past renewals to validate and calibrate the weight choices. Right now weights are grounded in logic and domain knowledge but are not empirically tuned.

2. **Streaming/incremental updates**: Rather than a batch pipeline, connect to live Salesforce/Gainsight APIs for real-time signal updates. The pipeline should run on a scheduler, not manually.

3. **Confidence intervals**: The risk scores are point estimates. For a BizOps team, knowing "this is 0.72 ± 0.15" vs "this is 0.72 ± 0.02" changes how they act on it.

4. **Champion network mapping**: Parse email and Slack data to build a graph of who at the customer actually uses the product. Losing a single high-centrality champion should spike the risk score.

5. **Competitor mention tracking**: Build a structured competitor mention database from the CSM notes (Hygraph, Contentful, Kontent.ai, Sanity, Strapi are all mentioned). Track frequency over time as a trend signal.

6. **A/B test the scoring weights**: Run experiments where different weight configurations are used and track prediction accuracy against actual renewal outcomes.

---

## What I'd Change for Production

1. **Secrets management**: AWS Secrets Manager or Vault instead of `.env` files.
2. **Output storage**: Write to a proper database (Postgres + Redshift) not a JSON file.
3. **LLM caching**: Cache Gemini responses with a TTL so re-runs don't burn API quota for unchanged accounts.
4. **Rate limiting & cost control**: Add budget caps on Gemini API calls; use Flash for narratives, Pro for portfolio insights.
5. **Evaluation framework**: Define ground truth (did the account actually churn?) and compute precision/recall for each tier monthly. Tune weights based on outcomes.
6. **Observability**: Log every LLM call with input/output hashes for audit trail and drift detection.
7. **Alerting**: Slack webhook when a new High Risk account appears, or when a previously Low Risk account crosses the Medium threshold.
8. **Access control**: Role-based access so a CSM only sees their own accounts, while a CRO sees the full portfolio.

---

## File Structure

```
renewal_intelligence_takehome/
├── accounts.csv
├── usage_metrics.csv
├── support_tickets.csv
├── csm_notes.txt
├── nps_responses.csv
├── changelog.md
├── src/
│   ├── data_loader.py       # Ingestion + reconciliation
│   ├── feature_engine.py    # Signal computation
│   ├── risk_scorer.py       # Weighted scoring model
│   └── llm_analyst.py       # Gemini integration (4 tasks)
├── pipeline.py              # CLI entrypoint
├── app.py                   # Streamlit dashboard
├── requirements.txt
├── .env.example
├── output/
│   └── risk_report.json     # Generated by pipeline.py
└── README.md
```

---

## Tradeoffs Made

| Decision | Why | Tradeoff |
|---|---|---|
| Gemini 1.5 Flash | Fast, cheap, good at structured extraction | Pro would give better reasoning depth |
| Streamlit over CLI-only | Much better demo experience | Adds dependency, harder to embed in internal tools |
| JSON output file | Simple, portable, easy to inspect | Not queryable at scale; would use DB in production |
| Fuzzy matching at 55% threshold | Catches all the typos in the data | Could false-match similar company names |
| 6-month usage window | Captures recent trend without too much noise | Might miss seasonal patterns |
| Weighted linear model | Transparent, tunable, explainable | Won't capture interaction effects between signals |
