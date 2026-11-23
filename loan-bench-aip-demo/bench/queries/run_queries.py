"""Run the analytics queries over the runs on an aip server's graph and save what they return.

    uv run --with neo4j python bench/queries/run_queries.py bolt://127.0.0.1:7695 neo4j <password>

The queries are in `queries.json` beside this file; the answers are written to `results.json`,
which the notebook shows. Load the runs first with `bench/load_runs.py`.
"""
import json
import pathlib
import sys

from neo4j import GraphDatabase

HERE = pathlib.Path(__file__).resolve().parent


def main():
    uri, user, password = sys.argv[1:4]
    queries = json.loads((HERE / "queries.json").read_text())
    with GraphDatabase.driver(uri, auth=(user, password)) as driver, driver.session() as session:
        results = [{"question": q["question"], "rows": [row.data() for row in session.run(q["cypher"])]} for q in queries]
    (HERE / "results.json").write_text(json.dumps(results, indent=1) + "\n")
    for result in results:
        print(len(result["rows"]), "rows:", result["question"])


if __name__ == "__main__":
    main()
