"""`loan`: the agent's tools (JSON out) plus the demo's own commands (import, record, export)."""

from __future__ import annotations

import json
from typing import Optional

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True,
                  help="Lantern Mutual business-loan demo: the credit analyst's tools and the pipeline commands.")


def _quiet() -> None:
    """Silence the SDK's info logs and the driver's schema-warning notifications on stderr."""
    import logging

    for name in ("neo4j", "neo4j.notifications", "neo4j_agent_memory"):
        logging.getLogger(name).setLevel(logging.ERROR)


_quiet()


def out(obj) -> None:
    typer.echo(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _tools():
    from loan import tools

    return tools


# ------------------------------------------------------------------ the agent's tools
@app.command()
def sop() -> None:
    """The credit team's page 'How we assess a business loan' (from memory)."""
    out(_tools().sop())


@app.command()
def application(application_id: str) -> None:
    """An application: amount, term, purpose, the business, its owners (name and share only)."""
    out(_tools().application(application_id))


@app.command()
def ownership(business_id: str) -> None:
    """Who owns a business, and every other business each owner holds 25%+ of, with those businesses' facilities and payment status (two hops in the graph)."""
    out(_tools().ownership(business_id))


@app.command()
def facilities(business_id: str) -> None:
    """A business's facilities and their payments, with days late per facility."""
    out(_tools().facilities(business_id))


@app.command()
def cashflow(business_id: str) -> None:
    """12- and 24-month average monthly inflow, outflow and net for a business, citing the Month nodes."""
    out(_tools().cashflow(business_id))


@app.command()
def kyc(business_id: str) -> None:
    """KYC record and any fraud events for a business."""
    out(_tools().kyc(business_id))


@app.command()
def policy(application_id: str) -> None:
    """Apply the lending policy (R1-R6, G1) to an application: outcome, fired rules, figures, cites."""
    out(_tools().policy(application_id))


@app.command()
def precedents(application_id: str) -> None:
    """Past Decision nodes on similar applications (same product, same outcome band) and what was decided."""
    out(_tools().precedents(application_id))


rationale_app = typer.Typer(help="The written rationale: submit a file, get an id.")
app.add_typer(rationale_app, name="rationale")


@rationale_app.command("submit")
def rationale_submit(file: str = typer.Option(..., "--file", help="markdown file with the rationale"),
                     application: str = typer.Option(..., "--application"),
                     outcome: str = typer.Option(..., "--outcome", help="approve | counter | decline | review")) -> None:
    """Store a rationale under .run/rationales/ and return its id."""
    from pathlib import Path

    out(_tools().submit_rationale(application, outcome, Path(file).read_text()))


@app.command()
def check(rationale_id: str) -> None:
    """Lint a rationale: every cite marker (cite: KEY) names a node in the graph, every figure matches `loan policy`, the outcome matches, no protected characteristics."""
    out(_tools().check(rationale_id))


@app.command()
def record(rationale_id: Optional[str] = typer.Argument(None),
           outcome: Optional[str] = typer.Option(None, "--outcome", help="approve | counter | decline | review"),
           confidence: Optional[float] = typer.Option(None, "--confidence", help="0..1"),
           revision: Optional[str] = typer.Option(None, "--revision", help="skill revision, or 'freeform' for a run without the skill"),
           all_: bool = typer.Option(False, "--all", help="pipeline: record every run in prompts/runs.yaml"),
           model: Optional[str] = typer.Option(None, "--model", help="pipeline: model for the headless runs")) -> None:
    """Record a checked rationale as a Decision node in memory (ABOUT, APPLIED_POLICY, CITES, PRECEDENT_FOR).

    Pipeline use: `loan record run-01` or `loan record --all` runs the headless agent sessions of step 4.
    """
    if all_ or (rationale_id and rationale_id.startswith("run-")):
        from loan.record import record_all, record_one

        if all_:
            record_all(model=model, log=typer.echo)
        else:
            record_one(rationale_id, model=model, log=typer.echo)
        return
    if not rationale_id:
        raise typer.Exit("give a rationale id (from `loan rationale submit`) or --all")
    if outcome is None or confidence is None or revision is None:
        raise SystemExit(json.dumps({"error": "loan record needs --outcome, --confidence and --revision"}))
    out(_tools().record(rationale_id, outcome, confidence, revision))


@app.command()
def decide(question: str = typer.Option(..., "--question"), options: str = typer.Option(..., "--options", help="comma-separated"),
           answer: str = typer.Option(..., "--answer"), why: str = typer.Option(..., "--why")) -> None:
    """Log a judgment call: the question, the options considered, the answer, and why."""
    out(_tools().decide(question, [o.strip() for o in options.split(",")], answer, why))


# ------------------------------------------------------------------ pipeline
@app.command("import")
def import_cmd(rules_only: bool = typer.Option(False, "--rules-only", help="step 7: (re)import only the Rule nodes and SUBJECT_TO edges")) -> None:
    """Step 2: write the five bank systems into memory."""
    from loan.importer import import_rules, run_import, verify

    if rules_only:
        import_rules(log=typer.echo)
        return
    run_import(log=typer.echo)
    raise typer.Exit(verify(log=typer.echo))


@app.command()
def verify(what: str = typer.Argument("import")) -> None:
    """Check a stage: fixture | import | traces."""
    if what == "fixture":
        from loan.fixture import verify_fixture

        raise typer.Exit(verify_fixture(log=typer.echo))
    if what == "import":
        from loan.importer import verify as v

        raise typer.Exit(v(log=typer.echo))
    if what == "traces":
        from loan.record import verify_traces

        raise typer.Exit(verify_traces(log=typer.echo))
    raise typer.Exit(f"unknown stage {what}")


@app.command()
def reset(yes: bool = typer.Option(False, "--yes")) -> None:
    """Wipe the memory database (everything the demo wrote)."""
    if not yes:
        raise typer.Exit("add --yes to wipe the memory database")
    from loan.importer import reset as r

    r(log=typer.echo)


@app.command()
def doctor() -> None:
    """Memory database reachable, keys present, aip installed."""
    import os
    import shutil

    from loan.env import require
    from loan.memory import cypher

    require("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")
    n = cypher("MATCH (n) RETURN count(n) AS n")[0]["n"]
    typer.echo(f"[memory] connected; {n} nodes")
    typer.echo(f"[typesafe] key {'present' if os.environ.get('TYPESAFE_API_KEY') else 'MISSING'} (aip run needs it for decisions; the server reads its own config)")
    typer.echo(f"[aip] {'installed' if shutil.which('aip') else 'MISSING: aip CLI not on PATH'}")
    typer.echo(f"[claude] {'installed' if shutil.which('claude') else 'MISSING'}")
    typer.echo(f"[loan] {'on PATH' if shutil.which('loan') else 'not on PATH (run: uv tool install --editable .)'}")


traces_app = typer.Typer(help="Recorded traces: show, export.")
app.add_typer(traces_app, name="traces")


@traces_app.command("show")
def traces_show(run_id: str) -> None:
    from loan.record import show_trace

    show_trace(run_id, log=typer.echo)


@traces_app.command("export")
def traces_export() -> None:
    """Write source/sop.md, source/policy.md and source/traces.md from memory for the AIP authoring step."""
    from loan.record import export_source

    export_source(log=typer.echo)


if __name__ == "__main__":
    app()
