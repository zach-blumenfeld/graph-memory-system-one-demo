Read PLAN.md in full. Build the entire demo unattended, following the build order in §11 and the stage contracts in §5. Nobody is watching: never ask a question, never wait for input. If something is ambiguous, pick the option PLAN.md recommends, write the assumption into BUILD-LOG.md, and continue.

Unattended rules:
- Stage 4 must be scripted: implement `pmm distill`, `pmm skill review --approve`, `pmm skill publish`, `pmm skill download` over the NAMS REST routes in PLAN.md and run them. Do not stop for the human review gate; record the provenance summary in BUILD-LOG.md.
- Stage 3 is headless only (`claude -p` runs); skip the interactive live run.
- Secrets come from `.env`. The NAMS key is account-level; always send MEMORY_WORKSPACE_ID (the SDK does this via NamsSettings; raw REST calls need the X-Workspace-Id header). If a key is rejected, do everything that does not need it, write what is blocked to BUILD-LOG.md, and finish the rest. Never print secret values.
- Commit after each build-order item and push to origin main.
- Append progress, failures, retries, and verification output to BUILD-LOG.md. Finish with a "Status" section: what works, what is blocked, how to run the demo.
- Use `make selftest` and `pmm verify stage<N>` as gates before moving on. Fix failures; don't skip them.
