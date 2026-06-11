"""
feature_engine.py
=================
Computes per-account features (signals) used by the risk scorer.
All features are normalised to [0, 1] where 1 = highest risk.
"""

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats  # for linregress


# ─────────────────────────────────────────────────────────────────────────────
# 1. USAGE FEATURES
# ─────────────────────────────────────────────────────────────────────────────

def compute_usage_features(usage_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each account compute:
    - api_calls_trend        : normalised slope of API call volume (negative → declining)
    - active_users_trend     : normalised slope of active users
    - workflow_trend         : normalised slope of workflows triggered
    - latest_sdk_version     : most recent SDK version string
    - usage_decline_score    : [0,1] risk from declining usage
    - avg_api_calls_6m       : raw average for display
    """
    records = []

    for acct_id, grp in usage_df.groupby("account_id"):
        grp = grp.sort_values("month").reset_index(drop=True)
        n = len(grp)

        x = np.arange(n)  # months as integers

        def slope_risk(series: pd.Series) -> float:
            """Return normalised risk [0,1]: 1 = max decline, 0 = flat or growing."""
            s = series.values.astype(float)
            if n < 2 or s.max() == 0:
                return 0.0
            slope, _, _, _, _ = stats.linregress(x, s)
            # Normalise by mean to get % change per month
            mean_val = s.mean()
            if mean_val == 0:
                return 0.0
            pct_slope = slope / mean_val  # e.g. -0.05 = 5% drop per month
            # Clamp and invert (bigger decline → higher risk)
            return float(np.clip(-pct_slope * 4, 0, 1))  # 25%+ decline = full risk

        api_risk   = slope_risk(grp["api_calls"])
        user_risk  = slope_risk(grp["active_users"])
        wflow_risk = slope_risk(grp["workflows_triggered"])

        # Recent vs early half comparison (another signal of step-change drops)
        mid = n // 2
        recent_api = grp["api_calls"].iloc[mid:].mean()
        early_api  = grp["api_calls"].iloc[:mid].mean()
        step_drop  = 0.0
        if early_api > 0:
            pct_drop = (early_api - recent_api) / early_api
            step_drop = float(np.clip(pct_drop * 2, 0, 1))  # 50% drop → 1.0

        usage_decline_score = float(np.clip(
            0.4 * api_risk + 0.3 * user_risk + 0.3 * wflow_risk * 0.5 + 0.5 * step_drop,
            0, 1
        ))

        records.append({
            "account_id":           acct_id,
            "api_calls_slope_risk": api_risk,
            "active_users_slope_risk": user_risk,
            "workflow_slope_risk":  wflow_risk,
            "usage_step_drop":      step_drop,
            "usage_decline_score":  usage_decline_score,
            "latest_sdk_version":   grp["sdk_version"].iloc[-1],
            "avg_api_calls_6m":     grp["api_calls"].mean(),
            "latest_active_users":  grp["active_users"].iloc[-1],
            "avg_active_users":     grp["active_users"].mean(),
            # Keep monthly series for display
            "api_calls_series":     grp[["month", "api_calls"]].to_dict(orient="records"),
        })

    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────
# 2. SUPPORT TICKET FEATURES
# ─────────────────────────────────────────────────────────────────────────────

PRIORITY_WEIGHT = {"P1": 4, "P2": 2, "P3": 1, "P4": 0.5}
STATUS_WEIGHT   = {"Open": 2.0, "Escalated": 2.5, "Resolved": 0.2}

def compute_ticket_features(tickets_df: pd.DataFrame, reference_date: date) -> pd.DataFrame:
    """
    For each account compute:
    - ticket_count_total     : total tickets in window
    - p1_open_count          : open/escalated P1 tickets (worst signal)
    - avg_resolution_hours   : mean resolution time for resolved tickets
    - support_health_score   : [0,1] risk score
    - ticket_subjects        : list of distinct subjects (for display)
    """
    # Only look at tickets in the past 6 months
    cutoff = pd.Timestamp(reference_date) - pd.DateOffset(months=6)
    recent = tickets_df[pd.to_datetime(tickets_df["created_date"]) >= cutoff].copy()
    recent["priority_weight"] = recent["priority"].map(PRIORITY_WEIGHT).fillna(1)
    recent["status_weight"]   = recent["status"].map(STATUS_WEIGHT).fillna(1)
    recent["ticket_score"]    = recent["priority_weight"] * recent["status_weight"]

    records = []
    for acct_id, grp in recent.groupby("account_id"):
        p1_open = grp[(grp["priority"] == "P1") &
                      (grp["status"].isin(["Open", "Escalated"]))].shape[0]
        total_score = grp["ticket_score"].sum()
        # Normalise: assume >30 score = max risk (empirical from data distribution)
        support_health_score = float(np.clip(total_score / 30, 0, 1))

        avg_res = grp[grp["status"] == "Resolved"]["resolution_time_hours"].mean()

        records.append({
            "account_id":           acct_id,
            "ticket_count_total":   len(grp),
            "p1_open_count":        p1_open,
            "avg_resolution_hours": round(avg_res, 1) if not np.isnan(avg_res) else None,
            "support_health_score": support_health_score,
            "open_ticket_count":    grp[grp["status"].isin(["Open", "Escalated"])].shape[0],
            "ticket_subjects":      grp["subject"].unique().tolist(),
        })

    return pd.DataFrame(records) if records else pd.DataFrame(
        columns=["account_id", "ticket_count_total", "p1_open_count",
                 "avg_resolution_hours", "support_health_score",
                 "open_ticket_count", "ticket_subjects"]
    )


# ─────────────────────────────────────────────────────────────────────────────
# 3. NPS FEATURES
# ─────────────────────────────────────────────────────────────────────────────

def compute_nps_features(nps_df: pd.DataFrame) -> pd.DataFrame:
    """
    - nps_score           : raw 0–10
    - nps_risk_score      : [0,1] inverted, non-linear (detractors weighted higher)
    - verbatim_comment    : raw text (may be non-English — LLM handles translation)
    - has_non_english     : bool flag for LLM processing
    """
    import re

    def nps_to_risk(score: float) -> float:
        """0–6 = detractor (high risk), 7–8 = passive, 9–10 = promoter (low risk)."""
        if pd.isna(score):
            return 0.5  # unknown = medium
        if score <= 6:
            return 1.0 - (score / 12)   # 0→1.0, 6→0.5
        elif score <= 8:
            return 0.3 - (score - 7) * 0.1  # 7→0.3, 8→0.2
        else:
            return max(0.0, 0.1 - (score - 9) * 0.05)

    # Simple non-English detector: look for non-ASCII characters
    def is_non_english(text: str) -> bool:
        if not text:
            return False
        non_ascii = sum(1 for c in text if ord(c) > 127)
        return non_ascii / max(len(text), 1) > 0.1

    df = nps_df.copy()
    df["nps_risk_score"]   = df["score"].apply(nps_to_risk)
    df["has_non_english"]  = df["verbatim_comment"].apply(is_non_english)
    df = df.rename(columns={"score": "nps_score"})
    return df[["account_id", "nps_score", "nps_risk_score",
               "verbatim_comment", "has_non_english"]]


# ─────────────────────────────────────────────────────────────────────────────
# 4. SDK VERSION RISK (cross-referenced with changelog)
# ─────────────────────────────────────────────────────────────────────────────

def compute_sdk_risk(latest_sdk: str, changelog: dict) -> float:
    """
    Returns [0,1] SDK risk score based on changelog signals:
    - v3.x → 1.0 (sunset April 30, 2026 — final extension)
    - v4.0.0, v4.1.0 → 0.6 (affected by locale bug AND breaking change in v4.2)
    - v4.2.0, v4.2.3 → 0.2 (breaking change behind them, mostly fine)
    - v4.3.x → 0.0 (latest, all fixes applied)
    """
    if not latest_sdk:
        return 0.3

    v = latest_sdk.strip().lower()

    if v.startswith("v3"):
        return 1.0  # Sunset imminent, security patches ending
    if v in ("v4.0.0", "v4.1.0"):
        return 0.6  # Locale bug + missed breaking change fix
    if v in ("v4.2.0", "v4.2.3"):
        return 0.15
    if v.startswith("v4.3"):
        return 0.0
    return 0.2  # Unknown → slight risk


# ─────────────────────────────────────────────────────────────────────────────
# 5. RENEWAL URGENCY
# ─────────────────────────────────────────────────────────────────────────────

def compute_renewal_urgency(contract_end_date: date, reference_date: date) -> float:
    """
    [0,1] urgency: 0 = far away, 1 = expiring in <7 days.
    Accounts expiring in >90 days are filtered out before scoring,
    so this function is only applied to the 90-day window.
    """
    days_left = (contract_end_date - reference_date).days
    if days_left <= 0:
        return 1.0
    if days_left <= 30:
        return 0.9
    if days_left <= 60:
        return 0.6
    return 0.3  # 61–90 days


# ─────────────────────────────────────────────────────────────────────────────
# 6. MASTER FEATURE BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_features(data: dict) -> pd.DataFrame:
    """
    Given the loaded data dict, compute all features and return a merged DataFrame
    with one row per account (all accounts, not just renewing ones).
    """
    reference_date = data["reference_date"]
    accounts  = data["accounts"]
    usage     = data["usage"]
    tickets   = data["tickets"]
    nps       = data["nps"]
    changelog = data["changelog"]
    csm_notes = data["csm_notes"]

    # ── Compute each feature group ────────────────────────────────────────────
    usage_feat   = compute_usage_features(usage)
    ticket_feat  = compute_ticket_features(tickets, reference_date)
    nps_feat     = compute_nps_features(nps)

    # ── Merge onto accounts ────────────────────────────────────────────────────
    df = accounts.copy()
    df = df.merge(usage_feat,  on="account_id", how="left")
    df = df.merge(ticket_feat, on="account_id", how="left")
    df = df.merge(nps_feat,    on="account_id", how="left")

    # ── Fill NaN for accounts missing from some sources ───────────────────────
    df["usage_decline_score"]  = df["usage_decline_score"].fillna(0.3)
    df["support_health_score"] = df["support_health_score"].fillna(0.0)
    df["nps_risk_score"]       = df["nps_risk_score"].fillna(0.5)
    df["p1_open_count"]        = df["p1_open_count"].fillna(0)
    df["ticket_count_total"]   = df["ticket_count_total"].fillna(0)
    df["open_ticket_count"]    = df["open_ticket_count"].fillna(0)

    # ── SDK risk ───────────────────────────────────────────────────────────────
    df["sdk_risk_score"] = df["latest_sdk_version"].apply(
        lambda v: compute_sdk_risk(v, changelog)
    )

    # ── Renewal urgency ────────────────────────────────────────────────────────
    df["days_to_renewal"] = df["contract_end_date"].apply(
        lambda d: (d - reference_date).days
    )
    df["renewal_urgency_score"] = df.apply(
        lambda row: compute_renewal_urgency(row["contract_end_date"], reference_date),
        axis=1
    )

    # ── CSM notes per account (for LLM) ──────────────────────────────────────
    notes_by_acct: dict[int, list[str]] = {}
    for note in csm_notes:
        if note["account_id"] is not None:
            aid = note["account_id"]
            notes_by_acct.setdefault(aid, []).append(note["raw_text"])

    df["csm_notes_raw"] = df["account_id"].map(
        lambda aid: notes_by_acct.get(aid, [])
    )
    df["has_csm_notes"] = df["csm_notes_raw"].apply(lambda x: len(x) > 0)

    # ── NPS/Usage divergence flag (non-obvious signal) ─────────────────────────
    # High NPS (≥7) but declining usage = silent churn risk
    df["silent_churn_flag"] = (
        (df["nps_score"].fillna(0) >= 7) &
        (df["usage_decline_score"] >= 0.5)
    )

    return df


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    from src.data_loader import load_all

    data = load_all()
    feat = build_features(data)
    print(feat[["account_id", "account_name", "usage_decline_score",
                "support_health_score", "nps_risk_score", "sdk_risk_score",
                "days_to_renewal"]].head(20).to_string(index=False))
    print(f"\nTotal accounts with features: {len(feat)}")
    print(f"Silent churn flags: {feat['silent_churn_flag'].sum()}")
