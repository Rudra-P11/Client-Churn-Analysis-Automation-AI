"""
app.py
======
Streamlit Renewal Intelligence Dashboard - Redesigned Light Theme.

Run: streamlit run app.py
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

# ─────────────────────────────────────────────────────────────────────────────
# SVG Icons (Lucide-inspired)
# ─────────────────────────────────────────────────────────────────────────────

SVG_TARGET = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>"""
SVG_USER = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>"""
SVG_MAP_PIN = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>"""
SVG_AWARD = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/></svg>"""
SVG_BRIEFCASE = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><rect width="20" height="14" x="2" y="6" rx="2"/></svg>"""
SVG_SHIELD = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.5 3.8 17 5 19 5a1 1 0 0 1 1 1z"/></svg>"""
SVG_CALENDAR = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 2v4"/><path d="M16 2v4"/><rect width="18" height="18" x="3" y="4" rx="2"/><path d="M3 10h18"/></svg>"""
SVG_STAR = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>"""
SVG_CODE = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>"""
SVG_LIGHTBULB = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A5 5 0 0 0 8 8c0 1 .3 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>"""
SVG_TICKET = """<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 2px;"><path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2Z"/><path d="M13 5v2"/><path d="M13 17v2"/><path d="M13 11v2"/></svg>"""
SVG_ALERT_TRIANGLE = """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>"""
SVG_ALERT_TRIANGLE_TINY = """<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 2px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>"""
SVG_CHECK_CIRCLE = """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>"""
SVG_MESSAGE_SQUARE = """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>"""
SVG_BAR_CHART_2 = """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>"""
SVG_FILE_TEXT = """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle;"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>"""
SVG_GLOBE = """<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 2px;"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>"""
SVG_VOLUME_X = """<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 2px;"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="22" y1="9" x2="16" y2="15"/><line x1="16" y1="9" x2="22" y2="15"/></svg>"""
SVG_CLOCK = """<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align: middle; margin-right: 2px;"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>"""

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Renewal Intelligence Engine",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Custom CSS — premium light design (Tailwind CSS style)
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* --- Global Reset & Canvas --- */
html, body, [class*="css"], [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif !important;
    background-color: #f8fafc !important;
    color: #1e293b !important;
}

/* Sidebar Override */
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #475569 !important;
    font-size: 0.9rem;
}
[data-testid="stSidebar"] .section-header {
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: #64748b !important;
    margin: 1.5rem 0 0.5rem 0 !important;
    border-bottom: 1px solid #e2e8f0 !important;
    padding-bottom: 0.25rem !important;
}

/* Tabs Styling */
button[data-baseweb="tab"] {
    color: #64748b !important;
    font-weight: 500 !important;
    font-size: 0.95rem !important;
    padding: 0.75rem 1rem !important;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #4f46e5 !important;
    border-bottom-color: #4f46e5 !important;
    font-weight: 600 !important;
}

/* Metric Cards */
.metric-card {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 16px !important;
    padding: 1.25rem 1.5rem !important;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.metric-card:hover {
    border-color: #cbd5e1 !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
    transform: translateY(-2px) !important;
}
.metric-value {
    font-size: 2.25rem !important;
    font-weight: 700 !important;
    line-height: 1.1 !important;
    margin-bottom: 0.25rem !important;
}
.metric-label {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    color: #64748b !important;
}
.metric-sub {
    font-size: 0.825rem !important;
    color: #94a3b8 !important;
    margin-top: 0.25rem !important;
}

/* Expander (Account Cards) Styling */
div[data-testid="stExpander"] {
    background-color: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
    margin-bottom: 0.75rem !important;
    overflow: hidden !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stExpander"]:hover {
    border-color: #6366f1 !important;
    box-shadow: 0 4px 8px -1px rgba(99, 102, 241, 0.08), 0 2px 4px -1px rgba(99, 102, 241, 0.04) !important;
}
div[data-testid="stExpander"] details summary {
    background-color: #ffffff !important;
    color: #0f172a !important;
    padding: 0.85rem 1.25rem !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
}
div[data-testid="stExpander"] details[open] summary {
    border-bottom: 1px solid #f1f5f9 !important;
}
div[data-testid="stExpander"] [data-testid="stMarkdownContainer"] p {
    color: #334155 !important;
}

/* Badges */
.badge-high {
    background-color: #fee2e2 !important;
    color: #991b1b !important;
    border: 1px solid #fca5a5 !important;
    padding: 3px 10px !important;
    border-radius: 9999px !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.025em !important;
    text-transform: uppercase !important;
    display: inline-block !important;
}
.badge-medium {
    background-color: #fef3c7 !important;
    color: #92400e !important;
    border: 1px solid #fcd34d !important;
    padding: 3px 10px !important;
    border-radius: 9999px !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.025em !important;
    text-transform: uppercase !important;
    display: inline-block !important;
}
.badge-low {
    background-color: #d1fae5 !important;
    color: #065f46 !important;
    border: 1px solid #6ee7b7 !important;
    padding: 3px 10px !important;
    border-radius: 9999px !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.025em !important;
    text-transform: uppercase !important;
    display: inline-block !important;
}
.badge-silent {
    background-color: #f3e8ff !important;
    color: #6b21a8 !important;
    border: 1px solid #e9d5ff !important;
    padding: 2px 8px !important;
    border-radius: 9999px !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    display: inline-block !important;
    margin-right: 6px !important;
}
.badge-urgent {
    background-color: #ffedd5 !important;
    color: #c2410c !important;
    border: 1px solid #fdba74 !important;
    padding: 2px 8px !important;
    border-radius: 9999px !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    display: inline-block !important;
    margin-right: 6px !important;
}
.badge-tech {
    background-color: #e0f2fe !important;
    color: #0369a1 !important;
    border: 1px solid #7dd3fc !important;
    padding: 2px 8px !important;
    border-radius: 9999px !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    display: inline-block !important;
    margin-right: 6px !important;
}
.badge-ticket {
    background-color: #fee2e2 !important;
    color: #b91c1c !important;
    border: 1px solid #fca5a5 !important;
    padding: 2px 8px !important;
    border-radius: 9999px !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    display: inline-block !important;
    margin-right: 6px !important;
}

/* Callout Box (Narrative Summary) */
.narrative-box {
    background-color: #f8fafc !important;
    border-left: 4px solid #4f46e5 !important;
    border-top: 1px solid #e2e8f0 !important;
    border-bottom: 1px solid #e2e8f0 !important;
    border-right: 1px solid #e2e8f0 !important;
    border-radius: 4px 12px 12px 4px !important;
    padding: 1.25rem !important;
    margin: 0.8rem 0 !important;
    font-size: 0.925rem !important;
    line-height: 1.6 !important;
    color: #334155 !important;
}

/* Portfolio Highlight Box */
.portfolio-summary-box {
    background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%) !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 16px !important;
    padding: 1.5rem !important;
    margin-bottom: 1.5rem !important;
    color: #1e293b !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(79, 70, 229, 0.15); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: rgba(79, 70, 229, 0.3); }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

REPORT_PATH = Path(__file__).parent / "output" / "risk_report.json"


@st.cache_data(ttl=300)
def load_report() -> dict | None:
    if not REPORT_PATH.exists():
        return None
    with open(REPORT_PATH, encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def tier_badge(tier: str) -> str:
    cls = {"High": "badge-high", "Medium": "badge-medium", "Low": "badge-low"}.get(tier, "badge-low")
    return f'<span class="{cls}">{tier}</span>'


def progress_bar(val: float, label: str) -> str:
    pct = min(100, max(0, int(val * 100)))
    if val > 0.6:
        color = "#ef4444"
    elif val > 0.3:
        color = "#f59e0b"
    else:
        color = "#10b981"
    return f"""
    <div style="margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; font-size: 0.82rem; margin-bottom: 4px;">
            <span style="font-weight: 500; color: #475569;">{label}</span>
            <span style="font-weight: 600; color: #1e293b;">{pct}%</span>
        </div>
        <div style="background-color: #f1f5f9; border-radius: 9999px; height: 8px; width: 100%; overflow: hidden; border: 1px solid #e2e8f0;">
            <div style="background-color: {color}; width: {pct}%; height: 100%; border-radius: 9999px;"></div>
        </div>
    </div>
    """


def kpi_block(label: str, val: str, icon_svg: str = "", is_warning: bool = False) -> str:
    warn_style = "color: #ef4444; font-weight: 600;" if is_warning else "color: #1e293b; font-weight: 600;"
    icon_html = f'<div style="color: #64748b; margin-right: 8px; display: inline-flex; align-items: center;">{icon_svg}</div>' if icon_svg else ""
    return f"""
    <div style="padding: 0.4rem 0; display: flex; align-items: center;">
        {icon_html}
        <div>
            <div style="font-size: 0.72rem; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; font-weight: 600; margin-bottom: 2px;">{label}</div>
            <div style="font-size: 0.925rem; {warn_style}">{val}</div>
        </div>
    </div>
    """


def fmt_arr(arr: float) -> str:
    if arr >= 1_000_000:
        return f"${arr/1_000_000:.2f}M"
    if arr >= 1_000:
        return f"${arr/1_000:.0f}K"
    return f"${arr:.0f}"


def sdk_risk_label(sdk: str) -> str:
    if not sdk:
        return "Unknown"
    v = str(sdk).lower()
    if v.startswith("v3"):
        return f'<span style="color: #ef4444; display: inline-flex; align-items: center; gap: 4px;"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 2px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>{sdk} (SUNSET)</span>'
    if v in ("v4.0.0", "v4.1.0"):
        return f'<span style="color: #b45309; display: inline-flex; align-items: center; gap: 4px;"><span style="background-color: #f59e0b; width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 4px;"></span>{sdk} (upgrade needed)</span>'
    return f'<span style="color: #10b981; display: inline-flex; align-items: center; gap: 4px;"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 2px;"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>{sdk}</span>'


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding: 1.5rem 0 1rem 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 1rem;">
        <div style="color: #4f46e5; display: flex; justify-content: center; margin-bottom: 0.5rem;">
            <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-target"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
        </div>
        <div style="font-size:1.15rem; font-weight:700; color:#0f172a;">Renewal Intelligence</div>
        <div style="font-size:0.7rem; color:#6366f1; letter-spacing:0.08em; text-transform:uppercase; font-weight: 600; margin-top: 0.2rem;">
            Powered by Gemini
        </div>
    </div>
    """, unsafe_allow_html=True)

    report = load_report()
    if report:
        st.markdown('<div class="section-header">🔍 Filter Portfolio</div>', unsafe_allow_html=True)

        accounts_list = report.get("accounts", [])
        df_all = pd.DataFrame(accounts_list)

        tier_filter = st.multiselect(
            "Risk Tier",
            options=["High", "Medium", "Low"],
            default=["High", "Medium", "Low"],
        )

        all_csms = sorted(df_all["csm_name"].dropna().unique().tolist())
        csm_filter = st.multiselect("CSM Owner", options=all_csms, default=all_csms)

        all_regions = sorted(df_all["region"].dropna().unique().tolist())
        region_filter = st.multiselect("Region", options=all_regions, default=all_regions)

        all_industries = sorted(df_all["industry"].dropna().unique().tolist())
        industry_filter = st.multiselect("Industry", options=all_industries, default=all_industries)

        show_silent_churn = st.checkbox("Silent Churn Only", value=False)

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.72rem; color:#94a3b8; text-align:center; border-top: 1px solid #e2e8f0; padding-top: 1rem;">'
        'Contentstack BizOps · Take-Home</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Main content
# ─────────────────────────────────────────────────────────────────────────────

if report is None:
    st.markdown(f"""
    <div style="text-align:center; padding: 6rem 2rem;">
        <div style="color: #4f46e5; display: flex; justify-content: center; margin-bottom: 1rem;">
            <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-target"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
        </div>
        <h1 style="font-size:2rem; font-weight:700; color:#1e293b; margin-bottom:0.8rem;">
            Renewal Intelligence Engine
        </h1>
        <p style="font-size:1rem; color:#64748b; max-width:500px; margin:0 auto 2rem auto;">
            No pre-generated report found. Please run the pipeline script in your terminal to ingest data and run analysis:
        </p>
        <div style="background:#f1f5f9; border:1px solid #e2e8f0;
                    border-radius:12px; padding:1.2rem 1.5rem; display:inline-block; text-align:left;
                    font-family:monospace; font-size:0.85rem; color:#4f46e5;">
            python pipeline.py
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Filter data ───────────────────────────────────────────────────────────────

df_all = pd.DataFrame(report.get("accounts", []))
meta   = report.get("meta", {})

# Apply filters
df = df_all.copy()
if "tier_filter" in dir():
    df = df[df["risk_tier"].isin(tier_filter)]
    df = df[df["csm_name"].isin(csm_filter)]
    df = df[df["region"].isin(region_filter)]
    df = df[df["industry"].isin(industry_filter)]
    if show_silent_churn:
        df = df[df["silent_churn_flag"] == True]

df = df.sort_values("risk_score", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(f"""
<div style="margin-bottom: 2rem; display: flex; align-items: center; gap: 12px;">
    <div style="color: #4f46e5; display: flex; align-items: center;">
        <svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-target"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
    </div>
    <div>
        <h1 style="font-size:2.2rem; font-weight:800; color:#0f172a; margin: 0; letter-spacing: -0.025em; line-height: 1.2;">
            Renewal Risk Intelligence
        </h1>
        <p style="color:#64748b; font-size:0.95rem; font-weight: 400; margin: 0; margin-top: 2px;">
            Accounts renewing in the next 90 days · Core BizOps Renewal Operations Dashboard
        </p>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# KPI Row
# ─────────────────────────────────────────────────────────────────────────────

high_arr   = df_all[df_all["risk_tier"] == "High"]["arr"].sum()
medium_arr = df_all[df_all["risk_tier"] == "Medium"]["arr"].sum()
total_arr  = df_all["arr"].sum()

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color:#ef4444;">{meta.get('high_risk_count', 0)}</div>
        <div class="metric-label">High Risk</div>
        <div class="metric-sub">{fmt_arr(high_arr)} ARR</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color:#f59e0b;">{meta.get('medium_risk_count', 0)}</div>
        <div class="metric-label">Medium Risk</div>
        <div class="metric-sub">{fmt_arr(medium_arr)} ARR</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color:#10b981;">{meta.get('low_risk_count', 0)}</div>
        <div class="metric-label">Low Risk</div>
        <div class="metric-sub">Healthy Accounts</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color:#4f46e5;">{fmt_arr(total_arr)}</div>
        <div class="metric-label">Total Portfolio ARR</div>
        <div class="metric-sub">Renewing in 90 Days</div>
    </div>""", unsafe_allow_html=True)

with c5:
    silent_count = int(df_all["silent_churn_flag"].fillna(False).sum()) if "silent_churn_flag" in df_all.columns else 0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color:#7c3aed;">{silent_count}</div>
        <div class="metric-label">Silent Churn Risk</div>
        <div class="metric-sub">Cratering Usage, High NPS</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main tabs
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
tab1, tab2, tab3 = st.tabs(["Account Risk List", "Portfolio Analytics", "Portfolio Insights"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: Account Risk List
# ═══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown(
        f'<div style="font-size:0.875rem; color:#64748b; margin-bottom:1.25rem; font-weight: 500;">'
        f'Showing {len(df)} matching accounts · Sorted by descending risk score</div>',
        unsafe_allow_html=True,
    )

    if df.empty:
        st.info("No accounts match the current filters.")
    else:
        for _, row in df.iterrows():
            tier  = str(row.get("risk_tier", "Low"))
            score = float(row.get("risk_score", 0))
            arr   = float(row.get("arr", 0))
            days  = int(row.get("days_to_renewal", 0)) if pd.notna(row.get("days_to_renewal")) else "?"
            sdk   = str(row.get("latest_sdk_version", "?"))
            p1    = int(row.get("p1_open_count", 0)) if pd.notna(row.get("p1_open_count")) else 0
            silent = bool(row.get("silent_churn_flag", False))
            nps   = row.get("nps_score")
            nps_str = f"{int(nps)}/10" if pd.notna(nps) else "N/A"

            # Badges inside the header/card
            # Badges inside the header/card
            signal_pills = ""
            if p1 > 0:
                signal_pills += f'<span class="badge-ticket" style="display: inline-flex; align-items: center; gap: 4px;">{SVG_TICKET} {p1} open P1</span>'
            if silent:
                signal_pills += f'<span class="badge-silent" style="display: inline-flex; align-items: center; gap: 4px;">{SVG_VOLUME_X} Silent Churn</span>'
            if sdk.lower().startswith("v3"):
                signal_pills += f'<span class="badge-tech" style="display: inline-flex; align-items: center; gap: 4px;">{SVG_ALERT_TRIANGLE_TINY} Sunset SDK</span>'
            if days != "?" and int(days) <= 30:
                signal_pills += f'<span class="badge-urgent" style="display: inline-flex; align-items: center; gap: 4px;">{SVG_CLOCK} &lt;{days} days</span>'

            # Expander representation of the Account Card
            emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(tier, "🟢")
            with st.expander(
                f"{emoji}  **{row.get('account_name')}**  ·  {fmt_arr(arr)} ARR  ·  {days} Days Left  ·  Score: {score:.2f}",
                expanded=False,
            ):
                # 1. Structured KPI Block Grid
                col_a, col_b, col_c, col_d = st.columns(4)
                with col_a:
                    st.markdown(kpi_block("CSM Owner", row.get("csm_name", "—"), icon_svg=SVG_USER), unsafe_allow_html=True)
                    st.markdown(kpi_block("Region", row.get("region", "—"), icon_svg=SVG_MAP_PIN), unsafe_allow_html=True)
                with col_b:
                    st.markdown(kpi_block("Plan Tier", row.get("plan_tier", "—"), icon_svg=SVG_AWARD), unsafe_allow_html=True)
                    st.markdown(kpi_block("Industry", row.get("industry", "—"), icon_svg=SVG_BRIEFCASE), unsafe_allow_html=True)
                with col_c:
                    st.markdown(kpi_block("Risk Profile", f"{tier_badge(tier)} (Score: {score:.2f})", icon_svg=SVG_SHIELD), unsafe_allow_html=True)
                    st.markdown(kpi_block("Contract End Date", row.get("contract_end_date", "—"), icon_svg=SVG_CALENDAR), unsafe_allow_html=True)
                with col_d:
                    st.markdown(kpi_block("NPS Score", nps_str, icon_svg=SVG_STAR, is_warning=(pd.notna(nps) and nps < 7)), unsafe_allow_html=True)
                    st.markdown(kpi_block("SDK Version", sdk_risk_label(sdk), icon_svg=SVG_CODE, is_warning=sdk.lower().startswith("v3")), unsafe_allow_html=True)

                # Status signals sub-header
                if signal_pills:
                    st.markdown(f'<div style="margin: 0.5rem 0 1rem 0;">{signal_pills}</div>', unsafe_allow_html=True)

                st.markdown("---")

                # 2. Risk Narrative Summary (Gemini Generated)
                narrative = str(row.get("narrative_summary", ""))
                if not narrative or "narrative generation failed" in narrative.lower():
                    narrative = "No risk narrative generated. Review structural signals, CSM call notes, and support ticket history below for direct insights."
                
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; margin-top: 0.5rem; margin-bottom: 0.4rem; color: #0f172a; font-size: 0.95rem;">
                    <div style="color: #4f46e5; display: inline-flex; align-items: center;">{SVG_FILE_TEXT}</div>
                    <span>Account Narrative Analysis</span>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f'<div class="narrative-box" style="margin-top: 0.2rem !important;">{narrative}</div>', unsafe_allow_html=True)

                # Urgency note from AI
                urgency = str(row.get("narrative_urgency", ""))
                if urgency and "narrative generation failed" not in urgency.lower():
                    st.markdown(f"""
                    <div style="background-color: #ffedd5; border: 1px solid #fdba74; border-radius: 8px; padding: 0.75rem 1rem; margin: 0.75rem 0; font-size: 0.88rem; color: #c2410c; display: flex; gap: 8px; align-items: center;">
                        <div style="color: #ea580c; display: flex; align-items: center;">{SVG_ALERT_TRIANGLE}</div>
                        <span><strong>Urgency Indicator:</strong> {urgency}</span>
                    </div>
                    """, unsafe_allow_html=True)

                # 3. Two columns: Risk Drivers & Recommended Actions
                col_risk, col_action = st.columns(2)

                with col_risk:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; margin-top: 0.5rem; margin-bottom: 0.4rem; color: #0f172a; font-size: 0.95rem;">
                        <div style="color: #ef4444; display: inline-flex; align-items: center;">{SVG_ALERT_TRIANGLE}</div>
                        <span>Key Risk Drivers</span>
                    </div>
                    """, unsafe_allow_html=True)
                    drivers = row.get("narrative_risk_drivers") or row.get("risk_flags") or []
                    if isinstance(drivers, str):
                        try:
                            drivers = json.loads(drivers)
                        except Exception:
                            drivers = [drivers]
                    
                    if drivers:
                        drivers_html = ""
                        for d in drivers:
                            drivers_html += f"""
                            <div style="display: flex; gap: 8px; margin: 6px 0; font-size: 0.88rem; align-items: start;">
                                <span style="color: #ef4444; font-weight: bold; line-height: 1;">•</span>
                                <span style="color: #475569;">{d}</span>
                            </div>
                            """
                        st.markdown(drivers_html, unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='color: #94a3b8; font-style: italic; font-size: 0.88rem;'>No active risk drivers identified.</span>", unsafe_allow_html=True)

                with col_action:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; margin-top: 0.5rem; margin-bottom: 0.4rem; color: #0f172a; font-size: 0.95rem;">
                        <div style="color: #10b981; display: inline-flex; align-items: center;">{SVG_CHECK_CIRCLE}</div>
                        <span>Recommended Actions</span>
                    </div>
                    """, unsafe_allow_html=True)
                    actions = row.get("narrative_actions") or []
                    if isinstance(actions, str):
                        try:
                            actions = json.loads(actions)
                        except Exception:
                            actions = [actions]
                    
                    if actions:
                        for a in actions:
                            st.markdown(f"""
                            <div style="background-color: #ecfdf5; border: 1px solid #d1fae5; border-radius: 8px; padding: 0.6rem 0.9rem; margin: 6px 0; font-size: 0.88rem; color: #065f46; display: flex; gap: 8px; align-items: start;">
                                <span style="font-weight: bold; color: #10b981; line-height: 1.1;">✓</span>
                                <span>{a}</span>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        # Fallback to general CSM recommendation if present
                        csm_rec = row.get("csm_recommended_action")
                        if pd.notna(csm_rec) and str(csm_rec).strip():
                            st.markdown(f"""
                            <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 0.6rem 0.9rem; margin: 6px 0; font-size: 0.88rem; color: #166534; display: flex; gap: 8px; align-items: start;">
                                <span style="font-weight: bold; color: #22c55e; line-height: 1.1;">✓</span>
                                <span>{csm_rec}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown("<span style='color: #94a3b8; font-style: italic; font-size: 0.88rem;'>Review details manually to define next steps.</span>", unsafe_allow_html=True)

                # 4. NPS Verbatim comment card (Original / Translated)
                verbatim = row.get("verbatim_comment")
                nps_score = row.get("nps_score")
                if pd.notna(verbatim) and str(verbatim).strip():
                    st.markdown("---")
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; margin-top: 0.5rem; margin-bottom: 0.4rem; color: #0f172a; font-size: 0.95rem;">
                        <div style="color: #4f46e5; display: inline-flex; align-items: center;">{SVG_MESSAGE_SQUARE}</div>
                        <span>NPS Customer Verbatim Feedback</span>
                    </div>
                    """, unsafe_allow_html=True)
                    lang = str(row.get("detected_language", "en"))
                    translated = row.get("english_translation")
                    
                    if lang.lower() not in ("en", "english", "") and translated:
                        st.markdown(f"""
                        <div style="background-color: #fffbeb; border: 1px solid #fef3c7; border-radius: 12px; padding: 1rem; margin-top: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span style="font-size: 0.7rem; background-color: #f59e0b; color: white; padding: 2px 8px; border-radius: 9999px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; display: inline-flex; align-items: center; gap: 4px;">
                                    {SVG_GLOBE} Translated from {lang.upper()}
                                </span>
                                <span style="font-size: 0.8rem; color: #78350f; font-weight: 600;">NPS Score: {int(nps_score)}/10</span>
                            </div>
                            <div style="font-style: italic; color: #78350f; font-size: 0.9rem; margin-bottom: 8px;">"{translated}"</div>
                            <div style="font-size: 0.78rem; color: #b45309; border-top: 1px dashed #fcd34d; padding-top: 6px;">
                                <strong>Original:</strong> "{verbatim}"
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1rem; margin-top: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                <span style="font-size: 0.7rem; background-color: #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 9999px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">
                                    Customer Feedback
                                </span>
                                <span style="font-size: 0.8rem; color: #475569; font-weight: 600;">NPS Score: {int(nps_score)}/10</span>
                            </div>
                            <div style="font-style: italic; color: #334155; font-size: 0.9rem;">"{verbatim}"</div>
                        </div>
                        """, unsafe_allow_html=True)

                # 5. Signal Contributions (CSS progress bars)
                breakdown = row.get("signal_breakdown")
                if isinstance(breakdown, dict):
                    st.markdown("---")
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; margin-top: 0.5rem; margin-bottom: 0.4rem; color: #0f172a; font-size: 0.95rem;">
                        <div style="color: #4f46e5; display: inline-flex; align-items: center;">{SVG_BAR_CHART_2}</div>
                        <span>Risk Signal Breakdown</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    sig_labels = {
                        "usage_decline_score":   "Usage Decline Trend",
                        "support_health_score":  "Support Ticket Burden",
                        "nps_risk_score":        "NPS Score Risk",
                        "sdk_risk_score":        "Sunset SDK Version Risk",
                        "csm_sentiment_score":   "CSM Notes Sentiment",
                        "renewal_urgency_score": "Contract Renewal Urgency",
                    }
                    
                    col_sig_l, col_sig_r = st.columns(2)
                    signals = list(breakdown.keys())
                    
                    with col_sig_l:
                        for s in signals[:3]:
                            lbl = sig_labels.get(s, s)
                            val = float(breakdown[s]["contribution"])
                            st.markdown(progress_bar(val, lbl), unsafe_allow_html=True)
                            
                    with col_sig_r:
                        for s in signals[3:]:
                            lbl = sig_labels.get(s, s)
                            val = float(breakdown[s]["contribution"])
                            st.markdown(progress_bar(val, lbl), unsafe_allow_html=True)

        # CSV export
        st.markdown("---")
        export_cols = ["account_name", "arr", "contract_end_date", "risk_score", "risk_tier",
                       "plan_tier", "industry", "region", "csm_name", "nps_score",
                       "latest_sdk_version", "p1_open_count", "silent_churn_flag",
                       "days_to_renewal", "narrative_summary"]
        export_df = df[[c for c in export_cols if c in df.columns]]
        st.download_button(
            "⬇️ Export Filtered Accounts to CSV",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name=f"renewal_risk_report_{date.today()}.csv",
            mime="text/csv",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: Portfolio Analytics
# ═══════════════════════════════════════════════════════════════════════════════

with tab2:
    col_l, col_r = st.columns(2)

    with col_l:
        # Risk score distribution
        fig_hist = px.histogram(
            df_all, x="risk_score", nbins=20,
            color="risk_tier",
            color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"},
            title="Risk Score Distribution",
            labels={"risk_score": "Risk Score", "count": "Number of Accounts"},
        )
        fig_hist.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#334155", family="Inter", size=11),
            legend_title_text="Risk Tier",
            xaxis=dict(gridcolor="#f1f5f9"),
            yaxis=dict(gridcolor="#f1f5f9"),
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        # ARR at risk by CSM
        csm_risk = df_all[df_all["risk_tier"].isin(["High", "Medium"])].groupby("csm_name")["arr"].sum().reset_index()
        csm_risk = csm_risk.sort_values("arr", ascending=True)
        fig_csm = px.bar(
            csm_risk, x="arr", y="csm_name", orientation="h",
            title="ARR at Risk by CSM Owner (High + Medium)",
            color="arr",
            color_continuous_scale=["#fcd34d", "#f97316", "#ef4444"],
        )
        fig_csm.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#334155", family="Inter", size=11),
            showlegend=False,
            xaxis=dict(gridcolor="#f1f5f9", title="Total ARR at Risk ($)"),
            yaxis=dict(gridcolor="#f1f5f9", title="CSM Owner"),
            margin=dict(l=10, r=10, t=50, b=10),
        )
        fig_csm.update_traces(texttemplate="%{x:$,.0f}", textposition="outside")
        st.plotly_chart(fig_csm, use_container_width=True)

    with col_r:
        # Tier donut
        tier_counts = df_all["risk_tier"].value_counts().reset_index()
        tier_counts.columns = ["tier", "count"]
        fig_donut = px.pie(
            tier_counts, names="tier", values="count",
            title="Account Breakdown by Risk Tier",
            color="tier",
            color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"},
            hole=0.55,
        )
        fig_donut.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#334155", family="Inter", size=11),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=10, r=10, t=50, b=10),
        )
        st.plotly_chart(fig_donut, use_container_width=True)

        # SDK version risk breakdown
        if "latest_sdk_version" in df_all.columns:
            sdk_counts = df_all.groupby(["latest_sdk_version", "risk_tier"]).size().reset_index(name="count")
            fig_sdk = px.bar(
                sdk_counts, x="latest_sdk_version", y="count", color="risk_tier",
                title="SDK Version Adoption vs Risk Profile",
                color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"},
                barmode="stack",
                labels={"latest_sdk_version": "SDK Version", "count": "Account Count"},
            )
            fig_sdk.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#334155", family="Inter", size=11),
                legend_title_text="Risk Tier",
                xaxis=dict(gridcolor="#f1f5f9"),
                yaxis=dict(gridcolor="#f1f5f9"),
                margin=dict(l=10, r=10, t=50, b=10),
            )
            st.plotly_chart(fig_sdk, use_container_width=True)

    # ARR scatter: risk score vs ARR coloured by tier
    st.markdown("<br><h4>Risk Score vs. Account ARR Bubble View</h4>", unsafe_allow_html=True)
    df_scatter = df_all.copy()
    df_scatter["arr_m"] = df_scatter["arr"] / 1e6
    fig_scatter = px.scatter(
        df_scatter, x="risk_score", y="arr_m",
        color="risk_tier",
        size="arr_m",
        hover_name="account_name",
        hover_data=["plan_tier", "csm_name", "days_to_renewal"],
        color_discrete_map={"High": "#ef4444", "Medium": "#f59e0b", "Low": "#10b981"},
        labels={"risk_score": "Risk Score (0 to 1)", "arr_m": "ARR ($M)"},
    )
    fig_scatter.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#334155", family="Inter", size=11),
        height=420,
        xaxis=dict(gridcolor="#f1f5f9"),
        yaxis=dict(gridcolor="#f1f5f9"),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    fig_scatter.add_vline(x=0.65, line_dash="dash", line_color="rgba(239,68,68,0.5)")
    fig_scatter.add_vline(x=0.35, line_dash="dash", line_color="rgba(245,158,11,0.5)")
    st.plotly_chart(fig_scatter, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: Portfolio Insights
# ═══════════════════════════════════════════════════════════════════════════════

with tab3:
    insights_data = report.get("portfolio_insights", {})
    insights = insights_data.get("insights", []) if isinstance(insights_data, dict) else []

    if not insights:
        # User requested clean message when insights are not generated due to Gemini rate limits
        st.markdown(f"""
        <div style="background-color: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 12px; padding: 2rem; text-align: center; margin-bottom: 2rem;">
            <div style="color: #94a3b8; display: flex; justify-content: center; margin-bottom: 0.75rem;">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-lightbulb"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A5 5 0 0 0 8 8c0 1 .3 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>
            </div>
            <h3 style="margin: 0; font-size: 1.15rem; color: #475569; font-weight: 600;">Portfolio Insights Not Available</h3>
            <p style="color: #64748b; font-size: 0.9rem; max-width: 480px; margin: 0.5rem auto 0 auto; line-height: 1.5;">
                Cross-portfolio trend analysis is disabled or the Gemini API rate limit was reached. Complete data enrichment to enable AI-powered non-obvious pattern matching.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Executive summary
        exec_summary = insights_data.get("executive_summary", "")
        if exec_summary:
            st.markdown(f"""
            <div class="portfolio-summary-box">
                <div style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.08em;
                            color:#4f46e5; margin-bottom:0.6rem; display: flex; align-items: center; gap: 6px;">
                    {SVG_BAR_CHART_2} Executive Summary
                </div>
                <div style="font-size:0.95rem; line-height:1.6; color:#1e293b;">{exec_summary}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; margin-top: 1.5rem; margin-bottom: 0.4rem;">
            <div style="color: #f59e0b; display: inline-flex; align-items: center;">{SVG_LIGHTBULB}</div>
            <h3 style="margin: 0; font-size: 1.35rem; font-weight: 700; color: #0f172a;">{len(insights)} Cross-Portfolio Findings</h3>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(
            '<p style="color:#64748b; font-size:0.875rem; margin-bottom:1.5rem; margin-top:0;">'
            'Compound risk vectors and patterns identified by analyzing global data signals.</p>',
            unsafe_allow_html=True,
        )

        for i, insight in enumerate(insights):
            with st.expander(f"{insight.get('title', f'Insight {i+1}')}", expanded=(i == 0)):
                obs_col, why_col = st.columns(2)

                with obs_col:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; margin-bottom: 0.4rem; color: #0f172a; font-size: 0.925rem;">
                        <div style="color: #3b82f6; display: inline-flex; align-items: center;">{SVG_MAP_PIN}</div>
                        <span>Observation</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="narrative-box" style="border-left-color: #3b82f6; margin-top: 0.2rem !important;">{insight.get("observation", "")}</div>',
                        unsafe_allow_html=True,
                    )

                with why_col:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; margin-bottom: 0.4rem; color: #0f172a; font-size: 0.925rem;">
                        <div style="color: #f59e0b; display: inline-flex; align-items: center;">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-search"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                        </div>
                        <span>BizOps/Technical Impact</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="narrative-box" style="border-left-color: #f59e0b; margin-top: 0.2rem !important;">{insight.get("why_non_obvious", "")}</div>',
                        unsafe_allow_html=True,
                    )

                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; margin-top: 0.5rem; margin-bottom: 0.4rem; color: #0f172a; font-size: 0.925rem;">
                    <div style="color: #10b981; display: inline-flex; align-items: center;">{SVG_CHECK_CIRCLE}</div>
                    <span>Recommended Structural Action</span>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(
                    f'<div style="background-color: #ecfdf5; border: 1px solid #d1fae5; border-radius: 8px; padding: 0.75rem 1rem; color: #065f46; font-size: 0.9rem; display: flex; gap: 8px; align-items: start; margin-top: 0.2rem;">'
                    f'<span style="font-weight: bold; color: #10b981; line-height: 1.1;">✓</span>'
                    f'<span>{insight.get("action", "")}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                affected = insight.get("affected_accounts", [])
                if affected:
                    st.markdown(
                        f'<div style="font-size:0.78rem; color:#64748b; margin-top:0.75rem; font-weight: 500;">'
                        f'<strong>Impacted Accounts:</strong> {", ".join(affected)}</div>',
                        unsafe_allow_html=True,
                    )

    # Silent churn spotlight
    st.markdown("---")
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 10px; margin-top: 2rem; margin-bottom: 0.4rem;">
        <div style="color: #7c3aed; display: inline-flex; align-items: center;">
            <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trending-down"><polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/></svg>
        </div>
        <h3 style="margin: 0; font-size: 1.35rem; font-weight: 700; color: #0f172a;">Silent Churn Spotlight</h3>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#64748b; font-size:0.875rem; margin-bottom:1rem; margin-top:0;">'
        'Accounts with positive NPS (≥ 7) but substantial 6-month product usage declines — highly deceptive churn targets.</p>',
        unsafe_allow_html=True,
    )

    if "silent_churn_flag" in df_all.columns:
        sc_df = df_all[df_all["silent_churn_flag"] == True][
            ["account_name", "arr", "nps_score", "usage_decline_score",
             "risk_tier", "contract_end_date", "csm_name"]
        ].sort_values("usage_decline_score", ascending=False)

        if not sc_df.empty:
            # Format columns for display in the native Streamlit data grid
            display_df = pd.DataFrame()
            display_df["Account Name"] = sc_df["account_name"]
            display_df["ARR"] = sc_df["arr"].apply(fmt_arr)
            display_df["NPS Score"] = sc_df["nps_score"].apply(lambda x: f"{int(x)}/10" if pd.notna(x) else "N/A")
            display_df["Usage Decline"] = sc_df["usage_decline_score"].apply(lambda x: f"-{int(x*100)}%")
            display_df["Risk Level"] = sc_df["risk_tier"].apply(lambda x: {"High": "🔴 High", "Medium": "🟡 Medium", "Low": "🟢 Low"}.get(x, x))
            display_df["Contract Renewal"] = sc_df["contract_end_date"]
            display_df["CSM Owner"] = sc_df["csm_name"]
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.success("No active accounts meet the silent churn risk definition in current filters.")
