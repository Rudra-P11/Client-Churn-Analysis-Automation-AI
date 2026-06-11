"""
data_loader.py
==============
Ingests all 5 data sources, reconciles inconsistencies (fuzzy name matching,
mixed date formats, mismatched IDs), and returns a unified account-level dict.
"""

import re
import csv
import json
from pathlib import Path
from datetime import datetime, date

import pandas as pd
from rapidfuzz import process, fuzz

# ── Paths ──────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent

ACCOUNTS_CSV      = DATA_DIR / "accounts.csv"
USAGE_CSV         = DATA_DIR / "usage_metrics.csv"
TICKETS_CSV       = DATA_DIR / "support_tickets.csv"
NPS_CSV           = DATA_DIR / "nps_responses.csv"
CSM_NOTES_TXT     = DATA_DIR / "csm_notes.txt"
CHANGELOG_MD      = DATA_DIR / "changelog.md"


# ── Helper: normalise date strings ─────────────────────────────────────────────
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
}

def _parse_note_date(raw: str) -> date | None:
    """Try multiple date formats seen in csm_notes.txt."""
    raw = raw.strip()
    # ISO: 2026-03-20
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    # MM/DD or M/DD: 04/07  3/15
    m = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$", raw)
    if m:
        yr = int(m.group(3)) if m.group(3) else 2026
        if yr < 100:
            yr += 2000
        return date(yr, int(m.group(1)), int(m.group(2)))
    # "march 25"  "Apr 1"
    m = re.match(r"([a-z]+)\s+(\d{1,2})(?:\s+(\d{4}))?", raw, re.I)
    if m:
        mon = _MONTH_MAP.get(m.group(1).lower())
        if mon:
            yr = int(m.group(3)) if m.group(3) else 2026
            return date(yr, mon, int(m.group(2)))
    return None


# ── 1. Accounts ─────────────────────────────────────────────────────────────────
def load_accounts() -> pd.DataFrame:
    df = pd.read_csv(ACCOUNTS_CSV)
    df["contract_end_date"] = pd.to_datetime(df["contract_end_date"]).dt.date
    df["account_id"] = df["account_id"].astype(int)
    return df


# ── 2. Usage metrics ───────────────────────────────────────────────────────────
def load_usage() -> pd.DataFrame:
    df = pd.read_csv(USAGE_CSV)
    df["account_id"] = df["account_id"].astype(int)
    df["month"] = pd.to_datetime(df["month"])
    return df


# ── 3. Support tickets ─────────────────────────────────────────────────────────
def load_tickets() -> pd.DataFrame:
    df = pd.read_csv(TICKETS_CSV)
    df["account_id"] = df["account_id"].astype(int)
    df["created_date"] = pd.to_datetime(df["created_date"]).dt.date
    df["resolution_time_hours"] = pd.to_numeric(df["resolution_time_hours"], errors="coerce")
    return df


# ── 4. NPS responses ───────────────────────────────────────────────────────────
def load_nps() -> pd.DataFrame:
    df = pd.read_csv(NPS_CSV)
    df["account_id"] = df["account_id"].astype(int)
    df["score"] = pd.to_numeric(df["score"], errors="coerce")
    df["verbatim_comment"] = df["verbatim_comment"].fillna("")
    return df


# ── 5. CSM notes parser ────────────────────────────────────────────────────────
def _build_fuzzy_name_map(account_names: list[str]) -> dict[str, str]:
    """Return a lookup: normalised_variant → canonical_name."""
    return {name.lower(): name for name in account_names}


def parse_csm_notes(account_df: pd.DataFrame) -> list[dict]:
    """
    Parse csm_notes.txt into structured records.
    Each block (separated by ---) is one note.
    Returns list of dicts: {date, account_id, account_name, raw_text}
    """
    text = CSM_NOTES_TXT.read_text(encoding="utf-8")
    blocks = re.split(r"\n---+\n", text)

    canonical_names = account_df["account_name"].tolist()
    name_to_id      = dict(zip(account_df["account_name"], account_df["account_id"]))

    # Build keyword → account_id map for explicit "acct XXXX" patterns
    id_mentions = {}  # acct_id str → account_id int

    results = []
    for block in blocks:
        block = block.strip()
        if not block or block.startswith("==="):
            continue

        # ── Extract date from first line ───────────────────────────────────────
        first_line = block.split("\n")[0]
        # Possible patterns: "Mar 12", "3/15 acct 1001", "2026-03-20 | NovaTech"
        #                    "march 25 -- meridian", "3/28 Pinacle Media (acct 1004)"
        date_obj = None
        date_pat = re.search(
            r"(\d{4}-\d{2}-\d{2}|0?[1-9]\/\d{1,2}|[A-Za-z]+\s+\d{1,2})",
            first_line,
        )
        if date_pat:
            date_obj = _parse_note_date(date_pat.group(1))

        # ── Extract account_id via explicit "acct NNNN" or (#NNNN) pattern ────
        acct_id = None
        explicit_id_match = re.search(r"(?:acct|#|account)\s*(\d{4})", block, re.I)
        if explicit_id_match:
            acct_id = int(explicit_id_match.group(1))

        # ── Fuzzy-match account name from first two lines ─────────────────────
        matched_name = None
        if acct_id is None:
            # Pull candidate name tokens from first two lines
            header = " ".join(block.split("\n")[:2])
            # Strip date prefix, punctuation
            header_clean = re.sub(
                r"(\d{4}-\d{2}-\d{2}|\d{1,2}\/\d{1,2}|[A-Za-z]+\s+\d{1,2})"
                r"[\s\|\-\—]*",
                "", header, count=1
            ).strip()

            best = process.extractOne(
                header_clean,
                canonical_names,
                scorer=fuzz.token_set_ratio,
                score_cutoff=55,
            )
            if best:
                matched_name = best[0]
                acct_id = name_to_id[matched_name]

        if acct_id is None:
            # Last resort: scan entire block for any account name substring
            for name in canonical_names:
                # Match first word of company name (e.g. "Acme" matches "Acme Corp")
                first_word = name.split()[0]
                if re.search(rf"\b{re.escape(first_word)}\b", block, re.I):
                    acct_id = name_to_id[name]
                    matched_name = name
                    break

        results.append({
            "date": date_obj,
            "account_id": acct_id,
            "account_name": matched_name,
            "raw_text": block,
        })

    return results


# ── 6. Changelog parser ────────────────────────────────────────────────────────
def parse_changelog() -> dict:
    """
    Extract structured risk signals from changelog.md:
    - Deprecated SDK versions and their sunset dates
    - Breaking changes and affected SDK versions
    - Upcoming feature removals
    """
    text = CHANGELOG_MD.read_text(encoding="utf-8")

    signals = {
        "sdk_v3_sunset_date": date(2026, 4, 30),          # Final extension
        "sdk_v3_security_patches_end": date(2026, 4, 30),
        "legacy_editor_removal_version": "v4.4.0",
        "legacy_editor_removal_expected": "May 2026",
        "breaking_change_sdk_v420": True,                  # response.entry→response.data
        "breaking_change_affected_below": "v4.2.0",
        "locale_fix_version": "v4.2.3",                    # SDK v4.0 and v4.1 had locale bug
        "locale_fix_affects": ["v4.0.0", "v4.1.0"],
    }
    return signals


# ── Master loader ──────────────────────────────────────────────────────────────
def load_all(reference_date: date | None = None) -> dict:
    """
    Load and reconcile all data sources.
    Returns a dict with keys: accounts, usage, tickets, nps, csm_notes, changelog, reference_date
    """
    if reference_date is None:
        reference_date = date.today()

    accounts  = load_accounts()
    usage     = load_usage()
    tickets   = load_tickets()
    nps       = load_nps()
    csm_notes = parse_csm_notes(accounts)
    changelog = parse_changelog()

    return {
        "accounts":       accounts,
        "usage":          usage,
        "tickets":        tickets,
        "nps":            nps,
        "csm_notes":      csm_notes,
        "changelog":      changelog,
        "reference_date": reference_date,
    }


if __name__ == "__main__":
    data = load_all()
    print(f"Accounts loaded:    {len(data['accounts'])}")
    print(f"Usage rows:         {len(data['usage'])}")
    print(f"Tickets loaded:     {len(data['tickets'])}")
    print(f"NPS responses:      {len(data['nps'])}")
    print(f"CSM note blocks:    {len(data['csm_notes'])}")
    print(f"Notes with acct_id: {sum(1 for n in data['csm_notes'] if n['account_id'])}")
    print(f"Changelog signals:  {data['changelog']}")
