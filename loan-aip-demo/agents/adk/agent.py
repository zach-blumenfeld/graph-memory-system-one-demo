#!/usr/bin/env python3
"""A Google ADK agent that assesses loan applications through AIP over MCP, and nothing else.

    uv run --project agents/adk python agents/adk/agent.py APP-1002 APP-1005

Run it from loan-aip-demo/: `aip mcp` starts in the current directory, which is where the
procedure's scripts look for `source/`. Each application is assessed in parallel, over its own
`aip mcp` process; all of them share one session id, so the console's History shows the command
as one session of agent `adk`. The agent's tools are `search`, `describe`, `run` and `resume`:
it can find and run procedures and answer their pauses, and cannot compile, publish or hand a
task to `aip agent`. The model is Claude (`DEMO_AGENT_MODEL`, default claude-sonnet-5-5), through
ADK's Anthropic API model class (`AnthropicLlm`) given an `anthropic.AsyncAnthropic` client (ADK's `Claude` is
Claude on Vertex AI only and refuses that client); the key is ANTHROPIC_API_KEY, else AIP_AGENT_MODEL_KEY.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import sys
import time

from anthropic import AsyncAnthropic
from google.adk.agents import LlmAgent
from google.adk.models.anthropic_llm import AnthropicLlm
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters

AGENT = "adk"
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


def aip_mcp(session: str) -> McpToolset:
    """One `aip mcp` process, with this shell's environment passed on (AIP_SERVER and the rest),
    named `adk` in the record and grouped under `session`."""
    aip = shutil.which("aip") or "aip"
    params = StdioServerParameters(command=aip, args=["mcp", "--agent", AGENT, "--session", session], env=dict(os.environ))
    return McpToolset(connection_params=StdioConnectionParams(server_params=params, timeout=600.0), tool_filter=TOOLS)


async def assess(application_id: str, session: str) -> str:
    toolset = aip_mcp(session)
    agent = LlmAgent(name=f"loan_{application_id.replace('-', '_').lower()}", model=AnthropicLlm(model=MODEL, max_tokens=8192, client=AsyncAnthropic()), instruction=SYSTEM, tools=[toolset])
    runner = InMemoryRunner(agent=agent, app_name="loan-aip-demo")
    adk_session = await runner.session_service.create_session(app_name="loan-aip-demo", user_id="demo")
    message = types.Content(role="user", parts=[types.Part(text=f"Assess loan application {application_id}.")])
    final = ""
    try:
        async for event in runner.run_async(user_id="demo", session_id=adk_session.id, new_message=message):
            for call in event.get_function_calls() or []:
                args = {k: (v if len(json.dumps(v)) < 80 else "...") for k, v in (call.args or {}).items()}
                print(f"[{application_id}] -> {call.name} {json.dumps(args)}", flush=True)
            for response in event.get_function_responses() or []:
                body = response.response or {}
                if isinstance(body, dict):
                    body = body.get("result", body)
                summary = {k: body[k] for k in ("paused", "step", "done", "error", "run_id") if isinstance(body, dict) and k in body}
                print(f"[{application_id}] <- {response.name} {json.dumps(summary) if summary else ''}", flush=True)
            if event.is_final_response() and event.content and event.content.parts:
                final = "".join(p.text or "" for p in event.content.parts)
    finally:
        await toolset.close()
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
    apps = sys.argv[1:] or ["APP-1002", "APP-1005"]
    raise SystemExit(asyncio.run(main(apps)))
