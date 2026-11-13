#!/usr/bin/env python3
"""Apply the hard rules R1 to R7 and guidance G1 to the figures `gather.py` produced.

Every threshold is read from the policy text the step hands in (`assets/policy.md`), so changing
a number in the policy changes the rule; a threshold the text no longer states fails the step
rather than falling back to a default. Touches no file, network or credential.

stdin:  {"state": {"figures": {...}}, "assets": {"policy": "<policy.md>"}, ...}
stdout: {"policy_check": {...}, "rules_fired": ["R3"], "band": "review"}

The band is what the rules say: `auto_decline` (a hard rule declines), `review` (a judgment is
needed), `human` (a person must see it: over the exposure cap, R7's connected exposure, or a
decline on a long-standing customer under G1), `auto_approve` (nothing fired). R7 says it is
never decided by the procedure alone whatever the other rules say, so `human` wins over
`auto_decline`, which wins over `review`.
"""

from __future__ import annotations

import json
import re
import sys

WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
         "eleven": 11, "twelve": 12, "eighteen": 18, "twenty-four": 24, "thirty-six": 36, "sixty": 60}


def number(text: str) -> float:
    text = text.strip().lower().replace("$", "").replace(",", "")
    return float(WORDS[text]) if text in WORDS else float(text)


def paragraph(policy: str, rule: str) -> str:
    m = re.search(r"\*\*" + re.escape(rule) + r",(.*?)(?=\n\*\*|\n## |\Z)", policy, re.S)
    if not m:
        raise SystemExit(f"the policy text has no paragraph for rule {rule}")
    return " ".join(m.group(1).split())


def grab(text: str, pattern: str, rule: str, what: str) -> float:
    m = re.search(pattern, text, re.I)
    if not m:
        raise SystemExit(f"could not read {what} from the policy text of {rule}: {text[:120]}...")
    return number(m.group(1))


def thresholds(policy: str) -> dict:
    r2, r3, r4, r5, r6, r7, g1 = (paragraph(policy, r) for r in ("R2", "R3", "R4", "R5", "R6", "R7", "G1"))
    return {
        "R2_fraud_months": grab(r2, r"last ([\w-]+) months", "R2", "the fraud window in months"),
        "R3_coverage_floor": grab(r3, r"ratio of ([\d.]+) or more", "R3", "the coverage floor"),
        "R3_decline_line": grab(r3, r"under ([\d.]+) is an automatic decline", "R3", "the coverage decline line"),
        "R4_exposure_cap": grab(r4, r"at or under \$([\d,]+)", "R4", "the exposure cap"),
        "R5_late_days": grab(r5, r"([\d]+) days or more late", "R5", "the days-late line"),
        "R6_tenure_months": grab(r6, r"fewer than ([\w-]+) months", "R6", "the tenure line in months"),
        "R7_connected_cap": grab(r7, r"over \$([\d,]+)", "R7", "the connected exposure cap"),
        "G1_tenure_years": grab(g1, r"([\w-]+) years or more", "G1", "the long-standing customer line in years"),
    }


def main() -> None:
    payload = json.load(sys.stdin)
    fig = payload["state"]["figures"]
    t = thresholds(payload["assets"]["policy"])
    fired, guidance = [], []

    def fire(rule, name, value, threshold, effect, cites):
        fired.append({"rule": rule, "name": name, "value": value, "threshold": threshold, "effect": effect, "cites": cites})

    kyc = fig["kyc"]
    if kyc.get("status") == "overdue":
        fire("R1", "KYC current", kyc["status"], "current", "auto_decline", [kyc["key"]])
    elif kyc.get("status") == "refresh_due":
        fire("R1", "KYC current", kyc["status"], "current", "review", [kyc["key"]])

    recent = [e for e in fig["fraud_events"] if e["months_ago"] <= t["R2_fraud_months"]]
    if recent:
        fire("R2", "no fraud event in twelve months", f"{recent[0]['months_ago']} months ago", f"{t['R2_fraud_months']:g} months", "auto_decline",
             [e["key"] for e in recent])

    cov = fig["coverage"]["ratio"]
    if cov is not None and cov < t["R3_decline_line"]:
        fire("R3", "coverage floor", cov, t["R3_decline_line"], "auto_decline", fig["coverage"]["cites"])
    elif cov is not None and cov < t["R3_coverage_floor"]:
        fire("R3", "coverage floor", cov, t["R3_coverage_floor"], "review", fig["coverage"]["cites"])

    if fig["exposure"]["total"] > t["R4_exposure_cap"]:
        fire("R4", "exposure cap", fig["exposure"]["total"], t["R4_exposure_cap"], "human", fig["exposure"]["cites"])

    if fig["connected_delinquency"]["worst_late_days"] >= t["R5_late_days"]:
        fire("R5", "connected delinquency", fig["connected_delinquency"]["worst_late_days"], t["R5_late_days"], "review",
             fig["connected_delinquency"]["cites"])

    if fig["business"]["tenure_months"] < t["R6_tenure_months"]:
        fire("R6", "tenure", fig["business"]["tenure_months"], t["R6_tenure_months"], "review", [fig["business"]["key"]])

    if fig["exposure"]["connected"] > t["R7_connected_cap"]:
        fire("R7", "connected exposure cap", fig["exposure"]["connected"], t["R7_connected_cap"], "human",
             [f["key"] for c in fig["connected"] for f in c["facilities"]])

    long_standing = fig["business"]["tenure_years"] >= t["G1_tenure_years"]
    declines = any(f["effect"] == "auto_decline" for f in fired)
    if long_standing:
        guidance.append({"rule": "G1", "name": "long-standing customer decline", "value": fig["business"]["tenure_years"], "threshold": t["G1_tenure_years"],
                         "effect": "a decline goes to a human before it is filed", "applies_now": declines, "cites": [fig["business"]["key"]]})

    if any(f["effect"] == "human" for f in fired) or (declines and long_standing):
        band = "human"
    elif declines:
        band = "auto_decline"
    elif any(f["effect"] == "review" for f in fired):
        band = "review"
    else:
        band = "auto_approve"

    check = {"as_of": fig["as_of"], "application": fig["application"]["key"], "band": band, "fired": fired, "guidance": guidance, "thresholds": t,
             "figures": {"coverage_ratio": cov, "avg_net_12m": fig["coverage"]["avg_net_12m"], "proposed_monthly_payment": fig["coverage"]["proposed_monthly_payment"],
                         "existing_monthly_payments": fig["coverage"]["existing_monthly_payments"], "total_monthly_payments": fig["coverage"]["total_monthly_payments"],
                         "exposure_total": fig["exposure"]["total"], "exposure_own": fig["exposure"]["own"], "exposure_connected": fig["exposure"]["connected"],
                         "connected_worst_late_days": fig["connected_delinquency"]["worst_late_days"], "tenure_months": fig["business"]["tenure_months"],
                         "tenure_years": fig["business"]["tenure_years"], "kyc_status": kyc.get("status"), "fraud_events": len(fig["fraud_events"]),
                         "amount": fig["application"]["amount"], "term_months": fig["application"]["term_months"]}}
    figs = check["figures"]
    where = {"auto_approve": "No hard rule fired; the policy approves without judgment.", "auto_decline": "A hard rule declines; no judgment is needed.",
             "review": "The hard rules sent this application to review.", "human": "A rule sends this application to a person."}[band]
    summary = (where + " Fired: " + ("; ".join(f"{f['rule']} {f['name']}: {f['value']} against {f['threshold']} ({f['effect']})" for f in fired) or "none")
               + f". Not fired: KYC {figs['kyc_status']}, {figs['fraud_events']} fraud events in the window, coverage ratio {figs['coverage_ratio']}, "
               + f"total exposure {figs['exposure_total']:,.0f} against the cap of {t['R4_exposure_cap']:,.0f}, connected exposure {figs['exposure_connected']:,.0f}, "
               + f"connected facilities {figs['connected_worst_late_days']} days late, tenure {figs['tenure_months']} months. Guidance: "
               + ("; ".join(g["name"] + (" (applies now)" if g.get("applies_now") else " (noted; no decline proposed)") for g in guidance) or "none") + ".")
    json.dump({"policy_check": check, "rules_fired": [f["rule"] for f in fired], "band": band, "policy_summary": summary}, sys.stdout)


if __name__ == "__main__":
    main()
