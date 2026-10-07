# Distilling agent knowledge into System One workflows with graph memory

Two versions of the same demo, a product-marketing agent that learns an email-blast procedure.

- **[`aip-demo/`](aip-demo/README.md)**: Updated working example, written as a follow-along walkthrough. Notion workspace into graph memory with
  the open-source `neo4j-agent-memory` SDK; Claude Code does the job from a Notion SOP with a small
  `blast` command and no MCP; the recorded traces are compiled into an AIP skill; the aip server runs
  it with TypeSafe's Jev answering the decisions. Start with `aip-demo/README.md`.
- **[`nams-demo/`](nams-demo/README.md)**:  WIP: Hosted NAMS does
  the distillation, the tools are an MCP server with Jev inside them.

Each folder has its own `.env`, `Makefile` and docs. Everything about Tessera Labs, the company in
the fixture, is invented.
