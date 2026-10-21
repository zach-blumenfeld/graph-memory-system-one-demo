# Distilling agent knowledge into System One workflows with graph memory

Two versions of the same demo, a product-marketing agent that learns an email-blast procedure.

- **[`aip-demo/`](aip-demo/README.md)**: Updated working example, written as a follow-along walkthrough. Notion workspace into graph memory with
  the open-source `neo4j-agent-memory` SDK; Claude Code does the job from a Notion SOP with a small
  `blast` command and no MCP; the recorded traces are compiled into an AIP skill; the aip server walks
  it while the `aip` client runs the scripts and asks TypeSafe's Jev the decisions. Start with
  `aip-demo/README.md`.
- **[`loan-demo/`](loan-demo/README.md)**: The same three things on a business-loan assessment at a made-up
  bank: five systems in graph memory, the connected delinquency found through the ownership graph, five
  recorded runs distilled into `assess-business-loan`, decisions filed back into the graph with the
  rules applied and the records cited, one rule added and revision 2 run on the same application.
- **[`nams-demo/`](nams-demo/README.md)**:  WIP: Hosted NAMS does
  the distillation, the tools are an MCP server with Jev inside them.

Each folder has its own `.env`, `Makefile` and docs. Both worked examples are on AIP format 0.6a1
(`aip` 0.6a1, `aip-spec` 0.6a1, the `aip-console` web client); agent memory is a local Neo4j in
Docker, one per example. Everything about Tessera Labs and Lantern Mutual, the companies in the
fixtures, is invented.
