"""
enrich_report.py
================
Picks up where the pipeline left off.

Loads the existing output/risk_report.json, checks which accounts are
missing LLM-generated narratives / CSM signals / portfolio insights,
and calls Gemini only for those gaps.  Saves the enriched report back
to output/risk_report.json in place.

Usage:
    python enrich_report.py

No flags needed - it auto-detects what's missing.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

REPORT_PATH = Path("output/risk_report.json")


def is_real_narrative(text: str) -> bool:
    """Returns True if the narrative is a real LLM output, not a fallback placeholder."""
    if not text:
        return False
    placeholders = [
        "narrative generation failed",
        "Review account signals manually",
        "Risk data computed but",
    ]
    return not any(p in text for p in placeholders)


def main():
    # ── Load existing report ──────────────────────────────────────────────────
    if not REPORT_PATH.exists():
        print("ERROR: output/risk_report.json not found. Run pipeline.py first.")
        sys.exit(1)

    with open(REPORT_PATH, encoding="utf-8") as f:
        report = json.load(f)

    accounts = report["accounts"]
    print(f"Loaded report with {len(accounts)} accounts.")

    # ── Audit what's missing ──────────────────────────────────────────────────
    needs_narrative = [
        a for a in accounts
        if not is_real_narrative(a.get("narrative_summary", ""))
    ]
    needs_csm = [
        a for a in accounts
        if not a.get("risk_flags") and a.get("csm_notes_raw")
    ]
    needs_nps_translation = [
        a for a in accounts
        if a.get("has_non_english") and not a.get("english_translation")
    ]
    needs_portfolio = not bool(
        report.get("portfolio_insights", {}).get("insights")
    )

    print(f"Missing narratives:         {len(needs_narrative)} accounts")
    print(f"Missing CSM signals:        {len(needs_csm)} accounts")
    print(f"Missing NPS translations:   {len(needs_nps_translation)} accounts")
    print(f"Missing portfolio insights: {'YES' if needs_portfolio else 'no'}")

    total_calls = len(needs_narrative) + len(needs_csm) + len(needs_nps_translation) + (1 if needs_portfolio else 0)
    if total_calls == 0:
        print("\nReport is already fully enriched. Nothing to do.")
        print("Run:  streamlit run app.py")
        return

    print(f"\nTotal LLM calls needed: {total_calls}")
    print("Starting enrichment (4s between calls to respect rate limits)...\n")

    # ── Init Gemini ───────────────────────────────────────────────────────────
    from src.llm_analyst import (
        _get_client,
        extract_csm_signals,
        translate_and_analyze_nps,
        generate_account_narrative,
        generate_portfolio_insights,
    )
    model = _get_client()

    # Build a lookup dict keyed by account_id for fast updates
    acct_by_id = {a["account_id"]: a for a in accounts}

    # ── Fill missing CSM signals ──────────────────────────────────────────────
    if needs_csm:
        print(f"[1/4] Extracting CSM signals for {len(needs_csm)} accounts...")
        for a in needs_csm:
            print(f"  -> {a['account_name']}")
            result = extract_csm_signals(a.get("csm_notes_raw", []), model)
            acct_by_id[a["account_id"]].update({
                "csm_sentiment_score":   result.get("csm_sentiment_score", 0.5),
                "risk_flags":            result.get("risk_flags", []),
                "positive_signals":      result.get("positive_signals", []),
                "key_stakeholder_concern": result.get("key_stakeholder_concern"),
                "csm_recommended_action":  result.get("recommended_action"),
            })
            if os.getenv("LLM_PROVIDER", "gemini").lower() == "gemini":
                time.sleep(4)
    else:
        print("[1/4] CSM signals - already complete, skipping.")

    # ── Fill missing NPS translations ─────────────────────────────────────────
    if needs_nps_translation:
        print(f"\n[2/4] Translating {len(needs_nps_translation)} non-English NPS comments...")
        for a in needs_nps_translation:
            print(f"  -> {a['account_name']}")
            result = translate_and_analyze_nps(
                str(a.get("verbatim_comment", "")),
                float(a.get("nps_score", 5)),
                model,
            )
            acct_by_id[a["account_id"]].update({
                "english_translation": result.get("english_translation", ""),
                "detected_language":   result.get("detected_language", "en"),
                "nps_key_themes":      result.get("key_themes", []),
                "sentiment_alignment": result.get("sentiment_alignment", "consistent"),
                "alignment_note":      result.get("alignment_note", ""),
            })
            if os.getenv("LLM_PROVIDER", "gemini").lower() == "gemini":
                time.sleep(4)
    else:
        print("[2/4] NPS translations - already complete, skipping.")

    # ── Fill missing narratives ───────────────────────────────────────────────
    if needs_narrative:
        print(f"\n[3/4] Generating narratives for {len(needs_narrative)} accounts...")
        for a in needs_narrative:
            print(f"  -> {a['account_name']} ({a['risk_tier']} risk, score={a['risk_score']:.2f})")
            # Use the now-updated account data (may have fresh CSM flags)
            narrative = generate_account_narrative(acct_by_id[a["account_id"]], model)
            acct_by_id[a["account_id"]].update({
                "narrative_summary":      narrative.get("summary", ""),
                "narrative_risk_drivers": narrative.get("risk_drivers", []),
                "narrative_actions":      narrative.get("recommended_actions", []),
                "narrative_urgency":      narrative.get("urgency_note", ""),
            })
            if os.getenv("LLM_PROVIDER", "gemini").lower() == "gemini":
                time.sleep(6)
    else:
        print("[3/4] Narratives - already complete, skipping.")

    # ── Generate portfolio insights ───────────────────────────────────────────
    if needs_portfolio:
        print("\n[4/4] Generating portfolio insights...")
        high_risk = [a for a in accounts if a.get("risk_tier") == "High"]
        meta = report.get("meta", {})
        summary = {
            "total_renewing":    len(accounts),
            "total_arr_at_risk": sum(a.get("arr", 0) for a in accounts),
            "high_count":        meta.get("high_risk_count", len(high_risk)),
            "medium_count":      meta.get("medium_risk_count", 0),
            "low_count":         meta.get("low_risk_count", 0),
        }
        insights = generate_portfolio_insights(high_risk, summary, model)
        report["portfolio_insights"] = insights
        print("  -> Portfolio insights generated.")
    else:
        print("[4/4] Portfolio insights - already complete, skipping.")

    # ── Save enriched report ──────────────────────────────────────────────────
    report["accounts"] = list(acct_by_id.values())

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\nReport saved to {REPORT_PATH}")
    print("\nAll done! Launch the dashboard with:")
    print("  streamlit run app.py")


if __name__ == "__main__":
    main()
