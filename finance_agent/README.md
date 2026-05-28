# Filing Analyst — AI Finance Agent (Phase 2 Prototype)

An AI agent that reads a public company's SEC filings and financial metrics and
explains them in plain language. Built on the **Claude Agent SDK** with two
custom finance skills, a local **web UI**, and a **mock/live data toggle** so it
runs with or without network access.

> **Scope:** research and summarization only. The agent does **not** give
> investment advice, recommendations, or execute trades. This is an internship
> learning prototype, not a production financial product.

---

## What it does

| Skill | Tool name | What it does |
|-------|-----------|--------------|
| 1. Filing fetch & parse | `fetch_filing` | Resolves a ticker → CIK, pulls the latest 10-K/10-Q from SEC EDGAR, extracts the business, risk-factor, and MD&A sections. |
| 2. Metric extraction | `extract_metrics` | Pulls standardized XBRL figures and computes revenue growth, net margin, leverage (assets/equity), debt ratio, and current ratio across the two most recent periods. |

The agent (Claude) decides which skill to call based on the question, calls them
through the SDK's tool loop, and writes a grounded, cited answer.

---

## Project layout

```
finance_agent/
├── agent/
│   ├── config.py        # settings: data mode, model, system prompt (persona + boundaries)
│   └── core.py          # registers skills as SDK tools; runs the agentic loop
├── skills/
│   ├── sec_filings.py   # Skill 1 (mock + live)
│   └── metrics.py       # Skill 2 (mock + live)
├── data/                # mock fixtures (ACME, GLOBEX) — illustrative, not real
├── web/
│   ├── server.py        # Flask server
│   └── index.html       # chat UI
├── cli.py               # command-line chat
├── test_skills.py       # offline smoke test (no SDK / no network needed)
├── requirements.txt
└── .env.example
```

---

## Setup

Requires **Python 3.10+**.

```bash
cd finance_agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env
```

### Configuration (`.env`)

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Required for live agent runs. Get one at platform.claude.com. |
| `FINANCE_AGENT_MODE` | `mock` (default, offline) or `live` (hits real APIs). |
| `FINANCE_AGENT_MODEL` | Model id (default `claude-opus-4-7`). |
| `SEC_USER_AGENT` | **Your name + email.** SEC requires a descriptive User-Agent. |
| `FRED_API_KEY` | Only for the stretch macro module. Free key from the St. Louis Fed. |

> **Note on auth:** the Claude Agent SDK uses API-key (or cloud-provider) auth.
> It cannot be powered by a consumer claude.ai subscription, so live runs are
> metered against your API key — budget accordingly.

---

## Running

### 0. Verify the data layer (no API key needed)

```bash
python test_skills.py
```
Confirms both skills load the mock fixtures and the ratio math is correct.

### 1. Command-line chat

```bash
python cli.py
```

### 2. Web UI

```bash
python -m web.server
# open http://localhost:5000
```

The UI shows the current data mode, the tools the agent called for each answer,
and the plain-language response.

---

## Mock vs. live mode

- **Mock (default):** skills read JSON fixtures in `data/` for tickers `ACME`
  and `GLOBEX`. The figures are **illustrative and clearly labelled as mock** —
  they are not real company data. This lets you exercise the full agent loop
  with no network and no SEC/FRED calls.
- **Live:** set `FINANCE_AGENT_MODE=live`. Skills then call the official, free
  SEC EDGAR APIs (`company_tickers.json`, `submissions`, `companyfacts`). No SEC
  key is required, but you must set a real `SEC_USER_AGENT` and stay within the
  fair-access rate limit (~10 requests/second).

To add another mock ticker, drop `TICKER_filing.json` and `TICKER_metrics.json`
into `data/` following the shape of the existing files.

---

## Example prompts

- "Summarize ACME's latest 10-K and its three biggest risks."
- "What are GLOBEX's net margin and current ratio, and how did revenue change year over year?"
- "Compare ACME and GLOBEX on leverage and liquidity."

---

## How the agent is wired (for the write-up)

`core.py` defines each skill as an SDK `@tool`, bundles them into an in-process
MCP server via `create_sdk_mcp_server`, and passes them to `query()` through
`ClaudeAgentOptions` along with the persona/boundary system prompt from
`config.py`. The `allowed_tools` list restricts the agent to exactly the two
finance tools (read-only), and `permission_mode="acceptEdits"` auto-approves
those safe calls. The SDK runs the reason → call-tool → observe → answer loop;
the app just collects the streamed messages.

---

## Known limitations (carry into Phase 3 analysis)

- The HTML section extractor in Skill 1 is deliberately simple; complex filing
  layouts may need a more robust parser.
- Live mode depends on US-GAAP XBRL tags; companies using less common tags may
  return partial metrics.
- Mock data is illustrative only — never cite it as real.
- The agent summarizes; it does not verify the filing's own accuracy.

## Stretch (per the Phase 1 recommendation)

A FRED-based macro module (policy rate, reserves, reverse-repo, balance sheet)
is the next skill to add, followed by a clearly-caveated 18-month outlook that
combines company filings with macro context. `fredapi` is already listed in
`requirements.txt` and `FRED_API_KEY` is wired into `config.py`.
