"""
metrics.py — Skill 2: extract financial metrics and compute ratios.

Pulls standardized figures (revenue, net income, assets, liabilities, equity,
current assets/liabilities) and computes a small set of ratios that a generalist
can interpret: revenue growth, net margin, leverage, and current ratio.

Mock mode reads bundled fixtures. Live mode uses the SEC XBRL
company-concept / company-facts API (free, no key).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent import config

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Map our friendly names to US-GAAP XBRL tags used by the SEC facts API.
GAAP_TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"],
    "net_income": ["NetIncomeLoss"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "stockholders_equity": ["StockholdersEquity"],
    "current_assets": ["AssetsCurrent"],
    "current_liabilities": ["LiabilitiesCurrent"],
}


def _load_mock(ticker: str) -> dict[str, Any] | None:
    path = DATA_DIR / f"{ticker.upper()}_metrics.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _fetch_facts_live(ticker: str) -> dict[str, Any]:
    import requests

    from skills.sec_filings import _ticker_to_cik_live

    headers = {"User-Agent": config.SEC_USER_AGENT}
    cik = _ticker_to_cik_live(ticker)
    if cik is None:
        return {"error": f"Could not resolve ticker '{ticker}'."}

    facts = requests.get(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        headers=headers,
        timeout=60,
    ).json()
    usgaap = facts.get("facts", {}).get("us-gaap", {})

    def latest_two(tags: list[str]) -> list[dict[str, Any]]:
        for tag in tags:
            if tag in usgaap:
                units = usgaap[tag].get("units", {})
                series = units.get("USD") or next(iter(units.values()), [])
                annual = [x for x in series if x.get("form") == "10-K" and x.get("fp") == "FY"]
                annual.sort(key=lambda x: x.get("end", ""))
                if annual:
                    return annual[-2:]
        return []

    raw: dict[str, list[dict[str, Any]]] = {k: latest_two(v) for k, v in GAAP_TAGS.items()}
    periods = sorted({pt["end"] for vals in raw.values() for pt in vals})
    return {
        "ticker": ticker.upper(),
        "company_name": facts.get("entityName", ticker.upper()),
        "periods": periods,
        "raw": raw,
    }


def _value_for(raw: dict[str, Any], key: str, period: str) -> float | None:
    for pt in raw.get(key, []):
        if pt.get("end") == period:
            return float(pt["val"])
    return None


def _compute_ratios(figures: dict[str, float | None]) -> dict[str, Any]:
    def safe_div(a, b):
        if a is None or b in (None, 0):
            return None
        return round(a / b, 4)

    rev = figures.get("revenue")
    ni = figures.get("net_income")
    return {
        "net_margin": safe_div(ni, rev),
        "leverage_assets_to_equity": safe_div(
            figures.get("total_assets"), figures.get("stockholders_equity")
        ),
        "current_ratio": safe_div(
            figures.get("current_assets"), figures.get("current_liabilities")
        ),
        "debt_ratio": safe_div(
            figures.get("total_liabilities"), figures.get("total_assets")
        ),
    }


def extract_metrics(ticker: str) -> dict[str, Any]:
    """Return per-period figures + ratios + period-over-period revenue growth."""
    if config.DATA_MODE == "mock":
        data = _load_mock(ticker)
        if data is None:
            return {
                "error": (
                    f"No mock metrics for '{ticker}'. Available: "
                    + ", ".join(p.stem.replace("_metrics", "") for p in DATA_DIR.glob("*_metrics.json"))
                )
            }
    else:
        data = _fetch_facts_live(ticker)
        if "error" in data:
            return data

    periods = data["periods"]
    raw = data["raw"]
    by_period: dict[str, Any] = {}
    for p in periods:
        figs = {k: _value_for(raw, k, p) for k in GAAP_TAGS}
        by_period[p] = {"figures": figs, "ratios": _compute_ratios(figs)}

    # Revenue growth between the two most recent periods, if available.
    rev_growth = None
    if len(periods) >= 2:
        old = _value_for(raw, "revenue", periods[-2])
        new = _value_for(raw, "revenue", periods[-1])
        if old not in (None, 0) and new is not None:
            rev_growth = round((new - old) / old, 4)

    return {
        "ticker": data["ticker"],
        "company_name": data.get("company_name", data["ticker"]),
        "periods": periods,
        "by_period": by_period,
        "revenue_growth_latest": rev_growth,
    }
