"""Exercise The Paired-Trial Helper With Temporary Plans And Trial Tables."""

import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_FOLDER = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_FOLDER / "scripts" / "compare.py"
ASSETS = SKILL_FOLDER / "assets"
LEGACY_KEYS = ["decision", "plan", "pair_count", "median_gain", "pair_wins", "pair_ties",
               "pair_losses", "guard_breaches", "orders_observed", "trials"]
SUMMARY_KEYS = LEGACY_KEYS[2:]
SPLIT_KEYS = ["decision", "decision_split", "warnings", "plan"] + SUMMARY_KEYS + ["other_splits"]
MEETS = "Candidate Meets Trial Criteria"
NO_FINAL = "No final Rows Exist."
DISTINCT = "Each Paired Trial Requires A Distinct Pair And Input Reference"
DISTINCT_IN_SPLIT = ("Each Paired Trial Requires A Distinct Pair, "
                     "And A Distinct Input Reference Within Its Split")

SPEC = importlib.util.spec_from_file_location("rsi_compare", SCRIPT)
compare = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(compare)

PLAN = {
    "baseline_workflow": "Current Caption Pass V1",
    "candidate_workflow": "Candidate Caption Pass V2",
    "metric": "Hands-On Correction Time",
    "unit": "Minutes",
    "direction": "lower",
    "minimum_pairs": 3,
    "minimum_median_gain": 2,
    "guardrail": "Caption Errors At Review",
    "maximum_guard_increase": 0,
}

# The Report Printed For The Bundled Example Before The split Column Existed.
BUNDLED_REPORT = {
    "decision": MEETS,
    "plan": {
        "baseline_workflow": "Manual Caption Timing V1",
        "candidate_workflow": "Phrase Grouping Pass V1",
        "metric": "Hands-On Caption Correction Time",
        "unit": "Minutes",
        "direction": "lower",
        "minimum_pairs": 3,
        "minimum_median_gain": "2",
        "guardrail": "Caption Errors Remaining At Editor Review",
        "maximum_guard_increase": "0",
    },
    "pair_count": 3,
    "median_gain": "2",
    "pair_wins": 3,
    "pair_ties": 0,
    "pair_losses": 0,
    "guard_breaches": [],
    "orders_observed": ["AB", "BA"],
    "trials": [
        {"pair": "P01", "input_ref": "Fixture-Opening-V1", "order": "AB", "baseline": "12",
         "candidate": "9", "baseline_guard": "1", "candidate_guard": "1",
         "baseline_evidence": "Fixture-Log-01#A", "candidate_evidence": "Fixture-Log-01#B",
         "gain": "3", "guard_change": "0", "guard_breached": False},
        {"pair": "P02", "input_ref": "Fixture-Interview-V1", "order": "BA", "baseline": "16",
         "candidate": "14", "baseline_guard": "2", "candidate_guard": "1",
         "baseline_evidence": "Fixture-Log-02#A", "candidate_evidence": "Fixture-Log-02#B",
         "gain": "2", "guard_change": "-1", "guard_breached": False},
        {"pair": "P03", "input_ref": "Fixture-Demo-V1", "order": "AB", "baseline": "10",
         "candidate": "9", "baseline_guard": "0", "candidate_guard": "0",
         "baseline_evidence": "Fixture-Log-03#A", "candidate_evidence": "Fixture-Log-03#B",
         "gain": "1", "guard_change": "0", "guard_breached": False},
    ],
}


def row(pair, baseline, candidate, split=None, order="AB", guards=(0, 0)):
    data = {
        "pair": pair, "input_ref": f"Input-{pair}", "order": order,
        "baseline": baseline, "candidate": candidate,
        "baseline_guard": guards[0], "candidate_guard": guards[1],
        "baseline_evidence": f"Log-{pair}#A", "candidate_evidence": f"Log-{pair}#B",
    }
    if split is not None:
        data["split"] = split
    return data


def rows_with_gains(gains, split=None, prefix="P"):
    """Build Rows Whose Candidate Saves The Given Minutes Under The lower Direction."""
    return [row(f"{prefix}{n}", 20, 20 - gain, split, "AB" if n % 2 else "BA")
            for n, gain in enumerate(gains, 1)]


def split_rows(develop=(), select=(), final=()):
    return (rows_with_gains(develop, "develop", "D") + rows_with_gains(select, "select", "S")
            + rows_with_gains(final, "final", "F"))


def run_script(*args):
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPT), *map(str, args)],
        capture_output=True, encoding="utf-8", errors="replace", check=False,
    )


class Base(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="paired trial test ")
        self.addCleanup(folder.cleanup)
        self.work = Path(folder.name)

    def save_plan(self, plan=None, **changes):
        path = self.work / "plan.json"
        data = dict(PLAN if plan is None else plan, **changes)
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def save_trials(self, rows, columns=None, encoding="utf-8"):
        path = self.work / "trials.csv"
        with path.open("w", encoding=encoding, newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(columns or rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def save_text(self, text, name="trials.csv"):
        path = self.work / name
        with path.open("w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        return path

    def run_main(self, plan, trials):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = compare.main([str(plan), str(trials)])
        return code, output.getvalue(), errors.getvalue()

    def report(self, rows, columns=None, **plan_changes):
        code, output, errors = self.run_main(
            self.save_plan(**plan_changes), self.save_trials(rows, columns))
        self.assertEqual(code, 0, errors)
        return json.loads(output), errors

    def rejected(self, trials, fragment, plan=None):
        if not isinstance(trials, Path):
            trials = self.save_trials(trials)
        code, output, errors = self.run_main(plan or self.save_plan(), trials)
        self.assertEqual(code, 1, output)
        self.assertEqual(output, "")
        self.assertIn(fragment, errors)


class LegacyTables(Base):
    def test_bundled_example_report_is_unchanged(self):
        result = run_script(ASSETS / "example-plan.json", ASSETS / "example-trials.csv")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, json.dumps(BUNDLED_REPORT, indent=2) + "\n")
        self.assertEqual(list(json.loads(result.stdout)), LEGACY_KEYS)

    def test_gain_at_the_threshold_meets_criteria(self):
        report, errors = self.report(rows_with_gains([3, 2, 1]))
        self.assertEqual(report["decision"], MEETS)
        self.assertEqual(report["median_gain"], "2")
        self.assertEqual((report["pair_wins"], report["pair_ties"], report["pair_losses"]), (3, 0, 0))
        self.assertEqual(report["orders_observed"], ["AB", "BA"])
        self.assertEqual(errors, "")

    def test_gain_below_the_threshold_keeps_baseline(self):
        report, _ = self.report(rows_with_gains([1, 1, 2, -4]))
        self.assertEqual(report["decision"], "Keep Baseline")
        self.assertEqual(report["median_gain"], "1")
        self.assertEqual((report["pair_wins"], report["pair_ties"], report["pair_losses"]), (3, 0, 1))

    def test_zero_gain_never_meets_criteria(self):
        report, _ = self.report(rows_with_gains([0, 0, 0]), minimum_median_gain=0)
        self.assertEqual(report["decision"], "Keep Baseline")
        self.assertEqual(report["pair_ties"], 3)

    def test_undersized_set_collects_more_pairs(self):
        report, _ = self.report(rows_with_gains([5, 5]))
        self.assertEqual(report["decision"], "Collect More Pairs")
        self.assertEqual(report["pair_count"], 2)

    def test_header_only_table_collects_more_pairs(self):
        report, errors = self.report([], columns=compare.COLUMNS)
        self.assertEqual(list(report), LEGACY_KEYS)
        self.assertEqual(report["decision"], "Collect More Pairs")
        self.assertEqual((report["pair_count"], report["median_gain"], report["trials"]), (0, None, []))
        self.assertEqual(errors, "")

    def test_guard_breach_takes_precedence(self):
        rows = rows_with_gains([5]) + [row("P2", 20, 10, guards=(1, 2))]
        report, _ = self.report(rows)
        self.assertEqual(report["decision"], "Revise Candidate")
        self.assertEqual(report["guard_breaches"], ["P2"])
        self.assertEqual([trial["guard_breached"] for trial in report["trials"]], [False, True])

    def test_guard_limit_allows_the_declared_increase(self):
        rows = [row(f"P{n}", 20, 15, guards=(1, 2)) for n in range(1, 4)]
        report, _ = self.report(rows, maximum_guard_increase=1)
        self.assertEqual(report["decision"], MEETS)
        self.assertEqual(report["guard_breaches"], [])

    def test_higher_direction_reverses_the_gain(self):
        rows = [row(f"P{n}", 70, 75) for n in range(1, 4)]
        report, _ = self.report(rows, direction="higher")
        self.assertEqual((report["decision"], report["median_gain"]), (MEETS, "5"))
        report, _ = self.report(rows)
        self.assertEqual((report["decision"], report["pair_losses"]), ("Keep Baseline", 3))

    def test_trials_sort_by_pair_and_keep_decimal_precision(self):
        rows = [row(pair, "12.5", "10.25") for pair in ("P3", "P1", "P2")]
        report, _ = self.report(rows)
        self.assertEqual([trial["pair"] for trial in report["trials"]], ["P1", "P2", "P3"])
        self.assertEqual(report["median_gain"], "2.25")

    def test_report_without_a_split_column_has_no_split_fields(self):
        report, errors = self.report(rows_with_gains([3, 2, 1]))
        self.assertEqual(list(report), LEGACY_KEYS)
        self.assertTrue(all("split" not in trial for trial in report["trials"]))
        self.assertEqual(errors, "")

    def test_byte_order_mark_and_padded_cells_are_accepted(self):
        rows = [dict(item, pair=f" {item['pair']} ") for item in rows_with_gains([3, 2, 1])]
        code, output, errors = self.run_main(
            self.save_plan(), self.save_trials(rows, encoding="utf-8-sig"))
        self.assertEqual(code, 0, errors)
        self.assertEqual([trial["pair"] for trial in json.loads(output)["trials"]], ["P1", "P2", "P3"])


class LegacyValidation(Base):
    def test_pairs_and_inputs_must_be_distinct(self):
        rows = rows_with_gains([3, 2, 1])
        rows[2]["pair"] = "P1"
        self.rejected(rows, DISTINCT)
        rows = rows_with_gains([3, 2, 1])
        rows[2]["input_ref"] = rows[0]["input_ref"]
        self.rejected(rows, DISTINCT)

    def test_order_and_evidence_rules(self):
        rows = rows_with_gains([3, 2, 1])
        rows[0]["order"] = "ab"
        self.rejected(rows, "Trial Order Must Be AB Or BA")
        rows = rows_with_gains([3, 2, 1])
        rows[1]["candidate_evidence"] = rows[1]["baseline_evidence"]
        self.rejected(rows, "Provide A Distinct Evidence Pointer For Each Workflow Run")

    def test_cells_must_be_present(self):
        message = "Missing Or Extra Values On CSV Line 2"
        rows = rows_with_gains([3, 2, 1])
        rows[0]["baseline_evidence"] = "  "
        self.rejected(rows, message)
        header = ",".join(compare.COLUMNS)
        self.rejected(self.save_text(f"{header}\nP1,Input-P1,AB,20,17,0,0,Log#A,Log#B,Surplus\n"), message)
        self.rejected(self.save_text(f"{header}\nP1,Input-P1,AB,20,17,0,0,Log#A\n"), message)

    def test_cells_must_be_supported_numbers(self):
        rows = rows_with_gains([3, 2, 1])
        rows[0]["baseline"] = "Twelve"
        self.rejected(rows, "Expected A Number In baseline")
        for value in ("NaN", "Infinity", "1e30", "0.0000000001"):
            with self.subTest(value=value):
                rows = rows_with_gains([3, 2, 1])
                rows[0]["candidate"] = value
                self.rejected(rows, "Use A Finite Number Within The Supported Precision In candidate")

    def test_columns_must_match(self):
        message = "CSV Columns Must Match The Included Example"
        rows = rows_with_gains([3, 2, 1])
        self.rejected([dict(item, notes="Extra") for item in rows], message)
        self.rejected([{key: item[key] for key in list(item)[:-1]} for item in rows], message)
        self.rejected(self.save_text(""), message)
        self.rejected(self.save_text(",".join(compare.COLUMNS + ("pair",)) + "\n"), message)

    def test_plan_rules(self):
        trials = self.save_trials(rows_with_gains([3, 2, 1]))
        fields = "Plan Fields Must Match The Included Example"
        missing = {key: value for key, value in PLAN.items() if key != "unit"}
        self.rejected(trials, fields, plan=self.save_plan(missing))
        self.rejected(trials, fields, plan=self.save_text("[1, 2]", "plan.json"))
        cases = (
            ({"notes": "Extra"}, fields),
            ({"metric": "  "}, "Enter A Label For metric"),
            ({"guardrail": 4}, "Enter A Label For guardrail"),
            ({"candidate_workflow": PLAN["baseline_workflow"]},
             "Give Each Workflow A Distinct Revision Label"),
            ({"direction": "Lower"}, "Choose higher Or lower For direction"),
            ({"minimum_pairs": 0}, "Minimum Pairs Must Be A Positive Integer"),
            ({"minimum_pairs": True}, "Minimum Pairs Must Be A Positive Integer"),
            ({"minimum_pairs": 2.0}, "Minimum Pairs Must Be A Positive Integer"),
            ({"minimum_median_gain": -1}, "Enter A Nonnegative Limit For minimum_median_gain"),
            ({"maximum_guard_increase": -0.5}, "Enter A Nonnegative Limit For maximum_guard_increase"),
            ({"minimum_median_gain": "Two"}, "Expected A Number In minimum_median_gain"),
        )
        for changes, message in cases:
            with self.subTest(changes=changes):
                self.rejected(trials, message, plan=self.save_plan(**changes))

    def test_unreadable_inputs_exit_one(self):
        trials = self.save_trials(rows_with_gains([3, 2, 1]))
        plan = self.save_plan()
        for arguments in ((self.work / "absent.json", trials), (plan, self.work / "absent.csv"),
                          (self.save_text("{", "broken.json"), trials)):
            with self.subTest(arguments=arguments):
                code, output, errors = self.run_main(*arguments)
                self.assertEqual((code, output), (1, ""))
                self.assertTrue(errors.strip())


class SplitTables(Base):
    def test_bundled_split_example_decides_on_final_rows(self):
        result = run_script(ASSETS / "example-plan.json", ASSETS / "example-split-trials.csv")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        report = json.loads(result.stdout)
        self.assertEqual(list(report), SPLIT_KEYS)
        self.assertEqual((report["decision"], report["decision_split"]), (MEETS, "final"))
        self.assertEqual(report["warnings"], [])
        self.assertEqual((report["pair_count"], report["median_gain"]), (4, "2"))
        self.assertEqual([trial["pair"] for trial in report["trials"]], ["F01", "F02", "F03", "F04"])
        self.assertEqual(list(report["other_splits"]), ["develop", "select"])
        develop, select = report["other_splits"]["develop"], report["other_splits"]["select"]
        self.assertEqual(list(develop), SUMMARY_KEYS)
        self.assertEqual((develop["pair_count"], develop["median_gain"]), (2, "4"))
        self.assertEqual((select["pair_count"], select["median_gain"]), (2, "3"))

    def test_bundled_examples_agree_on_the_decision(self):
        plain = run_script(ASSETS / "example-plan.json", ASSETS / "example-trials.csv")
        split = run_script(ASSETS / "example-plan.json", ASSETS / "example-split-trials.csv")
        self.assertEqual(json.loads(plain.stdout)["decision"], json.loads(split.stdout)["decision"])

    def test_decision_counts_final_rows_only(self):
        report, errors = self.report(split_rows(develop=[10, 10, 10], select=[9, 9, 9], final=[1, 1, 1]))
        self.assertEqual(report["decision"], "Keep Baseline")
        self.assertEqual((report["pair_count"], report["median_gain"]), (3, "1"))
        self.assertEqual(report["other_splits"]["develop"]["median_gain"], "10")
        self.assertEqual(report["other_splits"]["select"]["median_gain"], "9")
        self.assertEqual((report["warnings"], errors), ([], ""))

    def test_minimum_pairs_counts_final_rows_only(self):
        report, _ = self.report(split_rows(develop=[5, 5, 5], final=[5, 5]))
        self.assertEqual((report["decision"], report["pair_count"]), ("Collect More Pairs", 2))

    def test_breach_outside_final_rows_is_reported_without_changing_the_decision(self):
        rows = split_rows(final=[3, 3, 3]) + [row("D1", 20, 10, "develop", guards=(0, 2))]
        report, _ = self.report(rows)
        self.assertEqual((report["decision"], report["guard_breaches"]), (MEETS, []))
        self.assertEqual(report["other_splits"]["develop"]["guard_breaches"], ["D1"])

    def test_breach_in_final_rows_revises_the_candidate(self):
        rows = split_rows(develop=[3, 3, 3], final=[3, 3]) + [row("F9", 20, 10, "final", guards=(0, 1))]
        report, _ = self.report(rows)
        self.assertEqual((report["decision"], report["guard_breaches"]), ("Revise Candidate", ["F9"]))

    def test_missing_final_rows_warn_and_cannot_meet_criteria(self):
        report, errors = self.report(split_rows(develop=[9, 9, 9], select=[9, 9, 9]))
        self.assertEqual(report["decision"], "Collect More Pairs")
        self.assertEqual((report["pair_count"], report["median_gain"], report["trials"]), (0, None, []))
        self.assertEqual(len(report["warnings"]), 1)
        self.assertTrue(report["warnings"][0].startswith(NO_FINAL))
        self.assertIn(f"Warning: {NO_FINAL}", errors)

    def test_header_only_table_with_a_split_column_warns(self):
        report, errors = self.report([], columns=compare.COLUMNS + ("split",))
        self.assertEqual(list(report), SPLIT_KEYS)
        self.assertEqual(report["decision"], "Collect More Pairs")
        self.assertTrue(report["warnings"][0].startswith(NO_FINAL))
        self.assertIn(f"Warning: {NO_FINAL}", errors)

    def test_warnings_leave_standard_output_as_valid_json(self):
        plan = self.save_plan()
        trials = self.save_trials(split_rows(develop=[9, 9, 9]))
        result = run_script(plan, trials)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["decision"], "Collect More Pairs")
        self.assertIn(f"Warning: {NO_FINAL}", result.stderr)

    def test_input_shared_with_final_rows_warns(self):
        rows = split_rows(develop=[4], final=[3, 3, 3])
        rows[0]["input_ref"] = rows[1]["input_ref"]
        report, errors = self.report(rows)
        self.assertEqual(report["warnings"], [
            "Input Input-F1 Appears In Splits develop And final. "
            "A Final Case That Informed A Change Is No Longer A Final Case. "
            "Replace It With An Untouched Input Before Relying On This Decision."
        ])
        self.assertEqual(report["decision"], MEETS)
        self.assertIn("Warning: Input Input-F1 Appears In Splits develop And final.", errors)

    def test_input_shared_between_develop_and_select_rows_warns(self):
        rows = split_rows(develop=[4], select=[4], final=[3, 3, 3])
        rows[1]["input_ref"] = rows[0]["input_ref"]
        report, _ = self.report(rows)
        self.assertEqual(report["warnings"], [
            "Input Input-D1 Appears In Splits develop And select. "
            "Keep Each Input In One Split So Selection Does Not Reuse Development Cases."
        ])

    def test_input_in_every_split_gives_one_warning(self):
        rows = split_rows(develop=[4], select=[4], final=[3, 3, 3])
        rows[0]["input_ref"] = rows[1]["input_ref"] = rows[2]["input_ref"]
        report, _ = self.report(rows)
        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("Input Input-F1 Appears In Splits develop And select And final.", report["warnings"][0])

    def test_warnings_list_inputs_in_sorted_order(self):
        rows = split_rows(develop=[4, 4], final=[3, 3, 3])
        rows[0]["input_ref"], rows[1]["input_ref"] = rows[3]["input_ref"], rows[2]["input_ref"]
        report, _ = self.report(rows)
        self.assertEqual([text.split()[1] for text in report["warnings"]], ["Input-F1", "Input-F2"])

    def test_input_repeated_inside_one_split_is_rejected(self):
        rows = split_rows(final=[3, 3, 3])
        rows[1]["input_ref"] = rows[0]["input_ref"]
        self.rejected(rows, DISTINCT_IN_SPLIT)

    def test_pair_labels_stay_unique_across_splits(self):
        rows = split_rows(develop=[3], final=[3, 3, 3])
        rows[0]["pair"] = "F1"
        self.rejected(rows, DISTINCT_IN_SPLIT)

    def test_split_values_are_exact(self):
        for value in ("Final", "FINAL", "test", "holdout"):
            with self.subTest(value=value):
                rows = split_rows(final=[3, 3, 3])
                rows[0]["split"] = value
                self.rejected(rows, "Split Must Be develop, select, Or final On CSV Line 2")
        rows = split_rows(final=[3, 3, 3])
        rows[2]["split"] = " "
        self.rejected(rows, "Missing Or Extra Values On CSV Line 4")

    def test_split_column_may_sit_anywhere(self):
        rows = split_rows(final=[3, 2, 1])
        for columns in (list(compare.COLUMNS) + ["split"], ["split"] + list(compare.COLUMNS)):
            with self.subTest(columns=columns[0]):
                report, _ = self.report(rows, columns=columns)
                self.assertEqual((report["decision"], report["median_gain"]), (MEETS, "2"))

    def test_table_of_only_final_rows_matches_the_plain_decision(self):
        breach = [row("P4", 20, 10, guards=(0, 1))]
        tables = (rows_with_gains([3, 2, 1]), rows_with_gains([1, 1, 1]), rows_with_gains([5, 5]),
                  rows_with_gains([0, 0, 0]), rows_with_gains([4, 4, 4]) + breach)
        for plain_rows in tables:
            with self.subTest(gains=[item["candidate"] for item in plain_rows]):
                plain, _ = self.report(plain_rows)
                final, errors = self.report([dict(item, split="final") for item in plain_rows])
                for key in ["decision"] + SUMMARY_KEYS[:-1]:
                    self.assertEqual(final[key], plain[key], key)
                self.assertEqual((final["warnings"], errors), ([], ""))

    def test_each_trial_row_names_its_split(self):
        report, _ = self.report(split_rows(develop=[4], select=[3], final=[3, 3, 3]))
        self.assertEqual({trial["split"] for trial in report["trials"]}, {"final"})
        for name in ("develop", "select"):
            rows = report["other_splits"][name]["trials"]
            self.assertEqual([trial["split"] for trial in rows], [name])


class ModuleInterface(Base):
    def test_read_trials_returns_a_list_and_compare_infers_splits(self):
        plan = compare.read_plan(self.save_plan())
        plain = compare.read_trials(self.save_trials(rows_with_gains([3, 2, 1])), plan)
        self.assertIsInstance(plain, list)
        self.assertEqual(list(compare.compare(plan, plain)), LEGACY_KEYS)
        trials, has_split = compare.load_trials(self.save_trials(split_rows(final=[3, 2, 1])), plan)
        self.assertTrue(has_split)
        self.assertEqual(list(compare.compare(plan, trials)), SPLIT_KEYS)
        self.assertEqual(list(compare.compare(plan, [])), LEGACY_KEYS)
        self.assertEqual(list(compare.compare(plan, [], has_split=True)), SPLIT_KEYS)

    def test_help_names_the_optional_split_column(self):
        result = run_script("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("split", result.stdout)
        for name in compare.SPLITS:
            self.assertIn(name, result.stdout)


if __name__ == "__main__":
    unittest.main()
