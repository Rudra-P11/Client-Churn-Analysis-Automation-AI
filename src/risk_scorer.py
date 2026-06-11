"""
risk_scorer.py
==============
Weighted multi-signal risk scoring model.
Produces a [0,1] composite score and a High/Medium/Low tier for each account.
"""

from datetime import date

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Tunable weight configuration
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_WEIGHTS = {
    "usage_decline_score":  0.25,   # Usage drop is the strongest leading indicator
    "support_health_score": 0.20,   # Open/escalated P1 tickets = active pain
    "nps_risk_score":       0.15,   # NPS matters but can be decoupled (silent churn)
    "sdk_risk_score":       0.15,   # SDK deprecation is a structural/technical risk
    "csm_sentiment_score":  0.15,   # LLM-extracted sentiment from call notes
    "renewal_urgency_score": 0.10,  # Urgency multiplier (< 30 days = high weight)
}

# Tier thresholds
HIGH_THRESHOLD   = 0.60
MEDIUM_THRESHOLD = 0.35


# ─────────────────────────────────────────────────────────────────────────────
# Boosters: binary flags that push score up regardless of weights
# ─────────────────────────────────────────────────────────────────────────────

BOOSTERS = [
    # (flag_column, boost_amount, description)
    ("p1_open_count",      None,  0.10, "Has open/escalated P1 tickets"),
    ("silent_churn_flag",  None,  0.10, "NPS-usage divergence detected (silent churn)"),
]

BOOSTER_DEFS = [
    {
        "condition": lambda row: row.get("p1_open_count", 0) > 0,
        "boost": 0.10,
        "label": "Open P1 tickets",
    },
    {
        "condition": lambda row: bool(row.get("silent_churn_flag", False)),
        "boost": 0.10,
        "label": "Silent churn pattern (high NPS + declining usage)",
    },
    {
        "condition": lambda row: row.get("sdk_risk_score", 0) >= 1.0,
        "boost": 0.08,
        "label": "SDK v3.x sunset critical — must migrate now",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# Score computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_risk_score(
    row: pd.Series,
    weights: dict | None = None,
) -> dict:
    """
    Compute composite risk score for a single account row.
    Returns dict with: score, tier, signal_breakdown, boosters_applied.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    # Base weighted score
    base_score = 0.0
    signal_breakdown = {}

    for signal, weight in weights.items():
        value = float(row.get(signal, 0.0) or 0.0)
        contribution = value * weight
        base_score += contribution
        signal_breakdown[signal] = {
            "raw_value": round(value, 3),
            "weight":    weight,
            "contribution": round(contribution, 4),
        }

    # Apply boosters
    total_boost = 0.0
    boosters_applied = []
    for booster in BOOSTER_DEFS:
        if booster["condition"](row):
            total_boost += booster["boost"]
            boosters_applied.append(booster["label"])

    final_score = float(np.clip(base_score + total_boost, 0.0, 1.0))

    # Tier assignment
    if final_score >= HIGH_THRESHOLD:
        tier = "High"
    elif final_score >= MEDIUM_THRESHOLD:
        tier = "Medium"
    else:
        tier = "Low"

    return {
        "risk_score":       round(final_score, 4),
        "risk_tier":        tier,
        "base_score":       round(base_score, 4),
        "total_boost":      round(total_boost, 4),
        "signal_breakdown": signal_breakdown,
        "boosters_applied": boosters_applied,
    }


def score_all_accounts(features_df: pd.DataFrame, weights: dict | None = None) -> pd.DataFrame:
    """
    Apply compute_risk_score to every row.
    Returns features_df augmented with: risk_score, risk_tier, signal_breakdown, boosters_applied.
    """
    scored_rows = features_df.apply(
        lambda row: pd.Series(compute_risk_score(row, weights)),
        axis=1,
    )
    df = pd.concat([features_df.reset_index(drop=True),
                    scored_rows.reset_index(drop=True)], axis=1)
    return df


def filter_renewing_accounts(
    scored_df: pd.DataFrame,
    reference_date: date,
    window_days: int = 90,
) -> pd.DataFrame:
    """
    Return only accounts whose contract_end_date falls within [reference_date, reference_date + window_days].
    Sorted by risk_score descending.
    """
    cutoff = date(
        reference_date.year,
        reference_date.month,
        reference_date.day,
    )
    window_end = pd.Timestamp(cutoff) + pd.DateOffset(days=window_days)

    mask = (
        (pd.to_datetime(scored_df["contract_end_date"]) >= pd.Timestamp(cutoff)) &
        (pd.to_datetime(scored_df["contract_end_date"]) <= window_end)
    )
    return scored_df[mask].sort_values("risk_score", ascending=False).reset_index(drop=True)


def get_top_risk_signals(signal_breakdown: dict, n: int = 3) -> list[str]:
    """Return top N signal names by contribution, formatted for display."""
    sorted_signals = sorted(
        signal_breakdown.items(),
        key=lambda kv: kv[1]["contribution"],
        reverse=True,
    )
    labels = {
        "usage_decline_score":   "📉 Declining usage",
        "support_health_score":  "🎫 Support ticket burden",
        "nps_risk_score":        "😟 Low/concerning NPS",
        "sdk_risk_score":        "⚠️ SDK deprecation risk",
        "csm_sentiment_score":   "🗣️ Negative CSM sentiment",
        "renewal_urgency_score": "⏰ Renewal urgency",
    }
    return [labels.get(k, k) for k, _ in sorted_signals[:n]]


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.data_loader import load_all
    from src.feature_engine import build_features

    data    = load_all()
    feat_df = build_features(data)

    # Give placeholder csm_sentiment_score before LLM runs
    feat_df["csm_sentiment_score"] = 0.5

    scored  = score_all_accounts(feat_df)
    renewing = filter_renewing_accounts(scored, data["reference_date"])

    print(f"\nAccounts renewing in next 90 days: {len(renewing)}")
    print(f"  High risk:   {(renewing['risk_tier'] == 'High').sum()}")
    print(f"  Medium risk: {(renewing['risk_tier'] == 'Medium').sum()}")
    print(f"  Low risk:    {(renewing['risk_tier'] == 'Low').sum()}")
    print()
    print(renewing[["account_name", "arr", "contract_end_date",
                    "risk_score", "risk_tier"]].head(15).to_string(index=False))
