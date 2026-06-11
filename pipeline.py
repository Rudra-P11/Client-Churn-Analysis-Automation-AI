"""
pipeline.py
===========
CLI entrypoint - runs the full Renewal Intelligence pipeline end-to-end
and saves results to output/risk_report.json.

Usage:
    python pipeline.py [--reference-date YYYY-MM-DD] [--window-days 90]
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd


def run_pipeline(reference_date: date, window_days: int = 90, verbose: bool = True) -> dict:
    if verbose:
        print("=" * 60)
        print("  RENEWAL INTELLIGENCE ENGINE")
        print("=" * 60)
        print(f"  Reference date : {reference_date}")
        print(f"  Renewal window : {window_days} days")
        print("=" * 60)

    # Step 1: Load data
    if verbose:
        print("\n[1/5] Loading and reconciling data sources...")
    from src.data_loader import load_all
    data = load_all(reference_date)
    if verbose:
        print(f"  [OK] {len(data['accounts'])} accounts")
        print(f"  [OK] {len(data['usage'])} usage rows")
        print(f"  [OK] {len(data['tickets'])} tickets")
        print(f"  [OK] {len(data['nps'])} NPS responses")
        csm_matched = sum(1 for n in data['csm_notes'] if n['account_id'])
        print(f"  [OK] {csm_matched}/{len(data['csm_notes'])} CSM notes matched to accounts")

    # Step 2: Feature engineering
    if verbose:
        print("\n[2/5] Computing features...")
    from src.feature_engine import build_features
    feat_df = build_features(data)
    feat_df["csm_sentiment_score"] = 0.5
    if verbose:
        print(f"  [OK] Features computed for {len(feat_df)} accounts")
        print(f"  [OK] Silent churn flags: {feat_df['silent_churn_flag'].sum()}")

    # Step 3: Pre-LLM scoring
    if verbose:
        print("\n[3/5] Initial risk scoring...")
    from src.risk_scorer import score_all_accounts, filter_renewing_accounts
    scored_df  = score_all_accounts(feat_df)
    renewing   = filter_renewing_accounts(scored_df, reference_date, window_days)
    if verbose:
        print(f"  [OK] {len(renewing)} accounts renewing in next {window_days} days")
        print(f"     High:   {(renewing['risk_tier'] == 'High').sum()}")
        print(f"     Medium: {(renewing['risk_tier'] == 'Medium').sum()}")
        print(f"     Low:    {(renewing['risk_tier'] == 'Low').sum()}")

    # Step 4: LLM analysis
    if verbose:
        print("\n[4/5] Running LLM analysis (Gemini)...")
        print("  Making API calls for each account - may take 2-3 minutes...")
    from src.llm_analyst import run_llm_analysis
    enriched, portfolio_insights = run_llm_analysis(scored_df, renewing, verbose=verbose)

    # Step 5: Save output
    if verbose:
        print("\n[5/5] Saving results...")

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    def safe_val(v):
        """Convert non-JSON-serialisable types."""
        if isinstance(v, (date, pd.Timestamp)):
            return str(v)
        if isinstance(v, float) and (v != v):  # NaN
            return None
        try:
            if pd.isna(v) and not isinstance(v, (list, dict, str, bool)):
                return None
        except Exception:
            pass
        return v

    def row_to_dict(row):
        d = {}
        for k, v in row.items():
            if isinstance(v, list):
                d[k] = v
            elif isinstance(v, dict):
                d[k] = v
            elif isinstance(v, pd.Timestamp):
                d[k] = str(v.date())
            elif hasattr(v, 'item'):  # numpy scalar
                d[k] = v.item()
            else:
                d[k] = safe_val(v)
        return d

    report = {
        "meta": {
            "reference_date": str(reference_date),
            "window_days": window_days,
            "generated_at": str(date.today()),
            "total_renewing": len(enriched),
            "total_arr_at_risk": int(enriched["arr"].sum()),
            "high_risk_count":   int((enriched["risk_tier"] == "High").sum()),
            "medium_risk_count": int((enriched["risk_tier"] == "Medium").sum()),
            "low_risk_count":    int((enriched["risk_tier"] == "Low").sum()),
        },
        "portfolio_insights": portfolio_insights,
        "accounts": [row_to_dict(row) for _, row in enriched.iterrows()],
    }

    report_path = output_dir / "risk_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    if verbose:
        print(f"  [OK] Report saved to {report_path}")
        print()
        print("=" * 60)
        print("  PIPELINE COMPLETE")
        print("=" * 60)
        print("  Run dashboard: streamlit run app.py")
        print("=" * 60)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Renewal Intelligence Engine")
    parser.add_argument(
        "--reference-date",
        default=str(date.today()),
        help="Reference date for 'today' (YYYY-MM-DD). Default: today",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=90,
        help="Days forward to look for renewals. Default: 90",
    )
    args = parser.parse_args()

    ref_date = date.fromisoformat(args.reference_date)
    run_pipeline(ref_date, args.window_days)
