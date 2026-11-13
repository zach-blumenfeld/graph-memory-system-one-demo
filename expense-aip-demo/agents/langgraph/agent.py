#!/usr/bin/env python3
"""A LangGraph agent that reviews expense claims through AIP over MCP, and nothing else.

    uv run --project agents/langgraph python agents/langgraph/agent.py C-1001 C-1006

Run it from expense-aip-demo/: `aip mcp` starts in the current directory, which is where the
procedure appends its ledger line. The agent reads each claim's files (`claims/<id>.json` and its
receipt text) and hands them to the procedure. Each claim runs in parallel over its own `aip mcp`
process; all share one session id, so the console's History shows the command as one session of
agent `langgraph`. The tools are `search`, `describe`, `run` and `resume`: the agent
can find and run procedures and answer their pauses, and cannot compile, publish or hand a task
to `aip agent`. The model is Claude (`DEMO_AGENT_MODEL`, default claude-sonnet-5-5) through
langchain-anthropic; the key is ANTHROPIC_API_KEY, else AIP_AGENT_MODEL_KEY.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
import time

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, ToolMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent

AGENT = "langgraph"
TOOLS = ["search", "describe", "run", "resume"]
def _load_dotenv() -> None:
    """Read KEY=VALUE lines from the demo's .env (this folder's parent's parent) into os.environ, without overriding."""
    env = Path(__file__).resolve().parents[2] / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if "=" in line and not line.startswith("export "):
            k, v = line.split("=", 1)
            v = os.path.expandvars(v.strip().strip('"').strip("'"))
            os.environ.setdefault(k.strip(), v)


_load_dotenv()

MODEL = os.environ.get("DEMO_AGENT_MODEL", "claude-sonnet-5-5")
SYSTEM = """You are a finance team's assistant. You review expense claims with the procedures
in the AIP catalog, reached through four tools: `search` finds a procedure by what it does,
`describe` says what it needs, `run` starts it with its inputs, and `resume` answers a pause. You
never review a claim yourself and never do a procedure's steps by hand: the checks, the decisions
and the routing are the procedure's.

For each claim: search the catalog for an expense claim review procedure, describe it, and run it
with the claim's fields and the receipt text exactly as given, mapped to the procedure's inputs.
While the run is paused, do what the task's prompt asks (read its state, write what it asks for)
and call `resume` with exactly the keys in `answer_with`. Where the task is the person's decision,
you are the reviewer: decide from what the procedure found, and give a one-line reason. When the
run is done, report its result in two sentences: the status, the reason, and the run id. If a run
fails, report the error as it is."""


def connections(session: str) -> dict:
    """One `aip mcp` process per connection, with this shell's environment passed on, named
    `langgraph` in the record and grouped under `session`."""
    aip = shutil.which("aip") or "aip"
    return {"aip": {"transport": "stdio", "command": aip, "args": ["mcp", "--agent", AGENT, "--session", session], "env": dict(os.environ)}}


def brief(value) -> str:
    text = json.dumps(value, default=str) if not isinstance(value, str) else value
    return text if len(text) < 160 else text[:157] + "..."


HERE = Path(__file__).resolve().parents[2]


def claim_message(claim_id: str) -> str:
    """The claim as the agent is handed it: the JSON fields and the receipt text, read from claims/."""
    claim = json.loads((HERE / "claims" / f"{claim_id}.json").read_text())
    receipt = (HERE / "claims" / claim.pop("receipt_file")).read_text()
    return (f"Review expense claim {claim_id}.\n\nThe claim:\n{json.dumps(claim, indent=1)}\n\n"
            f"The receipt text, verbatim:\n<<<\n{receipt}>>>")


async def review(claim_id: str, session: str) -> str:
    client = MultiServerMCPClient(connections(session))
    async with client.session("aip") as mcp_session:
        tools = [t for t in await load_mcp_tools(mcp_session) if t.name in TOOLS]
        model = ChatAnthropic(model=MODEL, max_tokens=8192)
        graph = create_react_agent(model, tools, prompt=SYSTEM)
        final = ""
        async for chunk in graph.astream({"messages": [("user", claim_message(claim_id))]}, stream_mode="updates", config={"recursion_limit": 60}):
            for node, update in chunk.items():
                for message in update.get("messages", []):
                    if isinstance(message, AIMessage):
                        for call in message.tool_calls:
                            args = {k: (v if len(json.dumps(v, default=str)) < 80 else "...") for k, v in call["args"].items()}
                            print(f"[{claim_id}] -> {call['name']} {json.dumps(args)}", flush=True)
                        if not message.tool_calls and message.content:
                            final = message.content if isinstance(message.content, str) else "".join(b.get("text", "") for b in message.content if isinstance(b, dict))
                    elif isinstance(message, ToolMessage):
                        body = message.content
                        if isinstance(body, list):   # MCP tools answer a list of content blocks
                            body = "".join(b.get("text", "") for b in body if isinstance(b, dict))
                        try:
                            parsed = json.loads(body) if isinstance(body, str) else body
                            summary = {k: parsed[k] for k in ("paused", "step", "done", "error", "run_id") if isinstance(parsed, dict) and k in parsed}
                        except Exception:
                            summary = {}
                        print(f"[{claim_id}] <- {message.name} {json.dumps(summary) if summary else brief(body)}", flush=True)
        return final


async def main(claims: list[str]) -> int:
    if not os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("AIP_AGENT_MODEL_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = os.environ["AIP_AGENT_MODEL_KEY"]
    session = f"{AGENT}-{time.strftime('%H%M%S')}"
    print(f"agent {AGENT}  session {session}  model {MODEL}  tools {', '.join(TOOLS)}  claims {', '.join(claims)}", flush=True)
    results = await asyncio.gather(*(review(a, session) for a in claims), return_exceptions=True)
    for claim_id, result in zip(claims, results):
        print(f"\n== {claim_id}\n{result if not isinstance(result, BaseException) else f'failed: {result!r}'}")
    print(f"\nhistory: aip runs --agent {AGENT} --session {session}")
    return 1 if any(isinstance(r, BaseException) for r in results) else 0


if __name__ == "__main__":
    apps = sys.argv[1:] or ["C-1001", "C-1006"]
    raise SystemExit(asyncio.run(main(apps)))
