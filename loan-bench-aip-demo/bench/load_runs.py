"""Post the aip run files a results folder kept to an aip server, so its runs can be queried.

    uv run --with agent-instruction-protocol python bench/load_runs.py bench/results/<folder> [server URL]

The benchmark's containers cannot reach a server, so their runs are recorded nowhere but in the
run files `run.py` saves (`<APP>.r<n>.aip-runs.json`). This posts each one to the server as aip
itself would have, unchanged but for one field: the run's `session` is set to the application's
id, so a query can group the runs of one application. The procedure must be published there
first (`aip publish built/assess_term_loan`). The server defaults to http://127.0.0.1:8000.
"""
import json
import pathlib
import sys
import tempfile
import urllib.request

from aip.client.runs import RunFile


def main():
    folder = pathlib.Path(sys.argv[1])
    server = (sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8000").rstrip("/")
    posted = 0
    for path in sorted(folder.glob("runs/*/*.aip-runs.json")):
        application = path.name.split(".")[0]
        for run_file in json.loads(path.read_text()):
            with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
                json.dump(run_file, f)
                f.flush()
                loaded = RunFile.load(pathlib.Path(f.name))
            record = loaded.recording()
            record["identity"] = {**(record.get("identity") or {}), "session": application}
            request = urllib.request.Request(server + "/runs", json.dumps(record).encode(), {"Content-Type": "application/json"})
            urllib.request.urlopen(request).read()
            posted += 1
    print(posted, "runs posted to", server)


if __name__ == "__main__":
    main()
