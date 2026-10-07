"""`blast`: the agent's tools (JSON out) plus the demo's own commands (import, record, export)."""

from __future__ import annotations

import json
import sys
from typing import Optional

import typer

from blast import tools

app = typer.Typer(add_completion=False, no_args_is_help=True, help="Email-blast demo: the agent's tools and the pipeline commands.")


def _quiet() -> None:
    """Silence the SDK's info logs and the driver's schema-warning notifications on stderr."""
    import logging

    for name in ("neo4j", "neo4j.notifications", "neo4j_agent_memory"):
        logging.getLogger(name).setLevel(logging.ERROR)


_quiet()


def out(obj) -> None:
    typer.echo(json.dumps(obj, indent=2, ensure_ascii=False))


# ------------------------------------------------------------------ the agent's tools
@app.command()
def sop() -> None:
    """The team's 'How we run an email blast' page (from memory)."""
    out(tools.sop())


@app.command()
def brief(brief_id: str) -> None:
    """A campaign brief from the Notion briefs database."""
    out(tools.brief(brief_id))


@app.command()
def segments(product: str) -> None:
    """Audience segments (with their persona) for a product."""
    out(tools.segments(product))


@app.command()
def product(name: str) -> None:
    """A product and its approved claims."""
    out(tools.product(name))


@app.command()
def brand() -> None:
    """The brand guide: voice rules, banned claims, required disclaimer, subject line rules."""
    out(tools.brand())


@app.command("draft")
def draft(campaign_id: str, body_file: str = typer.Option(..., "--body-file", help="markdown file with the email body"),
          subject: list[str] = typer.Option(..., "--subject", help="repeat three times"), segment: str = typer.Option(..., "--segment")) -> None:
    """Submit a draft (three subject lines + body) and get a draft id."""
    from pathlib import Path

    out(tools.submit_draft(campaign_id, subject, Path(body_file).read_text(), segment))


@app.command()
def check(draft_id: str) -> None:
    """Run the compliance check on a draft."""
    out(tools.check(draft_id))


@app.command()
def schedule(draft_id: str, segment: str = typer.Option(..., "--segment"), at: str = typer.Option(..., "--at", help="ISO time, e.g. 2026-10-14T09:00Z"),
             subject: str = typer.Option(..., "--subject", help="the chosen subject line, verbatim")) -> None:
    """Schedule a draft that passed compliance."""
    out(tools.schedule(draft_id, segment, at, subject))


@app.command("log")
def log_cmd(campaign_id: str, draft: str = typer.Option(..., "--draft"), summary: str = typer.Option(..., "--summary"),
            scheduled: bool = typer.Option(False, "--scheduled/--not-scheduled")) -> None:
    """Log the campaign in Notion."""
    out(tools.log(campaign_id, draft, summary, scheduled))


@app.command()
def decide(question: str = typer.Option(..., "--question"), options: str = typer.Option(..., "--options", help="comma-separated"),
           answer: str = typer.Option(..., "--answer"), why: str = typer.Option(..., "--why")) -> None:
    """Log a judgment call: the question, the options considered, the answer, and why."""
    out(tools.decide(question, [o.strip() for o in options.split(",")], answer, why))


# ------------------------------------------------------------------ pipeline
@app.command("import")
def import_cmd() -> None:
    """Step 1: write the Notion workspace into memory."""
    from blast.importer import run_import, verify

    run_import(log=typer.echo)
    raise typer.Exit(verify(log=typer.echo))


@app.command()
def verify(what: str = typer.Argument("import")) -> None:
    """Check a stage: import | traces."""
    if what == "import":
        from blast.importer import verify as v

        raise typer.Exit(v(log=typer.echo))
    if what == "traces":
        from blast.record import verify_traces

        raise typer.Exit(verify_traces(log=typer.echo))
    raise typer.Exit(f"unknown stage {what}")


@app.command()
def reset(yes: bool = typer.Option(False, "--yes")) -> None:
    """Wipe the memory database (everything the demo wrote)."""
    if not yes:
        raise typer.Exit("add --yes to wipe the memory database")
    from blast.importer import reset as r

    r(log=typer.echo)


@app.command()
def doctor() -> None:
    """Memory database reachable, keys present, aip installed."""
    import shutil

    from blast.env import require
    from blast.memory import cypher

    require("NEO4J_URI", "NEO4J_USERNAME", "NEO4J_PASSWORD")
    n = cypher("MATCH (n) RETURN count(n) AS n")[0]["n"]
    typer.echo(f"[memory] connected; {n} nodes")
    typer.echo(f"[typesafe] key {'present' if __import__('os').environ.get('TYPESAFE_API_KEY') else 'MISSING'} (the aip server needs it for decisions)")
    typer.echo(f"[aip] {'installed' if shutil.which('aip') else 'MISSING: aip CLI not on PATH'}")
    typer.echo(f"[claude] {'installed' if shutil.which('claude') else 'MISSING'}")
    typer.echo(f"[blast] {'on PATH' if shutil.which('blast') else 'not on PATH (run: uv tool install --editable .)'}")


@app.command()
def record(run_id: Optional[str] = typer.Argument(None), all_: bool = typer.Option(False, "--all"), model: Optional[str] = None) -> None:
    """Step 2: run the agent headlessly on one run (or --all) and record traces."""
    from blast.record import record_all, record_one

    if all_:
        record_all(model=model, log=typer.echo)
    elif run_id:
        record_one(run_id, model=model, log=typer.echo)
    else:
        raise typer.Exit("give a run id or --all")


traces_app = typer.Typer(help="Recorded traces: show, export.")
app.add_typer(traces_app, name="traces")


@traces_app.command("show")
def traces_show(run_id: str) -> None:
    from blast.record import show_trace

    show_trace(run_id, log=typer.echo)


@traces_app.command("export")
def traces_export() -> None:
    """Write source/sop.md and source/traces.md from memory for the AIP authoring step."""
    from blast.record import export_source

    export_source(log=typer.echo)


if __name__ == "__main__":
    app()
