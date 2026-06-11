"""
llm_analyst.py
==============
Gemini-powered analysis layer.  Four distinct LLM tasks:

  1. CSM Note Parsing   — Extract structured signals from messy free-text
  2. NPS Translation    — Translate non-English comments + extract sentiment
  3. Account Narrative  — Generate plain-English risk explanation per account
  4. Portfolio Insights — Surface non-obvious cross-portfolio patterns
"""

import json
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv

# Look for .env in both the project root and the src/ folder
_project_root = Path(__file__).parent.parent
_src_dir = Path(__file__).parent
load_dotenv(_project_root / ".env")
load_dotenv(_src_dir / ".env")

# ─────────────────────────────────────────────────────────────────────────────
# Gemini client setup
# ─────────────────────────────────────────────────────────────────────────────

def _get_client() -> genai.GenerativeModel:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY not found. "
            "Create a .env file with GEMINI_API_KEY=your_key"
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=4096,
        ),
    )


def _call_gemini(prompt: str, model: genai.GenerativeModel, retries: int = 4) -> str:
    """Call Gemini with rate-limit-aware retry logic."""
    import re
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            err_str = str(e)
            if attempt < retries - 1:
                # Extract suggested retry delay from 429 error if present
                match = re.search(r'retry_delay\s*\{\s*seconds:\s*(\d+)', err_str)
                wait = int(match.group(1)) + 2 if match else (2 ** (attempt + 2))
                print(f"  [rate-limit] Waiting {wait}s before retry (attempt {attempt+1}/{retries})...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"Gemini API call failed after {retries} retries: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# Task 1: CSM Note Sentiment & Signal Extraction
# ─────────────────────────────────────────────────────────────────────────────

CSM_PARSE_SYSTEM = """You are an expert at extracting structured business intelligence
from messy, informal Customer Success Manager call notes.

For each note, extract:
1. sentiment_score: float from 0.0 (very negative / high churn risk) to 1.0 (very positive / likely to renew).
   Use these guidelines:
   - 0.0–0.2: Active churn signals (competitor POC underway, contract threat, no-shows, budget cuts)
   - 0.2–0.4: Significant concerns (unresolved issues, dissatisfied executives, compliance blockers)
   - 0.4–0.6: Mixed / neutral (some concerns but not critical)
   - 0.6–0.8: Generally positive but with issues
   - 0.8–1.0: Strong renewal signals (expansion plans, budget approved, champion engaged)

2. risk_flags: list of specific risk signals found (be specific, e.g. "Competitor POC with Kontent.ai underway")
3. positive_signals: list of positive renewal signals
4. key_stakeholder_concern: single most important concern raised by customer executives (or null)
5. recommended_action: one concrete action the account team should take NOW

Respond ONLY with valid JSON. No markdown, no explanation."""

def extract_csm_signals(notes: list[str], model: genai.GenerativeModel) -> dict:
    """
    Task 1: Given a list of raw CSM note strings for one account,
    extract structured sentiment and signals.
    Returns dict with sentiment_score (0-1, inverted to risk: 1-score), risk_flags, etc.
    """
    if not notes:
        return {
            "sentiment_score": 0.5,
            "csm_sentiment_score": 0.5,
            "risk_flags": [],
            "positive_signals": [],
            "key_stakeholder_concern": None,
            "recommended_action": None,
        }

    combined = "\n\n---\n\n".join(notes)
    prompt = f"""{CSM_PARSE_SYSTEM}

CSM Notes to analyze:
\"\"\"
{combined}
\"\"\"

Return JSON with keys: sentiment_score, risk_flags, positive_signals, key_stakeholder_concern, recommended_action"""

    try:
        raw = _call_gemini(prompt, model)
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        # Add inverted score as risk score (1 - sentiment = risk)
        sentiment = float(result.get("sentiment_score", 0.5))
        result["csm_sentiment_score"] = round(1.0 - sentiment, 4)
        return result
    except Exception as e:
        print(f"  [LLM] CSM parse failed: {e}")
        return {
            "sentiment_score": 0.5,
            "csm_sentiment_score": 0.5,
            "risk_flags": [],
            "positive_signals": [],
            "key_stakeholder_concern": None,
            "recommended_action": None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Task 2: NPS Comment Translation + Sentiment
# ─────────────────────────────────────────────────────────────────────────────

def translate_and_analyze_nps(comment: str, score: float,
                               model: genai.GenerativeModel) -> dict:
    """
    Task 2: Translate non-English NPS comment to English and extract themes.
    Returns dict with: english_translation, detected_language, key_themes, sentiment_alignment.
    sentiment_alignment: whether the verbatim matches the numeric score.
    """
    if not comment or not comment.strip():
        return {
            "english_translation": "",
            "detected_language": "en",
            "key_themes": [],
            "sentiment_alignment": "consistent",
        }

    prompt = f"""You are analyzing a customer NPS survey response. 

NPS Score: {score}/10
Verbatim Comment: "{comment}"

Tasks:
1. Detect the language (if not English, translate to English)
2. Identify 2-3 key themes (e.g., "poor support response time", "API performance issues")
3. Assess if the verbatim sentiment is CONSISTENT or MISALIGNED with the numeric score
   (e.g., score=8 but comment expresses frustration = "misaligned" — possible churn risk)

Respond ONLY with JSON:
{{
  "english_translation": "...",
  "detected_language": "...",
  "key_themes": ["theme1", "theme2"],
  "sentiment_alignment": "consistent" or "misaligned",
  "alignment_note": "brief explanation if misaligned"
}}"""

    try:
        raw = _call_gemini(prompt, model)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"  [LLM] NPS translation failed: {e}")
        return {
            "english_translation": comment,
            "detected_language": "unknown",
            "key_themes": [],
            "sentiment_alignment": "consistent",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Task 3: Per-Account Risk Narrative
# ─────────────────────────────────────────────────────────────────────────────

NARRATIVE_SYSTEM = """You are a senior BizOps analyst at Contentstack, a headless CMS company.
Your job is to write concise, actionable renewal risk summaries for the account team.

Be direct. BizOps people are busy. Write for someone who needs to act TODAY.
Avoid filler phrases. Lead with the most critical signal.
If there's a competitor mentioned, name them.
If there's a regulatory or technical deadline, be specific about the date."""

def generate_account_narrative(account_data: dict, model: genai.GenerativeModel) -> dict:
    """
    Task 3: Generate a plain-English risk narrative for one account.
    Returns dict with: summary, risk_drivers, recommended_actions, urgency_note.
    """
    # Build structured context for the LLM
    sdk_risk_desc = {
        1.0: "⚠️ CRITICAL: On SDK v3.x — sunset deadline was April 30, 2026. Security patches stopped.",
        0.6: "On SDK v4.0/v4.1 — affected by locale bug (fixed in v4.2.3). Missing breaking change fix.",
        0.15: "On SDK v4.2.x — stable but missing latest improvements.",
        0.0: "On latest SDK v4.3.x — fully up to date.",
    }.get(round(account_data.get("sdk_risk_score", 0), 2), "SDK version risk is moderate.")

    silent_churn = "YES — NPS score is high but usage has been declining (classic silent churn pattern)" \
        if account_data.get("silent_churn_flag") else "No"

    csm_note_text = "\n".join(account_data.get("csm_notes_raw", [])) or "No recent CSM notes."

    nps_comment = account_data.get("english_translation") or account_data.get("verbatim_comment", "")
    nps_info = f"Score: {account_data.get('nps_score', 'N/A')}/10\nComment: \"{nps_comment}\""
    if account_data.get("detected_language", "en") not in ("en", "english", "English"):
        nps_info += f"\n(Original in {account_data.get('detected_language', 'unknown')})"
    if account_data.get("sentiment_alignment") == "misaligned":
        nps_info += f"\n⚠️ MISALIGNMENT DETECTED: {account_data.get('alignment_note', '')}"

    prompt = f"""{NARRATIVE_SYSTEM}

=== ACCOUNT BRIEFING ===
Account: {account_data.get('account_name')} (ID: {account_data.get('account_id')})
ARR: ${account_data.get('arr', 0):,.0f}
Plan: {account_data.get('plan_tier')} | Industry: {account_data.get('industry')} | Region: {account_data.get('region')}
Contract Ends: {account_data.get('contract_end_date')} ({account_data.get('days_to_renewal')} days from today)
CSM: {account_data.get('csm_name')}

=== RISK SIGNALS ===
Composite Risk Score: {account_data.get('risk_score', 0):.2f}/1.00 → {account_data.get('risk_tier')} Risk

Usage Trend (6-month decline score): {account_data.get('usage_decline_score', 0):.2f}/1.00
Silent Churn Pattern: {silent_churn}

Support Tickets (last 6 months):
- Total: {account_data.get('ticket_count_total', 0)}
- Open/Escalated P1s: {account_data.get('p1_open_count', 0)}
- Open/Escalated total: {account_data.get('open_ticket_count', 0)}

SDK Risk: {sdk_risk_desc}

NPS:
{nps_info}

CSM Notes:
{csm_note_text[:1500]}

LLM-Extracted CSM Risk Flags: {account_data.get('risk_flags', [])}
LLM-Extracted Positive Signals: {account_data.get('positive_signals', [])}
Key Stakeholder Concern: {account_data.get('key_stakeholder_concern', 'None identified')}
=== END BRIEFING ===

Write a renewal risk briefing with:
1. "summary": 2-3 sentences capturing the core risk narrative. Be specific, not generic.
2. "risk_drivers": list of 3-5 specific, concrete risk factors (not generic categories)
3. "recommended_actions": list of 2-4 specific actions the account team should take, with urgency
4. "urgency_note": one sentence on why this can't wait

Return ONLY valid JSON with these 4 keys."""

    try:
        raw = _call_gemini(prompt, model)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        result = json.loads(raw.strip())
        return result
    except Exception as e:
        print(f"  [LLM] Narrative generation failed for {account_data.get('account_name')}: {e}")
        return {
            "summary": f"Risk data computed but narrative generation failed. Risk score: {account_data.get('risk_score', 0):.2f}",
            "risk_drivers": account_data.get("risk_flags", []),
            "recommended_actions": ["Review account signals manually"],
            "urgency_note": f"Contract ends {account_data.get('contract_end_date')}.",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Task 4: Portfolio-Level Non-Obvious Insights
# ─────────────────────────────────────────────────────────────────────────────

def generate_portfolio_insights(
    high_risk_accounts: list[dict],
    all_accounts_summary: dict,
    model: genai.GenerativeModel,
) -> dict:
    """
    Task 4: Analyse the full at-risk portfolio and surface non-obvious patterns
    that a rule-based system would miss.
    """
    # Build a concise portfolio summary for the LLM
    acct_summaries = []
    for a in high_risk_accounts[:20]:  # Top 20 for context window
        acct_summaries.append(
            f"- {a.get('account_name')} (ARR ${a.get('arr',0):,.0f}, "
            f"{a.get('risk_tier')} risk, SDK: {a.get('latest_sdk_version','?')}, "
            f"CSM: {a.get('csm_name','?')}, Industry: {a.get('industry','?')}, "
            f"Region: {a.get('region','?')}, "
            f"Silent churn: {a.get('silent_churn_flag', False)}, "
            f"P1 open: {a.get('p1_open_count', 0)}, "
            f"NPS: {a.get('nps_score', 'N/A')})"
        )

    portfolio_text = "\n".join(acct_summaries)

    prompt = f"""You are a senior revenue analytics expert at a SaaS company.

You have {all_accounts_summary.get('total_renewing')} accounts renewing in the next 90 days.
Total ARR at risk: ${all_accounts_summary.get('total_arr_at_risk', 0):,.0f}
Distribution: {all_accounts_summary.get('high_count')} High, {all_accounts_summary.get('medium_count')} Medium, {all_accounts_summary.get('low_count')} Low risk

Top at-risk accounts:
{portfolio_text}

Context: The product recently sunset SDK v3.x (April 30, 2026), is removing the legacy editor in May 2026, 
and had a breaking API change in v4.2.0 that affected all customers on older SDK versions.

Your task: Surface 4 NON-OBVIOUS insights that a simple rule-based risk system would completely miss.
Think about:
- Patterns across CSMs (is one CSM overloaded?)
- Industry-specific risk clusters
- Compounding risk factors that individually seem minor but together are dangerous
- Timing correlations (SDK sunset + renewal = double jeopardy)
- Silent churn patterns where good NPS masks real disengagement
- Accounts that look "safe" but have hidden risk signals

For each insight, explain:
1. What you noticed
2. Why a rule-based system would miss it
3. What action it implies

Return ONLY valid JSON:
{{
  "insights": [
    {{
      "title": "...",
      "observation": "...",
      "why_non_obvious": "...",
      "action": "...",
      "affected_accounts": ["account1", "account2"]
    }}
  ],
  "executive_summary": "2-3 sentence portfolio-level summary for a VP of CS or CRO"
}}"""

    try:
        raw = _call_gemini(prompt, model)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"  [LLM] Portfolio insights failed: {e}")
        return {
            "insights": [],
            "executive_summary": "Portfolio analysis could not be completed.",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Master LLM pipeline runner
# ─────────────────────────────────────────────────────────────────────────────

def run_llm_analysis(
    scored_df,
    renewing_df,
    verbose: bool = True,
) -> tuple:
    """
    Run all 4 LLM tasks:
    1. CSM sentiment for all renewing accounts with notes
    2. NPS translation for non-English comments
    3. Per-account narratives for renewing accounts
    4. Portfolio insights

    Returns (enriched_renewing_df, portfolio_insights_dict)
    """
    model = _get_client()

    renewing = renewing_df.copy()

    # ── Task 1: CSM Sentiment ─────────────────────────────────────────────────
    if verbose:
        print("\n[LLM Task 1] Extracting CSM note signals...")

    csm_results = {}
    for _, row in renewing.iterrows():
        aid = row["account_id"]
        notes = row.get("csm_notes_raw", [])
        if verbose and notes:
            print(f"  → {row['account_name']} ({len(notes)} note(s))")
        result = extract_csm_signals(notes if isinstance(notes, list) else [], model)
        csm_results[aid] = result
        time.sleep(4)  # Respect free-tier rate limit (~15 RPM)

    # Merge CSM sentiment into renewing
    renewing["csm_sentiment_score"] = renewing["account_id"].map(
        lambda aid: csm_results.get(aid, {}).get("csm_sentiment_score", 0.5)
    )
    renewing["risk_flags"]              = renewing["account_id"].map(
        lambda aid: csm_results.get(aid, {}).get("risk_flags", []))
    renewing["positive_signals"]        = renewing["account_id"].map(
        lambda aid: csm_results.get(aid, {}).get("positive_signals", []))
    renewing["key_stakeholder_concern"] = renewing["account_id"].map(
        lambda aid: csm_results.get(aid, {}).get("key_stakeholder_concern"))
    renewing["csm_recommended_action"]  = renewing["account_id"].map(
        lambda aid: csm_results.get(aid, {}).get("recommended_action"))

    # ── Task 2: NPS Translation ───────────────────────────────────────────────
    if verbose:
        print("\n[LLM Task 2] Translating non-English NPS comments...")

    nps_results = {}
    non_english_mask = renewing["has_non_english"].fillna(False).astype(bool)
    for _, row in renewing[non_english_mask].iterrows():
        aid = row["account_id"]
        if verbose:
            print(f"  → {row['account_name']} (NPS comment in foreign language)")
        result = translate_and_analyze_nps(
            str(row.get("verbatim_comment", "")),
            float(row.get("nps_score", 5)),
            model,
        )
        nps_results[aid] = result
        time.sleep(4)

    def _get_translation(aid):
        if aid in nps_results:
            return nps_results[aid].get("english_translation", "")
        matches = renewing.loc[renewing["account_id"] == aid, "verbatim_comment"]
        return matches.values[0] if len(matches) > 0 else ""

    renewing["english_translation"] = renewing["account_id"].map(_get_translation)
    renewing["detected_language"]   = renewing["account_id"].map(
        lambda aid: nps_results.get(aid, {}).get("detected_language", "en"))
    renewing["nps_key_themes"]      = renewing["account_id"].map(
        lambda aid: nps_results.get(aid, {}).get("key_themes", []))
    renewing["sentiment_alignment"] = renewing["account_id"].map(
        lambda aid: nps_results.get(aid, {}).get("sentiment_alignment", "consistent"))
    renewing["alignment_note"]      = renewing["account_id"].map(
        lambda aid: nps_results.get(aid, {}).get("alignment_note", ""))

    # ── Re-score with LLM sentiment filled in ────────────────────────────────
    if verbose:
        print("\n[Re-scoring] Applying LLM CSM sentiment to risk scores...")

    from src.risk_scorer import compute_risk_score
    updated_scores = renewing.apply(lambda row: pd.Series(compute_risk_score(row)), axis=1)
    renewing["risk_score"]       = updated_scores["risk_score"]
    renewing["risk_tier"]        = updated_scores["risk_tier"]
    renewing["signal_breakdown"] = updated_scores["signal_breakdown"]
    renewing["boosters_applied"] = updated_scores["boosters_applied"]
    renewing = renewing.sort_values("risk_score", ascending=False).reset_index(drop=True)

    # ── Task 3: Per-account narratives ────────────────────────────────────────
    if verbose:
        print("\n[LLM Task 3] Generating per-account risk narratives...")

    # Only generate narratives for High + Medium risk accounts (BizOps priority)
    # Low risk accounts get a placeholder — saves ~60% of API calls
    narrative_targets = renewing[renewing["risk_tier"].isin(["High", "Medium"])]
    if verbose:
        low_count = (renewing["risk_tier"] == "Low").sum()
        print(f"  (Skipping narratives for {low_count} Low-risk accounts to respect rate limits)")

    narratives = {}
    for _, row in narrative_targets.iterrows():
        aid = row["account_id"]
        if verbose:
            print(f"  → {row['account_name']} ({row['risk_tier']} risk, score={row['risk_score']:.2f})")
        narrative = generate_account_narrative(row.to_dict(), model)
        narratives[aid] = narrative
        time.sleep(6)  # Respect free-tier rate limit

    renewing["narrative_summary"]      = renewing["account_id"].map(
        lambda aid: narratives.get(aid, {}).get("summary", ""))
    renewing["narrative_risk_drivers"] = renewing["account_id"].map(
        lambda aid: narratives.get(aid, {}).get("risk_drivers", []))
    renewing["narrative_actions"]      = renewing["account_id"].map(
        lambda aid: narratives.get(aid, {}).get("recommended_actions", []))
    renewing["narrative_urgency"]      = renewing["account_id"].map(
        lambda aid: narratives.get(aid, {}).get("urgency_note", ""))

    # ── Task 4: Portfolio insights ────────────────────────────────────────────
    if verbose:
        print("\n[LLM Task 4] Generating portfolio-level insights...")

    portfolio_summary = {
        "total_renewing": len(renewing),
        "total_arr_at_risk": renewing["arr"].sum(),
        "high_count":   (renewing["risk_tier"] == "High").sum(),
        "medium_count": (renewing["risk_tier"] == "Medium").sum(),
        "low_count":    (renewing["risk_tier"] == "Low").sum(),
    }
    high_risk_list = renewing[renewing["risk_tier"] == "High"].to_dict(orient="records")
    portfolio_insights = generate_portfolio_insights(high_risk_list, portfolio_summary, model)

    if verbose:
        print("\n✅ LLM analysis complete.")

    return renewing, portfolio_insights
