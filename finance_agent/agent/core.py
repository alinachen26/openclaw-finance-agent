"""
core.py — wires the finance skills into the Claude Agent SDK as custom tools
and exposes a single `ask()` coroutine the CLI and web UI both call.

The SDK handles the agentic loop; we just (a) define the tools, (b) register
them via an in-process MCP server, and (c) pass the persona + tool allow-list.
"""
from __future__ import annotations

from typing import Any

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    create_sdk_mcp_server,
    tool,
    AssistantMessage,
    ResultMessage,
)

from agent import config
from skills.sec_filings import fetch_filing as _fetch_filing
from skills.metrics import extract_metrics as _extract_metrics


# ---------------------------------------------------------------------------
# Tool definitions (the @tool decorator registers name, description, schema)
# ---------------------------------------------------------------------------
@tool(
    "fetch_filing",
    "Fetch a public company's most recent SEC filing (10-K or 10-Q) and return "
    "its metadata plus extracted text sections (business, risk factors, MD&A).",
    {"ticker": str, "form_type": str},
)
async def fetch_filing(args: dict[str, Any]) -> dict[str, Any]:
    result = _fetch_filing(args["ticker"], args.get("form_type", "10-K"))
    return {"content": [{"type": "text", "text": _as_text(result)}]}


@tool(
    "extract_metrics",
    "Extract standardized financial figures for a company and compute ratios "
    "(revenue growth, net margin, leverage, current ratio) across the two most "
    "recent reporting periods.",
    {"ticker": str},
)
async def extract_metrics(args: dict[str, Any]) -> dict[str, Any]:
    result = _extract_metrics(args["ticker"])
    return {"content": [{"type": "text", "text": _as_text(result)}]}


def _as_text(obj: Any) -> str:
    import json

    return json.dumps(obj, indent=2, default=str)


# ---------------------------------------------------------------------------
# In-process MCP server bundling both tools
# ---------------------------------------------------------------------------
finance_server = create_sdk_mcp_server(
    name="finance-skills",
    version="0.1.0",
    tools=[fetch_filing, extract_metrics],
)

# Tool names are namespaced by the SDK as mcp__<server>__<tool>.
ALLOWED_TOOLS = [
    "mcp__finance-skills__fetch_filing",
    "mcp__finance-skills__extract_metrics",
]


def _options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=config.MODEL,
        system_prompt=config.SYSTEM_PROMPT,
        mcp_servers={"finance-skills": finance_server},
        allowed_tools=ALLOWED_TOOLS,
        permission_mode="acceptEdits",  # auto-approve our read-only finance tools
        max_turns=8,
    )


async def ask(prompt: str) -> str:
    """Run one turn of the agent and return the final text answer.

    Streams internally; concatenates assistant text blocks for a clean reply.
    """
    chunks: list[str] = []
    async for message in query(prompt=prompt, options=_options()):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text") and block.text:
                    chunks.append(block.text)
        elif isinstance(message, ResultMessage):
            break
    return "\n".join(chunks).strip() or "(no response)"


async def ask_streaming(prompt: str):
    """Async generator yielding ('reasoning'|'tool'|'final', text) events.

    Used by the web UI to show tool calls as they happen.
    """
    async for message in query(prompt=prompt, options=_options()):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text") and block.text:
                    yield ("reasoning", block.text)
                elif hasattr(block, "name"):
                    yield ("tool", block.name)
        elif isinstance(message, ResultMessage):
            yield ("final", getattr(message, "subtype", "done"))
            break
