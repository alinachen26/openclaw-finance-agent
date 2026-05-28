"""
cli.py — command-line chat with the finance agent.

Run:  python cli.py        (from the finance_agent/ directory)
Type 'exit' to quit.
"""
import asyncio

from agent import config
from agent import core


def main():
    print("=" * 60)
    print(f"  Filing Analyst — AI Finance Agent  [mode: {config.DATA_MODE}]")
    print("  Research/summarization only. Not investment advice.")
    print("  Type 'exit' to quit.")
    print("=" * 60)
    while True:
        try:
            q = input("\nyou › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if q.lower() in {"exit", "quit"}:
            break
        if not q:
            continue
        answer = asyncio.run(core.ask(q))
        print(f"\nagent › {answer}")


if __name__ == "__main__":
    main()
