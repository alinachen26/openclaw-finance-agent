"""
test_skills.py — offline smoke test for the two finance skills.

Verifies the skills load mock fixtures and compute metrics correctly WITHOUT
needing the Claude Agent SDK, an API key, or network access. Run this first to
confirm the data layer works, then run cli.py / web with your API key.

Run:  python test_skills.py    (from the finance_agent/ directory)
"""
import os

os.environ.setdefault("FINANCE_AGENT_MODE", "mock")

from skills.sec_filings import fetch_filing
from skills.metrics import extract_metrics


def approx(a, b, tol=1e-6):
    return a is not None and abs(a - b) < tol


def test_fetch_filing():
    f = fetch_filing("ACME", "10-K")
    assert "error" not in f, f
    assert f["ticker"] == "ACME"
    assert "risk_factors" in f["sections"]
    print("  ✓ fetch_filing(ACME) -> sections:", list(f["sections"]))


def test_unknown_ticker():
    f = fetch_filing("NOPE")
    assert "error" in f
    print("  ✓ unknown ticker returns a helpful error")


def test_metrics_math():
    m = extract_metrics("ACME")
    assert "error" not in m, m
    latest = m["periods"][-1]
    r = m["by_period"][latest]["ratios"]
    figs = m["by_period"][latest]["figures"]
    # net margin = 91,000,000 / 968,000,000 = 0.094...
    assert approx(r["net_margin"], round(91000000 / 968000000, 4)), r
    # current ratio = 625 / 340
    assert approx(r["current_ratio"], round(625000000 / 340000000, 4)), r
    # revenue growth = (968 - 820) / 820
    assert approx(m["revenue_growth_latest"], round((968000000 - 820000000) / 820000000, 4)), m
    print(f"  ✓ extract_metrics(ACME) net_margin={r['net_margin']} "
          f"current_ratio={r['current_ratio']} rev_growth={m['revenue_growth_latest']}")


def test_second_ticker():
    m = extract_metrics("GLOBEX")
    assert "error" not in m and len(m["periods"]) == 2
    print("  ✓ extract_metrics(GLOBEX) periods:", m["periods"])


if __name__ == "__main__":
    print("Running offline skill tests (mock mode)…")
    test_fetch_filing()
    test_unknown_ticker()
    test_metrics_math()
    test_second_ticker()
    print("\nAll skill tests passed. ✅")
