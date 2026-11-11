"""Compare Paired Editing Trials Against A Declared Gain And Quality Guardrail."""

import argparse
import csv
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from statistics import median
import sys


COLUMNS = ("pair", "input_ref", "order", "baseline", "candidate", "baseline_guard",
           "candidate_guard", "baseline_evidence", "candidate_evidence")
PLAN_FIELDS = ("baseline_workflow", "candidate_workflow", "metric", "unit", "direction",
               "minimum_pairs", "minimum_median_gain", "guardrail", "maximum_guard_increase")


def number(value, label):
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Expected A Number In {label}") from exc
    if not result.is_finite() or result.adjusted() > 18 or result.as_tuple().exponent < -9:
        raise ValueError(f"Use A Finite Number Within The Supported Precision In {label}")
    return result


def read_plan(path):
    with path.open(encoding="utf-8-sig") as stream:
        plan = json.load(stream, parse_float=Decimal)
    if not isinstance(plan, dict) or set(plan) != set(PLAN_FIELDS):
        raise ValueError("Plan Fields Must Match The Included Example")
    for key in ("baseline_workflow", "candidate_workflow", "metric", "unit", "guardrail"):
        if not isinstance(plan[key], str) or not plan[key].strip():
            raise ValueError(f"Enter A Label For {key}")
    if plan["baseline_workflow"].strip() == plan["candidate_workflow"].strip():
        raise ValueError("Give Each Workflow A Distinct Revision Label")
    if plan["direction"] not in ("higher", "lower"):
        raise ValueError("Choose higher Or lower For direction")
    if type(plan["minimum_pairs"]) is not int or plan["minimum_pairs"] < 1:
        raise ValueError("Minimum Pairs Must Be A Positive Integer")
    for key in ("minimum_median_gain", "maximum_guard_increase"):
        plan[key] = number(plan[key], key)
        if plan[key] < 0:
            raise ValueError(f"Enter A Nonnegative Limit For {key}")
    return plan


def read_trials(path, plan):
    trials = []
    seen_pairs = set()
    seen_inputs = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or sorted(reader.fieldnames) != sorted(COLUMNS):
            raise ValueError("CSV Columns Must Match The Included Example")
        for row in reader:
            if None in row or any(not row[key] or not row[key].strip() for key in COLUMNS):
                raise ValueError(f"Missing Or Extra Values On CSV Line {reader.line_num}")
            row = {k: v.strip() for k, v in row.items()}
            if row["pair"] in seen_pairs or row["input_ref"] in seen_inputs:
                raise ValueError("Each Paired Trial Requires A Distinct Pair And Input Reference")
            if row["order"] not in ("AB", "BA"):
                raise ValueError("Trial Order Must Be AB Or BA")
            if row["baseline_evidence"] == row["candidate_evidence"]:
                raise ValueError("Provide A Distinct Evidence Pointer For Each Workflow Run")
            seen_pairs.add(row["pair"])
            seen_inputs.add(row["input_ref"])
            baseline = number(row["baseline"], "baseline")
            candidate = number(row["candidate"], "candidate")
            gain = candidate - baseline if plan["direction"] == "higher" else baseline - candidate
            guard_change = number(row["candidate_guard"], "candidate_guard") - number(
                row["baseline_guard"], "baseline_guard")
            trials.append({**row, "gain": gain, "guard_change": guard_change,
                           "guard_breached": guard_change > plan["maximum_guard_increase"]})
    return sorted(trials, key=lambda trial: trial["pair"])


def compare(plan, trials):
    gains = [trial["gain"] for trial in trials]
    middle = median(gains) if gains else None
    breaches = [t["pair"] for t in trials if t["guard_breached"]]
    enough = len(trials) >= plan["minimum_pairs"]
    if breaches:
        decision = "Revise Candidate"
    elif not enough:
        decision = "Collect More Pairs"
    elif middle > 0 and middle >= plan["minimum_median_gain"]:
        decision = "Candidate Meets Trial Criteria"
    else:
        decision = "Keep Baseline"
    return {
        "decision": decision, "plan": plan, "pair_count": len(trials), "median_gain": middle,
        "pair_wins": sum(g > 0 for g in gains), "pair_ties": sum(g == 0 for g in gains),
        "pair_losses": sum(g < 0 for g in gains), "guard_breaches": breaches,
        "orders_observed": sorted({t["order"] for t in trials}), "trials": trials,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="Comparison Plan JSON")
    parser.add_argument("trials", type=Path, help="Paired Evidence CSV")
    args = parser.parse_args()
    try:
        plan = read_plan(args.plan)
        report = compare(plan, read_trials(args.trials, plan))
    except (ValueError, OSError, csv.Error) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, default=str, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
