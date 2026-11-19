"""Score a results folder against expected.json, on the host.

    python3 bench/score.py bench/results/<folder>

Five measures per run, each 0 or 1: the outcome, the failed rules (as a set), the missing items
(as a set, case and spacing ignored), and a scripted rubric for each of the two messages. Prints
one row per cell and writes `scores.csv` (one row per run) and `summary.json` into the folder.
"""
import csv
import json
import pathlib
import re
import statistics
import sys

DEMO = pathlib.Path(__file__).resolve().parent.parent
FIRST = {"approve": r"approv", "decline": r"declin|not approved|unable to (approve|offer)|cannot (approve|offer)",
         "return": r"return|incomplete|missing|cannot (be )?(assess|process)", "escalate": r"review|credit officer|escalat"}
# What a customer must be told for each failed hard rule: the figure the policy requires.
THRESHOLD = {"H1": r"10000|250000", "H2": r"\b(12|60)\b", "H3": r"\b24\b|two years", "H4": r"\b660\b",
             "H5": r"bankrupt|lien", "H6": r"1\.25", "H7": r"\b25\b|quarter"}
MEASURES = ["outcome", "failed_rules", "missing", "customer_message", "officer_message"]
DECIDED = ["outcome", "failed_rules", "missing"]


def norm(text):
    return re.sub(r"\s+", " ", str(text)).strip().lower()


def plain(text):
    """Lowercase, with the commas and dollar signs out of the numbers."""
    return re.sub(r"(?<=\d),(?=\d)", "", norm(text)).replace("$", "")


def first_sentence(text):
    return re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]


def fields(application):
    text = (DEMO / "applications" / f"{application}.md").read_text()
    return {k.strip(): v.strip() for k, v in re.findall(r"^([^#\-\n][^:\n]*):[ \t]*(.*)$", text, re.M)}


def message_checks(want, form, customer, officer):
    outcome = want["outcome"]
    c, o = plain(customer), plain(officer)
    customer_checks = {
        "under_150_words": len(customer.split()) <= 150,
        "outcome_first": bool(re.search(FIRST[outcome], norm(first_sentence(customer)))),
        "no_rule_ids": not re.search(r"\b[HJ][1-7]\b", customer),
    }
    officer_checks = {
        "under_150_words": len(officer.split()) <= 150,
        "outcome_first": bool(re.search(FIRST[outcome], norm(first_sentence(officer)))),
        "rule_ids": all(re.search(rf"\b{r}\b", officer) for r in want["failed_rules"]),
    }
    if outcome == "return":
        customer_checks["reasons"] = all(norm(m) in c for m in want["missing"])
        officer_checks["reasons"] = all(norm(m) in o for m in want["missing"])
    elif outcome == "decline":
        customer_checks["reasons"] = all(re.search(THRESHOLD[r], c) for r in want["failed_rules"])
    elif outcome == "approve":
        terms = [plain(form[k]) for k in ("Amount requested", "Term in months", "Quoted monthly payment")]
        customer_checks["reasons"] = all(t in c for t in terms)
    else:
        customer_checks["reasons"] = "credit officer" in c
    return customer_checks, officer_checks


def tokens(claude):
    total = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0, "thinking": 0}
    for usage in (claude.get("modelUsage") or {}).values():
        total["input"] += usage.get("inputTokens", 0)
        total["cache_write"] += usage.get("cacheCreationInputTokens", 0)
        total["cache_read"] += usage.get("cacheReadInputTokens", 0)
        total["output"] += usage.get("outputTokens", 0)
        total["thinking"] += usage.get("thinkingTokens", 0)      # already inside output
    return total


def score(record, expected):
    want = expected[record["application"]]
    claude = record.get("claude") or {}
    got = claude.get("structured_output") or {}
    row = {"cell": record["cell"], "application": record["application"], "repeat": record["repeat"],
           "difficulty": want.get("difficulty", ""), "expected": want["outcome"], "got": got.get("outcome", ""),
           "answered": int(bool(got))}
    customer, officer = message_checks(want, fields(record["application"]),
                                       got.get("customer_message", ""), got.get("officer_message", ""))
    row["outcome"] = int(got.get("outcome") == want["outcome"])
    row["failed_rules"] = int(bool(got) and set(got.get("failed_rules", [])) == set(want["failed_rules"]))
    row["missing"] = int(bool(got) and {norm(m) for m in got.get("missing", [])} == {norm(m) for m in want["missing"]})
    row["customer_message"] = int(bool(got) and all(customer.values()))
    row["officer_message"] = int(bool(got) and all(officer.values()))
    row["got_failed_rules"] = " ".join(got.get("failed_rules", []))
    row["message_failures"] = " ".join([f"customer:{k}" for k, v in customer.items() if not v]
                                       + [f"officer:{k}" for k, v in officer.items() if not v])
    row.update({f"tokens_{k}": v for k, v in tokens(claude).items()})
    row["tokens_total"] = sum(v for k, v in tokens(claude).items() if k != "thinking")
    row["cost_usd"] = round(claude.get("total_cost_usd") or 0, 4)
    row["turns"] = claude.get("num_turns", 0)
    row["seconds"] = round((claude.get("duration_ms") or 0) / 1000, 1)
    row["api_seconds"] = round((claude.get("duration_api_ms") or 0) / 1000, 1)
    row["wall_seconds"] = record["wall_seconds"]
    return row


def summarize(rows):
    summary = {}
    for cell in sorted({r["cell"] for r in rows}):
        mine = [r for r in rows if r["cell"] == cell]
        mean = lambda key: statistics.mean(r[key] for r in mine)
        summary[cell] = {"runs": len(mine), "answered": sum(r["answered"] for r in mine),
                         **{m: round(mean(m), 3) for m in MEASURES},
                         "all_five": round(statistics.mean(int(all(r[m] for m in MEASURES)) for r in mine), 3),
                         "tokens_total": round(mean("tokens_total")), "tokens_output": round(mean("tokens_output")), "tokens_thinking": round(mean("tokens_thinking")),
                         "cost_usd": round(mean("cost_usd"), 4), "turns": round(mean("turns"), 1),
                         "seconds_mean": round(mean("seconds"), 1),
                         "seconds_median": round(statistics.median(r["seconds"] for r in mine), 1),
                         "seconds_max": max(r["seconds"] for r in mine)}
    return summary


def load(folder, expected=None):
    expected = expected or json.loads((DEMO / "expected.json").read_text())
    rows = []
    for p in sorted((p for p in folder.glob("runs/*/*.json") if re.search(r"\.r\d+\.json$", p.name))):
        try:
            rows.append(score(json.loads(p.read_text()), expected))
        except ValueError:
            pass                      # a file still being written
    return rows


def main():
    folder = pathlib.Path(sys.argv[1])
    rows = load(folder)
    with open(folder / "scores.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows)
    (folder / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    keys = list(next(iter(summary.values())))
    print("cell".ljust(28) + "".join(k[:14].rjust(15) for k in keys))
    for cell, s in summary.items():
        print(cell.ljust(28) + "".join(str(s[k]).rjust(15) for k in keys))
    tiers = [t for t in ("easy", "medium", "hard") if any(r["difficulty"] == t for r in rows)]
    if tiers:
        decided = ("outcome", "failed_rules", "missing")
        print("\ncorrect runs by difficulty (outcome / rules / missing), and applications where every repeat agreed")
        for cell in summary:
            for tier in tiers:
                mine = [r for r in rows if r["cell"] == cell and r["difficulty"] == tier]
                answers = {}
                for r in mine:
                    answers.setdefault(r["application"], set()).add((r["got"], r["got_failed_rules"]))
                stable = sum(1 for a in answers.values() if len(a) == 1)
                print(f"  {cell:26} {tier:7} " + "  ".join(f"{sum(r[m] for r in mine):>3}/{len(mine)}" for m in decided)
                      + f"   stable {stable}/{len(answers)}")
    wrong = [r for r in rows if not all(r[m] for m in DECIDED)] if tiers else [r for r in rows if not all(r[m] for m in MEASURES)]
    if wrong:
        print("\nruns that missed a measure:")
        for r in wrong:
            missed = [m for m in MEASURES if not r[m]]
            print(f"  {r['cell']:28} {r['application']} expected {r['expected']:8} got {r['got'] or '-':8} "
                  f"[{r['got_failed_rules']}] missed: {', '.join(missed)} {r['message_failures']}")


if __name__ == "__main__":
    main()
