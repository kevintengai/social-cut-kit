"""Compare Paired Trials Against A Declared Gain And Quality Guardrail."""

import argparse
import csv
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from statistics import median
import sys


COLUMNS = ("pair", "input_ref", "order", "baseline", "candidate", "baseline_guard",
           "candidate_guard", "baseline_evidence", "candidate_evidence")
SPLIT_COLUMN = "split"
SPLITS = ("develop", "select", "final")
DECISION_SPLIT = "final"
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


def load_trials(path, plan):
    """Return The Sorted Trials And Whether The File Carries A split Column."""
    trials = []
    seen_pairs = set()
    seen_inputs = set()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        names = sorted(reader.fieldnames or ())
        has_split = names == sorted(COLUMNS + (SPLIT_COLUMN,))
        if not has_split and names != sorted(COLUMNS):
            raise ValueError("CSV Columns Must Match The Included Example. Only The split Column Is Optional")
        columns = COLUMNS + ((SPLIT_COLUMN,) if has_split else ())
        for row in reader:
            if None in row or any(not row[key] or not row[key].strip() for key in columns):
                raise ValueError(f"Missing Or Extra Values On CSV Line {reader.line_num}")
            row = {k: v.strip() for k, v in row.items()}
            split = row.get(SPLIT_COLUMN)
            if has_split and split not in SPLITS:
                raise ValueError(f"Split Must Be develop, select, Or final On CSV Line {reader.line_num}")
            if row["pair"] in seen_pairs or (split, row["input_ref"]) in seen_inputs:
                if has_split:
                    raise ValueError("Each Paired Trial Requires A Distinct Pair, "
                                     "And A Distinct Input Reference Within Its Split")
                raise ValueError("Each Paired Trial Requires A Distinct Pair And Input Reference")
            if row["order"] not in ("AB", "BA"):
                raise ValueError("Trial Order Must Be AB Or BA")
            if row["baseline_evidence"] == row["candidate_evidence"]:
                raise ValueError("Provide A Distinct Evidence Pointer For Each Workflow Run")
            seen_pairs.add(row["pair"])
            seen_inputs.add((split, row["input_ref"]))
            baseline = number(row["baseline"], "baseline")
            candidate = number(row["candidate"], "candidate")
            gain = candidate - baseline if plan["direction"] == "higher" else baseline - candidate
            guard_change = number(row["candidate_guard"], "candidate_guard") - number(
                row["baseline_guard"], "baseline_guard")
            trials.append({**row, "gain": gain, "guard_change": guard_change,
                           "guard_breached": guard_change > plan["maximum_guard_increase"]})
    return sorted(trials, key=lambda trial: trial["pair"]), has_split


def read_trials(path, plan):
    return load_trials(path, plan)[0]


def summarize(trials):
    gains = [trial["gain"] for trial in trials]
    return {
        "pair_count": len(trials), "median_gain": median(gains) if gains else None,
        "pair_wins": sum(g > 0 for g in gains), "pair_ties": sum(g == 0 for g in gains),
        "pair_losses": sum(g < 0 for g in gains),
        "guard_breaches": [t["pair"] for t in trials if t["guard_breached"]],
        "orders_observed": sorted({t["order"] for t in trials}), "trials": trials,
    }


def decide(plan, summary):
    middle = summary["median_gain"]
    if summary["guard_breaches"]:
        return "Revise Candidate"
    if summary["pair_count"] < plan["minimum_pairs"]:
        return "Collect More Pairs"
    if middle > 0 and middle >= plan["minimum_median_gain"]:
        return "Candidate Meets Trial Criteria"
    return "Keep Baseline"


def split_warnings(trials):
    warnings = []
    if not any(trial[SPLIT_COLUMN] == DECISION_SPLIT for trial in trials):
        warnings.append("No final Rows Exist. The Decision Counts final Rows Only, "
                        "So develop And select Rows Cannot Meet The Trial Criteria.")
    places = {}
    for trial in trials:
        places.setdefault(trial["input_ref"], set()).add(trial[SPLIT_COLUMN])
    for input_ref in sorted(places):
        found = [name for name in SPLITS if name in places[input_ref]]
        if len(found) < 2:
            continue
        if DECISION_SPLIT in found:
            advice = ("A Final Case That Informed A Change Is No Longer A Final Case. "
                      "Replace It With An Untouched Input Before Relying On This Decision.")
        else:
            advice = "Keep Each Input In One Split So Selection Does Not Reuse Development Cases."
        warnings.append(f"Input {input_ref} Appears In Splits {' And '.join(found)}. {advice}")
    return warnings


def compare(plan, trials, has_split=None):
    if has_split is None:
        has_split = any(SPLIT_COLUMN in trial for trial in trials)
    if not has_split:
        summary = summarize(trials)
        return {"decision": decide(plan, summary), "plan": plan, **summary}
    groups = {name: [t for t in trials if t[SPLIT_COLUMN] == name] for name in SPLITS}
    summary = summarize(groups[DECISION_SPLIT])
    return {
        "decision": decide(plan, summary), "decision_split": DECISION_SPLIT,
        "warnings": split_warnings(trials), "plan": plan, **summary,
        "other_splits": {name: summarize(groups[name]) for name in SPLITS if name != DECISION_SPLIT},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="Comparison Plan JSON")
    parser.add_argument("trials", type=Path,
                        help="Paired Evidence CSV. An Optional split Column Holds develop, select, Or final")
    args = parser.parse_args(argv)
    try:
        plan = read_plan(args.plan)
        trials, has_split = load_trials(args.trials, plan)
        report = compare(plan, trials, has_split)
    except (ValueError, OSError, csv.Error) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(report, default=str, indent=2))
    for warning in report.get("warnings", ()):
        print(f"Warning: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
