"""
config.py — central settings for the finance agent.

Controls the mock/live data toggle, model selection, and the agent's
system prompt (persona + boundaries). Everything that a reviewer might
want to change lives here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Data mode
# ---------------------------------------------------------------------------
# "mock"  -> skills read from bundled JSON fixtures in finance_agent/data/.
#            Lets the whole agent run with NO network access.
# "live"  -> skills hit the real SEC EDGAR / FRED APIs.
#
# Override from the shell:  export FINANCE_AGENT_MODE=live
DATA_MODE = os.getenv("FINANCE_AGENT_MODE", "mock").lower()

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
MODEL = os.getenv("FINANCE_AGENT_MODEL", "claude-opus-4-7")

# ---------------------------------------------------------------------------
# SEC EDGAR requires a descriptive User-Agent identifying the caller.
# Replace with your real name + email before running in live mode.
# (SEC fair-access policy: include contact info; keep under ~10 req/sec.)
# ---------------------------------------------------------------------------
SEC_USER_AGENT = os.getenv(
    "SEC_USER_AGENT",
    "AI Finance Internship Prototype - alina.chen@example.com",
)

# FRED API key — only needed in live mode for the stretch macro module.
FRED_API_KEY = os.getenv("FRED_API_KEY", "")

# ---------------------------------------------------------------------------
# Agent persona and boundaries (system prompt)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are a careful financial-analysis assistant built for a retail investor or \
small family office. Your job is to help the user understand a public company's \
recent SEC filings and key financial metrics.

How you work:
- Use the `fetch_filing` tool to retrieve a company's most recent 10-K or 10-Q \
and read the relevant sections (business overview, risk factors, management \
discussion).
- Use the `extract_metrics` tool to pull standardized financial figures and \
compute simple ratios (revenue growth, margins, leverage, liquidity).
- Always ground statements in the data you retrieved. Cite the filing form type \
and period (e.g. "per the FY2025 10-K").
- Explain findings in plain language a non-specialist can follow. Define jargon \
the first time you use it.
- When numbers are missing or ambiguous, say so. Never fill gaps with guesses.

Hard boundaries (do not cross):
- You provide research and summarization ONLY. You do NOT give buy/sell/hold \
recommendations, price targets, or any personalized investment advice.
- You do NOT execute trades or suggest specific allocations.
- You always note that filings are historical and that past results do not \
predict future performance.
- If asked for a recommendation, decline and instead lay out the relevant facts \
and the trade-offs so the user can decide for themselves.

Keep answers concise and structured. Lead with the direct answer, then the \
supporting detail.
"""
