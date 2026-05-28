"""
sec_filings.py — Skill 1: fetch and parse SEC filings.

Resolves a ticker to a CIK, finds the most recent 10-K/10-Q on EDGAR, and
returns the filing's metadata plus extracted text sections.

In mock mode it reads bundled fixtures so the agent runs with no network.
In live mode it calls the official, free SEC EDGAR APIs (no key required).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from agent import config

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ---------------------------------------------------------------------------
# Mock path
# ---------------------------------------------------------------------------
def _load_mock(ticker: str) -> dict[str, Any] | None:
    path = DATA_DIR / f"{ticker.upper()}_filing.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Live path (SEC EDGAR)
# ---------------------------------------------------------------------------
def _ticker_to_cik_live(ticker: str) -> str | None:
    import requests

    headers = {"User-Agent": config.SEC_USER_AGENT}
    url = "https://www.sec.gov/files/company_tickers.json"
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    for entry in resp.json().values():
        if entry["ticker"].upper() == ticker.upper():
            return str(entry["cik_str"]).zfill(10)
    return None


def _fetch_filing_live(ticker: str, form_type: str) -> dict[str, Any]:
    import requests

    headers = {"User-Agent": config.SEC_USER_AGENT}
    cik = _ticker_to_cik_live(ticker)
    if cik is None:
        return {"error": f"Could not resolve ticker '{ticker}' to a CIK on EDGAR."}

    subs = requests.get(
        f"https://data.sec.gov/submissions/CIK{cik}.json",
        headers=headers,
        timeout=30,
    ).json()

    recent = subs["filings"]["recent"]
    idx = None
    for i, form in enumerate(recent["form"]):
        if form == form_type:
            idx = i
            break
    if idx is None:
        return {"error": f"No {form_type} found for {ticker}."}

    accession = recent["accessionNumber"][idx].replace("-", "")
    primary_doc = recent["primaryDocument"][idx]
    filing_date = recent["filingDate"][idx]
    report_date = recent["reportDate"][idx]
    doc_url = (
        f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
        f"{accession}/{primary_doc}"
    )
    html = requests.get(doc_url, headers=headers, timeout=60).text
    sections = _extract_sections(html)

    return {
        "ticker": ticker.upper(),
        "company_name": subs.get("name", ticker.upper()),
        "cik": cik,
        "form_type": form_type,
        "filing_date": filing_date,
        "report_date": report_date,
        "source_url": doc_url,
        "sections": sections,
    }


def _extract_sections(html: str) -> dict[str, str]:
    """Very lightweight section extractor for 10-K/10-Q HTML.

    Strips tags, then slices out a few well-known Items by heading. This is
    intentionally simple — a Phase 2 prototype, not a production parser.
    """
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&#160;|&nbsp;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    anchors = {
        "business": r"Item\s+1\.?\s+Business",
        "risk_factors": r"Item\s+1A\.?\s+Risk Factors",
        "mdna": r"Item\s+7\.?\s+Management.s Discussion",
    }
    found: dict[str, str] = {}
    for name, pat in anchors.items():
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            start = m.start()
            found[name] = text[start : start + 4000]
    if not found:
        found["full_text_excerpt"] = text[:4000]
    return found


# ---------------------------------------------------------------------------
# Public entry point used by the agent tool wrapper
# ---------------------------------------------------------------------------
def fetch_filing(ticker: str, form_type: str = "10-K") -> dict[str, Any]:
    form_type = form_type.upper()
    if config.DATA_MODE == "mock":
        data = _load_mock(ticker)
        if data is None:
            return {
                "error": (
                    f"No mock fixture for '{ticker}'. Available mock tickers: "
                    + ", ".join(p.stem.replace("_filing", "") for p in DATA_DIR.glob("*_filing.json"))
                )
            }
        # Honor requested form type if the fixture has it; else return what we have.
        if data.get("form_type", "").upper() != form_type:
            data = {**data, "note": f"Mock fixture is a {data.get('form_type')}, not {form_type}."}
        return data
    return _fetch_filing_live(ticker, form_type)
