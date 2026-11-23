# The loan benchmark

One task, done two ways, measured the same way. The task is Lantern Mutual's small-business
term loan assessment: one written application in, one of four outcomes out. The two ways are a
**baseline** agent that is handed the SOP and the policy and told to follow them, and an **AIP**
agent that runs a procedure compiled from the same two documents. The agent is Claude Code in
both.

## The task

| Path | What |
|---|---|
| `source/policy.md` | The rules: completeness, seven hard rules (H1 to H7, checkable by arithmetic), five judgment rules (J1 to J5, which a reader must judge), and how they form the outcome |
| `source/sop.md` | The order of work, the six fields every assessment returns (section 6) and the rules for the two messages (section 7) |
| `applications/` | The benchmark's thirty applications, one file each, in three tiers of ten: easy (`APP-20xx`), medium (`APP-21xx`), hard (`APP-22xx`). Sections 1 to 4 are `Label: value` fields and a document list; sections 5 to 7 are the applicant's own words |
| `expected.json` | The right answer for each application: its tier, outcome, failed rules, missing items. Read only by the scorer |
| `make_applications.py` | Writes both of the above. It recomputes the hard-rule answers from the fields and stops if one disagrees with its label; the judgment-rule answers are by design |
| `applications-dev/` | Two applications that are not in the benchmark. The procedure's builder sees these and no others |
| `built/` | The procedure the AIP arms run: built by Claude (below), then edited by hand |

The four outcomes, tested in this order: **return** (incomplete), **decline** (fails a hard
rule), **approve** (every judgment rule holds, each with a probability above 0.75), **escalate**
(anything else; the application goes to a credit officer's queue and the assessment ends).

## What is measured

Each run returns six fields, enforced by a JSON schema (`bench/result.schema.json`). Five are
scored, each 0 or 1:

| Measure | 1 when |
|---|---|
| `outcome` | it equals the expected outcome |
| `failed_rules` | the set of rule ids equals the expected set (order ignored) |
| `missing` | the set of missing items equals the expected set (order, case and spacing ignored) |
| `customer_message` | it passes a scripted rubric: 150 words or fewer, the outcome in the first sentence, no rule ids, and the reasons present (the missing items for a return, the required figure for each failed hard rule, the amount, term and payment for an approval, the credit officer for an escalation) |
| `officer_message` | it passes its rubric: 150 words or fewer, the outcome in the first sentence, every expected rule id |

Beside them, from what Claude Code reports for the run: tokens (input, cache write, cache read,
output; thinking tokens are counted inside output and also shown alone), estimated cost at list
price, turns, and seconds. The rubrics are in `bench/score.py`; they are strict and literal.

## Isolation

Every agent run is one Docker container, and the rule is that a container holds only what the
agent is meant to have.

- **What a baseline run sees:** `sop.md`, `policy.md` and one `application.md`, mounted
  read-only at `/work`. It has two tools, Read and Bash.
- **What it never sees:** `expected.json`, the scorer, any other application, this folder, your
  home directory. None of them is in the image or mounted. Scoring happens on the host, after
  the container has gone.
- **Network:** the container is on a Docker network created with `--internal`, which has no
  route out. Its one exit is `bench/proxy.py`, a small HTTPS proxy that allows the hosts on its
  command line and refuses the rest: `api.anthropic.com` for the baseline, plus the decision
  model (`api.typesafe.ai`) wherever aip runs. Every connection attempt, allowed or denied, is
  logged and saved as `egress.log` with the results.
- **Claude Code itself:** started with `--bare`, so no memory, skills, plugins, hooks, MCP
  servers or `CLAUDE.md` load, and with a fresh home directory. It signs in with
  `ANTHROPIC_API_KEY` only (bare mode reads nothing else), so runs are billed to that API key.

The keys are passed in the container's environment and are never written to a file. The
Anthropic key is read from `ANTHROPIC_API_KEY` in the environment, or else from `.env` in this
folder (`--key-file` to change it). The decision model's key is read from
`AIP_DECISION_MODEL_KEY` in the same two places, or else from `~/.config/aip/config.json`, where
`aip config --decision-model-key` keeps it.

## Running the benchmark

Needs Docker, Python 3.11 or later, an Anthropic API key, and for the aip arms a
[TypeSafe](https://typesafe.ai) key for the decision model. Nothing else is installed on your
machine: Claude Code and `aip` (0.9.0, from PyPI) are installed inside the images, which the
first run builds.

```sh
cd loan-bench-aip-demo
cp .env.example .env                                      # then put the two keys in it
python3 bench/run.py bench/configs/floor-ceiling.toml     # run every cell on every application
python3 bench/watch.py                                    # in another terminal: the live screen
python3 bench/score.py bench/results/<folder>             # the table, scores.csv, summary.json
```

A config is a list of cells. Each cell is an arm, a model and an effort, so the baseline and
AIP arms can cover different models and efforts:

```toml
applications = "APP-*"      # a glob over the ids in applications/
concurrency  = 8            # containers at once
repeats      = 1            # runs of each cell on each application

[[cell]]
arm    = "baseline"
model  = "sonnet"           # passed to `claude --model`
effort = "max"              # passed to `claude --effort`: low, medium, high, xhigh, max
```

Sonnet 5.5 and Haiku 5.5 always think; there is no "off". `low` is the least.

With tiers in `expected.json`, `score.py` also prints the correct runs for each tier and the
number of applications where every repeat gave the same answer.

`run.py --only APP-2001` runs one application, as a smoke test. `watch.py` shows, for each cell,
the running averages of every measure, then one group of five marks per run in the order
outcome, rules, missing, customer message, officer message, then what each failed run missed.

### What a run leaves

Everything goes to `bench/results/<config>-<time>/`, which git ignores:

| File | What |
|---|---|
| `runs/<cell>/<APP>.r<n>.json` | One run: the six-field answer, usage per model, cost, turns, durations, exit code |
| `runs/<cell>/<APP>.r<n>.transcript.jsonl` | The run's transcript: every message and tool call |
| `runs/<cell>/<APP>.r<n>.aip-runs.json` | For the aip arms, aip's own record of the run: every step, with what it read and produced, each hard rule's figure and each judgment rule's probability |
| `plan.json`, `config.toml` | The runs planned, and the config as it was |
| `egress.log` | Every connection the containers attempted |
| `scores.csv`, `summary.json` | Written by `score.py`: one row per run, and the averages per cell |

## The results

`analysis.html` is the results of our runs as figures and tables; open it in a browser.
`analysis.ipynb` is the notebook behind it. The run data itself is not in the repository, so to
run the notebook, run the benchmark first and put your own results folders in the `RUNS` list in
its first code cell.

## Building the procedure

The AIP arm runs a procedure, and Claude builds it, alone, in a container of its own:

```sh
python3 bench/build.py --model fable --effort high
```

- **The prompt** is `bench/prompt-build.md`. It says what the procedure's input and result are,
  which kind of step does each kind of work (a script for the form check, a `For` over the
  judgment rules with one `Decide` each, an `Aggregate`, routes for the endings, a script for
  each of the four endings, one `Task_Agent` for the two messages) and what "done" means.
- **The image** is `bench/Dockerfile.aip`: Claude Code, Python 3.14, `aip` 0.9.0 from PyPI
  (`AIP_VERSION` in the environment to change the release), and the aip skill at
  `/opt/aip/skill`.
- **What the builder sees:** the SOP, the policy and the two applications under
  `applications-dev/`. It does not see the benchmark's applications or `expected.json`, so it
  cannot fit the procedure to the answers. It can reach the Anthropic API and the decision
  model, and nothing else.
- **What it leaves:** the procedure is copied to `built/assess_term_loan/`. The transcript, the
  builder's closing report (`report.md`), its usage and cost (`result.json`), the files it left
  in its working directory and the egress log go to `bench/results/build-<time>/`.

`built/` is what the AIP arms run. It is not a one-shot build: procedures are built in rounds
with a person, so it is the build's output improved by hand, and each hand edit is also written
into `prompt-build.md` so the prompt still describes the procedure. One edit so far: the input
is the application's file (`application_file`), which the form check opens itself. Before that
the agent had to type the form's text into the run, and sometimes mistyped it.

## Files under `bench/`

| File | What |
|---|---|
| `run.py` | The runner: one container per run, in parallel |
| `score.py`, `watch.py` | The scorer and the live screen; both run on the host |
| `extract.py` | Reads the figures out of each baseline answer with a model, for the notebook's audit questions; needs the `anthropic` package |
| `load_runs.py` | Posts the aip run files a results folder kept to an aip server, so the runs can be queried |
| `queries/` | The notebook's analytics questions as Cypher (`queries.json`), the script that runs them over a server's graph, and what they returned (`results.json`) |
| `build.py`, `prompt-build.md` | The procedure's build |
| `proxy.py` | The allow-list proxy that is each container's only way out |
| `Dockerfile.baseline`, `Dockerfile.aip` | The two images |
| `prompt-baseline.md`, `prompt-aip-mcp.md`, `prompt-aip.md` | What each arm's agent is told |
| `result.schema.json` | The six fields every run must return |
| `configs/` | The benchmark configs |

## The arms

A cell's `arm` is one of three:

| Arm | What the agent is given | Its tools |
|---|---|---|
| `baseline` | `sop.md`, `policy.md` and `application.md`, and the instruction to follow them (`prompt-baseline.md`) | Read, Bash |
| `aip-mcp` | `application.md` and the procedure folder, with aip as MCP tools (`prompt-aip-mcp.md`). The agent calls `describe`, `run` with the application's file name, and `resume` with the two messages | aip's `describe`, `run`, `resume`; nothing else |
| `aip` | The same folder, the `aip` command and the aip skill file to learn it from (`prompt-aip.md`). Costs more tokens than `aip-mcp` for the same procedure | Read, Bash |

Both aip arms run `built/assess_term_loan` in the `Dockerfile.aip` image, with the decision
model's key in the environment and `api.typesafe.ai` allowed through the proxy. Their work
folder is writable, and the lines the procedure files (`decisions.jsonl`, `returns.jsonl`,
`credit_officer_queue.jsonl`) are saved beside each run as `<APP>.r<n>.filed.json`: the proof
that the procedure ran and what it decided.

What Claude Code reports covers the agent only. The decision model's calls, five for each
application that reaches the judgment rules, are not in the token or cost columns; their time is
in the seconds.
