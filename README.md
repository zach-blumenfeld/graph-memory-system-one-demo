# Agent procedures, graph memory and System One: worked examples

Four examples built around the [Agent Instruction Protocol (AIP)](https://github.com/zach-blumenfeld/aip).
AIP turns a multi-step job (a runbook, an SOP) into a procedure: a graph of typed steps. Scripts
do the mechanical steps, a decision model answers the judgment questions with a probability, and
the agent is asked only for the steps that need an agent.

If you are new here, start with the benchmark. It needs the least setup to read, and its results
are already in the folder.

| Folder | What it shows | AIP version | How the procedure is written |
|---|---|---|---|
| [`loan-bench-aip-demo/`](loan-bench-aip-demo/README.md) | A benchmark comparing an agent with and without AIP on 30 loan applications | 0.9 | Procedure language (a `procedure.aip` file) |
| [`aip-demo/`](aip-demo/README.md) | A walkthrough of graph memory, distilling recorded agent runs into an AIP skill, and running it with a decision model, on an email campaign job | 0.5a0 | YAML, inside a `SKILL.md` (format 0.5a1) |
| [`loan-demo/`](loan-demo/README.md) | A walkthrough of graph memory, distilling recorded agent runs into an AIP skill, and running it with a decision model, on a business-loan assessment | 0.5a0 | YAML, inside a `SKILL.md` (format 0.5a1) |
| [`nams-demo/`](nams-demo/README.md) | Unfinished: an email campaign job with a hosted memory service doing the distillation | None | No AIP procedure |

## The two ways a procedure is written

AIP changed how a procedure is written between these examples, and the two do not mix.

- **YAML (AIP before 0.9).** The procedure is a YAML block inside a `SKILL.md` file. `aip-demo`
  and `loan-demo` use this. They install `aip` 0.5a0 and do not run on 0.9.
- **Procedure language (AIP 0.9).** The procedure is its own file, `procedure.aip`, in a small
  language with keywords such as `Execute`, `Decide`, `Route` and `For`, which a compiler checks.
  `loan-bench-aip-demo` uses this.

## The examples

### [`loan-bench-aip-demo/`](loan-bench-aip-demo/README.md): the benchmark (AIP 0.9, procedure language)

A comparison of an agent with and without AIP on one task. The task is a small-business term
loan assessment at a made-up bank: one written application in, one of four outcomes out (return,
decline, approve, escalate to a credit officer). The **baseline** agent is handed the bank's SOP
and policy and told to follow them. The **AIP** agent runs a procedure written from that SOP and
policy. Both agents are Claude Code, each run in its own container with no network beyond the
model APIs, and both are scored by one script against one set of expected answers.

It measures whether the answer was right, the tokens and cost, and the time, across 30
applications in three tiers of difficulty. `analysis.html` is the results as figures; open it in
a browser without running anything.

To run it you need Docker, an Anthropic API key, a TypeSafe key for the decision model, and a
local checkout of AIP 0.9 (the `release-0.9.0` branch, at `~/dev/aip-0.9` or wherever
`AIP_CHECKOUT` points).

### [`aip-demo/`](aip-demo/README.md): the email campaign walkthrough (AIP 0.5a0, YAML)

A follow-along walkthrough of three ideas, on a product-marketing agent that sends a launch
email:

1. **Graph memory.** A Notion workspace is loaded into a graph with the open-source
   `neo4j-agent-memory` SDK.
2. **Distillation.** Claude Code does the job from a Notion SOP, its runs are recorded, and the
   recordings are compiled into an AIP skill, `launch-email-blast`.
3. **System One.** The `aip` server runs the skill, and TypeSafe's decision model, Jev, answers
   its decisions.

### [`loan-demo/`](loan-demo/README.md): the business-loan walkthrough (AIP 0.5a0, YAML)

A follow-along walkthrough of graph memory, distillation and System One, on a business-loan
assessment, where the explanation matters as much as the answer:

1. **Graph memory.** Five bank systems go into one graph, so the agent can find that an owner's
   other business is behind on a loan.
2. **Distillation.** Five recorded agent runs are compiled into an AIP skill,
   `assess-business-loan`.
3. **System One.** The `aip` server runs the skill with TypeSafe's decision model, Jev, and each
   decision is filed back into the graph with the rules applied and the records cited. Then one
   rule is added, and an application assessed under the old rules is assessed again under the
   new ones.

This is a different, larger loan task than the one in `loan-bench-aip-demo`. The two share the
made-up bank and nothing else.

### [`nams-demo/`](nams-demo/README.md): unfinished (no AIP)

A product-marketing agent sending a launch email, with the hosted Neo4j Agent Memory Service
(NAMS) doing the distillation and the tools served over MCP with Jev inside them. It is a work in progress and stops before
the AIP step.

## Notes

- Each folder has its own README, setup and keys. Nothing is shared between folders.
- The companies in the fixtures, Tessera Labs and Lantern Mutual, are invented.
