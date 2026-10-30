"""Run a prompt through the Claude Agent SDK, paid from Ali's promotional API credit.

    .venv-sdk/bin/python tools/run_on_credit.py "Do prompt 48."
    .venv-sdk/bin/python tools/run_on_credit.py --resume "Yes, go on."

Ali's Console credit (promotional, $100 granted 11 October 2026, expires 14 November 2026) pays for
the API and the Agent SDK but not for Claude Code, and Claude Code inside the Claude app always uses
his Max plan. This runs the same Claude (Opus at high effort, with this folder's CLAUDE.md, agents and
settings) through the Agent SDK with the Console key that `claude auth login --console` saved, so the
work is paid from the credit. It prints what Claude says and does, and the cost at the end.
--resume continues the last run with a new message (an answer to its question, a follow-up).

Needs its own environment, apart from the city code:
    .venv/bin/python -m venv .venv-sdk && .venv-sdk/bin/python -m pip install claude-agent-sdk
Run it outside the sandbox (it writes Claude's session files under ~/.claude).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, ResultMessage, SystemMessage,
                              TextBlock, ToolUseBlock, query)

ROOT = Path(__file__).resolve().parents[1]
LAST_SESSION = ROOT / ".venv-sdk" / "last_session"
# The Claude app gives every command it starts its own account (the Max plan); drop those settings
# so the Console login is used.
APP_PREFIXES = ("CLAUDE", "ANTHROPIC_")
TOOL_ARGS = ("command", "file_path", "path", "pattern", "description", "url")


def clean_env() -> None:
    for name in [n for n in os.environ if n.startswith(APP_PREFIXES)]:
        del os.environ[name]


def options(args: argparse.Namespace) -> ClaudeAgentOptions:
    resume = LAST_SESSION.read_text().strip() if args.resume and LAST_SESSION.exists() else None
    if args.resume and not resume:
        sys.exit("No earlier run to resume.")
    return ClaudeAgentOptions(
        model=args.model,
        effort=args.effort,
        cwd=str(ROOT),
        resume=resume,
        permission_mode="bypassPermissions",
        setting_sources=["user", "project", "local"],
        system_prompt={"type": "preset", "preset": "claude_code"},
        extra_args={"strict-mcp-config": None},
    )


def tool_line(block: ToolUseBlock) -> str:
    detail = next((str(block.input[k]) for k in TOOL_ARGS if k in block.input), "")
    return f"  > {block.name} {detail.splitlines()[0][:110] if detail else ''}"


def show(message, cost: list[float]) -> None:
    if isinstance(message, SystemMessage) and message.subtype == "init":
        print(f"[session {message.data.get('session_id')}, model {message.data.get('model')}]")
        LAST_SESSION.write_text(str(message.data.get("session_id")))
    elif isinstance(message, AssistantMessage):
        helper = "  helper: " if message.parent_tool_use_id else ""
        if message.error:
            print(f"{helper}[error: {message.error}]")
        for block in message.content:
            if isinstance(block, TextBlock) and block.text.strip():
                print(f"\n{helper}{block.text.strip()}\n")
            elif isinstance(block, ToolUseBlock):
                print(("  " if helper else "") + tool_line(block))
    elif isinstance(message, ResultMessage):
        cost.append(message.total_cost_usd or 0.0)
        state = "stopped with an error" if message.is_error else "done"
        print(f"\n[{state}: {message.num_turns} turns, {message.duration_ms / 60000:.1f} min, "
              f"about ${cost[-1]:.2f} of credit]")
        if message.is_error:
            print(message.result or "", *(message.errors or []), sep="\n")
    sys.stdout.flush()


async def run(args: argparse.Namespace) -> int:
    cost: list[float] = []
    async for message in query(prompt=args.prompt, options=options(args)):
        show(message, cost)
    return 0 if cost else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("prompt", help='what to ask, for example "Do prompt 48."')
    parser.add_argument("--resume", action="store_true", help="continue the last run")
    parser.add_argument("--model", default="opus")
    parser.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    args = parser.parse_args()
    clean_env()
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
