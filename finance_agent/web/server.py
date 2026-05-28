"""
server.py — minimal Flask web UI for the finance agent.

Run:  python -m web.server     (from the finance_agent/ directory)
Then open http://localhost:5000

The browser posts a question to /api/ask; the server runs one agent turn
and returns the final answer plus the list of tools the agent called.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory

from agent import config
from agent import core

app = Flask(__name__, static_folder=None)
WEB_DIR = Path(__file__).resolve().parent

# Use nest_asyncio to allow nested event loops in Flask
import nest_asyncio
nest_asyncio.apply()


@app.route("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.route("/api/meta")
def meta():
    return jsonify({"mode": config.DATA_MODE, "model": config.MODEL})


@app.route("/api/ask", methods=["POST"])
def api_ask():
    question = (request.json or {}).get("question", "").strip()
    if not question:
        return jsonify({"error": "empty question"}), 400

    tools_used: list[str] = []
    final_text: list[str] = []

    async def run():
        async for kind, payload in core.ask_streaming(question):
            if kind == "tool":
                tools_used.append(payload)
            elif kind == "reasoning":
                final_text.append(payload)

    asyncio.run(run())
    return jsonify({
        "answer": "\n".join(final_text).strip() or "(no response)",
        "tools_used": tools_used,
        "mode": config.DATA_MODE,
    })


if __name__ == "__main__":
    print(f"Finance agent web UI — data mode: {config.DATA_MODE}")
    app.run(host="127.0.0.1", port=5000, debug=False)
