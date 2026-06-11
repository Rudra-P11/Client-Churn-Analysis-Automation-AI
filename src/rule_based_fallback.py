"""
rule_based_fallback.py
======================
Generates rich, structured narratives from quantitative signals only
when LLM quota is unavailable.  This is NOT a replacement for the LLM —
it exists to ensure the dashboard is always functional.

The output mirrors the LLM narrative schema exactly so the dashboard
renders identically.
"""

from datetime import date


SDK_RISK_LABELS = {
    1.0:  ("SDK v3.x (SUNSET)", "critical — security patches have ended as of April 30 2026"),
    0.6:  ("SDK v4.0/v4.1", "affected by the locale-fallback bug and missed the v4.2 breaking-change fix"),
    0.15: ("SDK v4.2.x",   "stable but missing Agent OS and latest performance improvements"),
    0.0:  ("SDK v4.3.x",   "fully up to date"),
}


def _sdk_label(score: float) -> tuple[str, str]:
    rounded = round(score, 2)
    for threshold, label in sorted(SDK_RISK_LABELS.items(), reverse=True):
        if rounded >= threshold - 0.01:
            return label
    return ("Unknown SDK", "unknown version")


def generate_rule_based_narrative(row: dict) -> dict:
    """
    Build a plain-English risk narrative from structured signals alone.
    Returns the same schema as generate_account_narrative().
    """
    name     = row.get("account_name", "This account")
    arr      = row.get("arr", 0)
    tier     = row.get("risk_tier", "Unknown")
    score    = row.get("risk_score", 0)
    days     = row.get("days_to_renewal", "?")
    nps      = row.get("nps_score")
    plan     = row.get("plan_tier", "")
    industry = row.get("industry", "")
    csm      = row.get("csm_name", "")

    usage_decline  = float(row.get("usage_decline_score", 0) or 0)
    support_score  = float(row.get("support_health_score", 0) or 0)
    p1_open        = int(row.get("p1_open_count", 0) or 0)
    open_tickets   = int(row.get("open_ticket_count", 0) or 0)
    sdk_score      = float(row.get("sdk_risk_score", 0) or 0)
    silent_churn   = bool(row.get("silent_churn_flag", False))
    csm_sentiment  = float(row.get("csm_sentiment_score", 0.5) or 0.5)
    nps_comment    = row.get("verbatim_comment") or row.get("english_translation") or ""
    sdk_name, sdk_desc = _sdk_label(sdk_score)

    risk_drivers = []
    actions      = []

    # ── Build risk drivers ──────────────────────────────────────────────────
    if usage_decline >= 0.7:
        risk_drivers.append(
            f"Severe usage decline over 6 months (decline risk score: {usage_decline:.0%}) — "
            f"API call volume has dropped significantly, indicating reduced reliance on the platform."
        )
    elif usage_decline >= 0.4:
        risk_drivers.append(
            f"Moderate usage decline (score: {usage_decline:.0%}) — "
            f"engagement is trending downward and has not recovered."
        )

    if silent_churn:
        risk_drivers.append(
            f"Silent churn pattern detected: NPS score is {int(nps)}/10 (seemingly healthy) "
            f"but product usage has declined sharply — a classic indicator of disengagement "
            f"that will not surface in survey data until it is too late."
        )

    if p1_open > 0:
        risk_drivers.append(
            f"{p1_open} open/escalated P1 ticket(s) — unresolved critical issues "
            f"are actively blocking the customer's workflows and eroding trust."
        )
    elif open_tickets > 0:
        risk_drivers.append(
            f"{open_tickets} open/escalated tickets with no resolution — "
            f"slow support response is a common trigger for non-renewal decisions."
        )

    if sdk_score >= 1.0:
        risk_drivers.append(
            f"CRITICAL SDK risk: customer is on {sdk_name}, which is {sdk_desc}. "
            f"They face a forced migration that may cause production disruptions — "
            f"this technical urgency often becomes a contractual one."
        )
    elif sdk_score >= 0.5:
        risk_drivers.append(
            f"SDK version risk: customer is on {sdk_name} ({sdk_desc}). "
            f"Upgrade is needed before they hit breaking changes."
        )

    if isinstance(nps, (int, float)) and nps <= 6:
        risk_drivers.append(
            f"NPS detractor (score {int(nps)}/10) — customers in this range actively "
            f"evaluate alternatives and are statistically unlikely to renew."
        )

    if csm_sentiment >= 0.7:
        risk_drivers.append(
            "CSM notes indicate negative or mixed sentiment — qualitative signals from "
            "recent calls suggest dissatisfaction beyond what the metrics capture."
        )

    if days != "?" and int(days) <= 30:
        risk_drivers.append(
            f"Contract expires in {days} days — insufficient time for standard renewal "
            f"process without immediate escalation."
        )

    if not risk_drivers:
        risk_drivers.append(
            f"Composite risk score of {score:.2f} reflects multiple small signals: "
            f"usage trends, support volume, and NPS — none individually severe, "
            f"but combined they suggest a renewal conversation is needed."
        )

    # ── Build recommended actions ───────────────────────────────────────────
    if days != "?" and int(days) <= 30:
        actions.append(f"URGENT: Escalate to CRO/VP CS immediately — {days} days to renewal leaves no margin.")

    if p1_open > 0:
        actions.append(
            f"Resolve {p1_open} open P1 ticket(s) before any renewal conversation — "
            f"no customer renews while production is broken."
        )

    if sdk_score >= 1.0:
        actions.append(
            f"Arrange a dedicated SA/engineering session to unblock the migration from "
            f"{sdk_name} to v4.3.x — offer as a goodwill gesture tied to renewal."
        )

    if silent_churn:
        actions.append(
            "Book an executive QBR within 2 weeks — the NPS hides real disengagement. "
            "Probe for active evaluation of alternatives and identify the champion."
        )

    if usage_decline >= 0.5 and not silent_churn:
        actions.append(
            "Conduct a usage audit with the customer's technical team — "
            "identify which workflows are abandoned and offer re-onboarding support."
        )

    if not actions:
        actions.append(
            f"Schedule a renewal conversation with {csm} and {name}'s decision-maker "
            f"within the next 2 weeks to align on value and contract terms."
        )

    # ── Build summary ───────────────────────────────────────────────────────
    summary_parts = []

    lead_signal = risk_drivers[0] if risk_drivers else f"risk score of {score:.2f}"
    summary_parts.append(
        f"{name} is flagged as {tier} renewal risk (score {score:.2f}) with "
        f"${arr:,.0f} ARR renewing in {days} days."
    )

    if silent_churn:
        summary_parts.append(
            f"The most concerning signal is a silent churn pattern — NPS {int(nps)}/10 "
            f"masks a {usage_decline:.0%} usage decline risk score, suggesting the team "
            f"still likes the support relationship but has reduced platform dependence."
        )
    elif usage_decline >= 0.5:
        summary_parts.append(
            f"Usage has declined significantly (decline risk: {usage_decline:.0%}), "
            f"and {'combined with ' + str(p1_open) + ' open P1 tickets' if p1_open else 'compounded by support friction'}, "
            f"the renewal is not guaranteed."
        )
    elif p1_open > 0:
        summary_parts.append(
            f"With {p1_open} open P1 ticket(s) unresolved, the customer is actively "
            f"experiencing production pain that must be addressed before renewal talks."
        )
    else:
        summary_parts.append(
            f"Signals are moderate but the {days}-day renewal window leaves little "
            f"time for recovery if the account team doesn't act now."
        )

    summary = " ".join(summary_parts)

    urgency_note = (
        f"Contract expires {row.get('contract_end_date')} — "
        f"{'immediate escalation required' if (days != '?' and int(days) <= 30) else 'proactive outreach needed now to avoid last-minute scramble'}."
    )

    return {
        "summary":              summary,
        "risk_drivers":         risk_drivers,
        "recommended_actions":  actions,
        "urgency_note":         urgency_note,
        "source":               "rule_based",  # Flag so dashboard can show provenance
    }


def generate_rule_based_csm_signals(csm_notes: list[str]) -> dict:
    """
    Extract basic risk signals from CSM notes using keyword matching.
    Used as fallback when LLM quota is exhausted.
    """
    if not csm_notes:
        return {
            "csm_sentiment_score": 0.5,
            "risk_flags": [],
            "positive_signals": [],
            "key_stakeholder_concern": None,
            "recommended_action": None,
        }

    combined = " ".join(csm_notes).lower()

    # Competitor mentions
    competitors = ["hygraph", "contentful", "kontent.ai", "sanity", "strapi",
                   "builder.io", "wordpress", "drupal"]
    found_competitors = [c for c in competitors if c in combined]

    risk_flags = []
    positive_signals = []
    sentiment_hits = 0
    sentiment_total = 0

    # Negative signals
    negative_keywords = {
        "evaluating alternatives": "Actively evaluating competitor CMS",
        "competitor": f"Competitor mention ({', '.join(found_competitors) or 'unnamed'})",
        "no show": "No-show on CSM calls — disengagement signal",
        "churn": "Churn explicitly mentioned",
        "cancel": "Cancellation language used",
        "angry": "Customer expressed anger",
        "furious": "Billing/product dispute causing customer fury",
        "escalate": "Escalation requested",
        "walk": "Threatened to walk",
        "discount": "Discount demanded — pricing sensitivity",
        "budget cut": "Budget reduction communicated",
        "downgrade": "Downgrade risk mentioned",
        "poc": "Proof of concept with competitor underway",
        "lost faith": "Champion lost faith in product/roadmap",
        "acquiring": "M&A activity — vendor contracts under review",
    }
    for kw, flag in negative_keywords.items():
        if kw in combined:
            risk_flags.append(flag)
            sentiment_hits -= 1
        sentiment_total += 1

    # Positive signals
    positive_keywords = {
        "expand": "Expansion plans discussed",
        "upgrade": "Upgrade interest expressed",
        "budget approved": "Budget for renewal approved",
        "champagne": "Strong renewal / expansion confirmed",
        "locked in": "Renewal locked in",
        "2-year": "Multi-year extension discussed",
        "love": "Strong product satisfaction expressed",
        "great qbr": "Positive QBR outcome",
        "adding seats": "Seat expansion in progress",
    }
    for kw, signal in positive_keywords.items():
        if kw in combined:
            positive_signals.append(signal)
            sentiment_hits += 1
        sentiment_total += 1

    # Sentiment score: 0=very negative, 1=very positive
    base = 0.5
    if sentiment_total > 0:
        adjustment = sentiment_hits / max(sentiment_total, 5)  # Dampen
        base = min(1.0, max(0.0, 0.5 + adjustment))

    # Executive involvement = always a risk signal
    exec_keywords = ["vp ", "cto", "cro", "ciso", "coo", "cfo", "executive", "president"]
    key_concern = None
    for kw in exec_keywords:
        if kw in combined:
            key_concern = f"Executive-level stakeholder involved ('{kw.strip()}' mentioned) — elevates urgency"
            break

    # Recommended action
    action = None
    if found_competitors:
        action = f"Schedule executive call immediately — competitor evaluation ({', '.join(found_competitors)}) is active"
    elif risk_flags:
        action = f"Escalate to CRO/VP CS — {risk_flags[0].lower()}"
    elif positive_signals:
        action = "Confirm renewal paperwork and document expansion opportunity"

    return {
        "csm_sentiment_score": round(1.0 - base, 4),  # Invert: high sentiment = low risk score
        "risk_flags": risk_flags[:5],
        "positive_signals": positive_signals[:3],
        "key_stakeholder_concern": key_concern,
        "recommended_action": action,
    }


def generate_rule_based_portfolio_insights(renewing_df) -> dict:
    """
    Generate portfolio insights from structured data without LLM.
    """
    import pandas as pd

    df = renewing_df.copy()

    insights = []

    # Insight 1: SDK v3.x + renewal = double jeopardy
    sdk3_renewing = df[df["latest_sdk_version"].str.startswith("v3", na=False)]
    if not sdk3_renewing.empty:
        names = sdk3_renewing["account_name"].tolist()
        total_arr = sdk3_renewing["arr"].sum()
        insights.append({
            "title": "SDK v3.x Sunset + Renewal = Double Jeopardy",
            "observation": (
                f"{len(sdk3_renewing)} account(s) renewing in the next 90 days "
                f"(${total_arr:,.0f} total ARR) are still on SDK v3.x, which had its "
                f"security patches ended on April 30, 2026. These accounts face a mandatory "
                f"technical migration coinciding exactly with renewal negotiations."
            ),
            "why_non_obvious": (
                "A rule-based system would treat SDK version as a static risk signal "
                "independent of the renewal date. It would NOT detect that a forced migration "
                "coinciding with contract renewal gives the customer a natural 'exit moment' — "
                "the friction of migrating might tip them toward evaluating alternatives "
                "rather than upgrading in place."
            ),
            "action": (
                "Proactively offer a dedicated Solutions Architect migration sprint (2 weeks) "
                "at no cost, bundled into the renewal contract. Removes the friction and "
                "ties the customer to Contentstack during the highest-risk window."
            ),
            "affected_accounts": names,
        })

    # Insight 2: Silent churn cluster
    silent = df[df["silent_churn_flag"] == True] if "silent_churn_flag" in df.columns else pd.DataFrame()
    if not silent.empty:
        names = silent["account_name"].tolist()
        insights.append({
            "title": "Silent Churn Cluster — Good NPS Hiding Real Disengagement",
            "observation": (
                f"{len(silent)} account(s) ({', '.join(names)}) have NPS scores of 7+ "
                f"but show significant usage decline. This is the 'silent churn' pattern: "
                f"customers who still like your support team but have already reduced "
                f"their operational dependency on your platform."
            ),
            "why_non_obvious": (
                "A rule-based system using NPS as a health signal would classify these "
                "as 'healthy' and deprioritize outreach. The divergence between survey "
                "sentiment and actual usage data — only visible by cross-referencing "
                "both signals — reveals the real picture."
            ),
            "action": (
                "Do NOT rely on NPS alone for these accounts. Conduct immediate usage "
                "audit calls. Ask specifically: 'What workflows have you moved off-platform "
                "in the last 3 months and why?' The answer will reveal whether this is "
                "recoverable or the customer has already built an alternative."
            ),
            "affected_accounts": names,
        })

    # Insight 3: CSM workload concentration
    if "csm_name" in df.columns:
        csm_high = df[df["risk_tier"].isin(["High", "Medium"])].groupby("csm_name").size()
        if not csm_high.empty:
            top_csm = csm_high.idxmax()
            top_count = csm_high.max()
            top_arr = df[(df["csm_name"] == top_csm) & (df["risk_tier"].isin(["High", "Medium"]))]["arr"].sum()
            insights.append({
                "title": f"CSM Workload Risk — {top_csm} Holds the Most At-Risk ARR",
                "observation": (
                    f"{top_csm} has {top_count} High/Medium risk accounts renewing in "
                    f"the next 90 days (${top_arr:,.0f} ARR). This is the highest "
                    f"concentration of renewal risk in a single CSM's book."
                ),
                "why_non_obvious": (
                    "Individual account risk scores look manageable in isolation. "
                    "But when one CSM is responsible for multiple high-risk renewals "
                    "simultaneously, the quality of attention each account receives "
                    "necessarily degrades — increasing the probability of losing at "
                    "least one that could have been saved."
                ),
                "action": (
                    f"Temporarily assign a CSM shadow or senior overlay to {top_csm}'s "
                    f"book for the next 90 days. Prioritize the two highest-ARR accounts "
                    f"for executive sponsorship from Contentstack leadership."
                ),
                "affected_accounts": df[(df["csm_name"] == top_csm) &
                                        (df["risk_tier"].isin(["High", "Medium"]))]["account_name"].tolist(),
            })

    # Insight 4: Enterprise accounts with low NPS
    ent_low_nps = df[
        (df["plan_tier"] == "Enterprise") &
        (df["nps_score"].fillna(10) <= 6)
    ] if "nps_score" in df.columns else pd.DataFrame()
    if not ent_low_nps.empty:
        names = ent_low_nps["account_name"].tolist()
        total_arr = ent_low_nps["arr"].sum()
        insights.append({
            "title": "Enterprise Detractors — Highest ARR, Lowest NPS",
            "observation": (
                f"{len(ent_low_nps)} Enterprise account(s) (${total_arr:,.0f} ARR) "
                f"have NPS scores of 6 or below, making them active detractors. "
                f"Detractors in Enterprise accounts are disproportionately dangerous "
                f"because they are often active in analyst communities and peer networks."
            ),
            "why_non_obvious": (
                "A simple churn model treats NPS as a probability modifier. It misses "
                "the qualitative impact: an Enterprise detractor who churns will often "
                "actively advocate against your product in Gartner/G2 reviews and "
                "peer conversations — creating pipeline damage beyond the lost ARR."
            ),
            "action": (
                "Escalate to CRO for executive-to-executive engagement. Offer a "
                "dedicated product roadmap session with the CPO. The goal is not just "
                "retention — it's converting a detractor into a passive or promoter "
                "before they exit and start talking."
            ),
            "affected_accounts": names,
        })

    # Executive summary
    high_arr = df[df["risk_tier"] == "High"]["arr"].sum()
    med_arr  = df[df["risk_tier"] == "Medium"]["arr"].sum()
    total    = df["arr"].sum()

    exec_summary = (
        f"Of {len(df)} accounts renewing in the next 90 days (${total:,.0f} total ARR), "
        f"{(df['risk_tier']=='High').sum()} are High risk (${high_arr:,.0f} ARR) and "
        f"{(df['risk_tier']=='Medium').sum()} are Medium risk (${med_arr:,.0f} ARR). "
        f"The most critical pattern is the convergence of SDK v3.x forced migrations "
        f"with renewal windows — these accounts have a natural exit moment that the "
        f"account team must neutralise with proactive technical support before the "
        f"renewal conversation begins."
    )

    return {"insights": insights, "executive_summary": exec_summary}
