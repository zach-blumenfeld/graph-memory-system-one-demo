#!/usr/bin/env python3
"""A LangGraph agent that assesses loan applications through AIP over MCP, and nothing else.

    uv run --project agents/langgraph python agents/langgraph/agent.py APP-1004 APP-1001

Run it from loan-aip-demo/: `aip mcp` starts in the current directory, which is where the
procedure's scripts look for `source/`. Each application is assessed in parallel over its own
`aip mcp` process; all share one session id, so the console's History shows the command as one
session of agent `langgraph`. The tools are `search`, `describe`, `run` and `resume`: the agent
can find and run procedures and answer their pauses, and cannot compile, publish or hand a task
to `aip agent`. The model is Claude (`DEMO_AGENT_MODEL`, default claude-sonnet-5-5) through
langchain-anthropic; the key is ANTHROPIC_API_KEY, else AIP_AGENT_MODEL_KEY.
"""

from __future__ import annotations

import asyncio
import json
import os
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
MODEL = os.environ.get("DEMO_AGENT_MODEL", "claude-sonnet-5-5")
SYSTEM = """You are a credit analyst's assistant at Lantern Mutual. You assess business-loan
applications with the procedures in the AIP catalog, reached through four tools: `search` finds
a procedure by what it does, `describe` says what it needs, `run` starts it with its inputs, and
`resume` answers a pause. You never assess an application yourself and never do a procedure's
steps by hand: the scripts, the decisions and the routing are the procedure's.

For each application: search the catalog for a business-loan assessment procedure, run it with
the application id as its input, and while the run is paused do what the task's prompt asks
(read its state, write what it asks for) and call `resume` with exactly the keys in
`answer_with`. When the run is done, report its result in two or three sentences: the outcome,
the rules that fired, and the run id. If a run fails, report the error as it is."""


def connections(session: str) -> dict:
    """One `aip mcp` process per connection, with this shell's environment passed on, named
    `langgraph` in the record and grouped under `session`."""
    aip = shutil.which("aip") or "aip"
    return {"aip": {"transport": "stdio", "command": aip, "args": ["mcp", "--agent", AGENT, "--session", session], "env": dict(os.environ)}}


def brief(value) -> str:
    text = json.dumps(value, default=str) if not isinstance(value, str) else value
    return text if len(text) < 160 else text[:157] + "..."


async def assess(application_id: str, session: str) -> str:
    client = MultiServerMCPClient(connections(session))
    async with client.session("aip") as mcp_session:
        tools = [t for t in await load_mcp_tools(mcp_session) if t.name in TOOLS]
        model = ChatAnthropic(model=MODEL, max_tokens=8192)
        graph = create_react_agent(model, tools, prompt=SYSTEM)
        final = ""
        async for chunk in graph.astream({"messages": [("user", f"Assess loan application {application_id}.")]}, stream_mode="updates", config={"recursion_limit": 60}):
            for node, update in chunk.items():
                for message in update.get("messages", []):
                    if isinstance(message, AIMessage):
                        for call in message.tool_calls:
                            args = {k: (v if len(json.dumps(v, default=str)) < 80 else "...") for k, v in call["args"].items()}
                            print(f"[{application_id}] -> {call['name']} {json.dumps(args)}", flush=True)
                        if not message.tool_calls and message.content:
                            final = message.content if isinstance(message.content, str) else "".join(b.get("text", "") for b in message.content if isinstance(b, dict))
                    elif isinstance(message, ToolMessage):
                        body = message.content
                        try:
                            parsed = json.loads(body) if isinstance(body, str) else body
                            summary = {k: parsed[k] for k in ("paused", "step", "done", "error", "run_id") if isinstance(parsed, dict) and k in parsed}
                        except Exception:
                            summary = {}
                        print(f"[{application_id}] <- {message.name} {json.dumps(summary) if summary else brief(body)}", flush=True)
        return final


async def main(applications: list[str]) -> int:
    if not os.environ.get("ANTHROPIC_API_KEY") and os.environ.get("AIP_AGENT_MODEL_KEY"):
        os.environ["ANTHROPIC_API_KEY"] = os.environ["AIP_AGENT_MODEL_KEY"]
    session = f"{AGENT}-{time.strftime('%H%M%S')}"
    print(f"agent {AGENT}  session {session}  model {MODEL}  tools {', '.join(TOOLS)}  applications {', '.join(applications)}", flush=True)
    results = await asyncio.gather(*(assess(a, session) for a in applications), return_exceptions=True)
    for application_id, result in zip(applications, results):
        print(f"\n== {application_id}\n{result if not isinstance(result, BaseException) else f'failed: {result!r}'}")
    print(f"\nhistory: aip runs --agent {AGENT} --session {session}")
    return 1 if any(isinstance(r, BaseException) for r in results) else 0


if __name__ == "__main__":
    apps = sys.argv[1:] or ["APP-1004", "APP-1001"]
    raise SystemExit(asyncio.run(main(apps)))
