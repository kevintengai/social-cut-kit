"""Exercise The Scenario Validator And The Bundled Scenario File With Temporary Files."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_FOLDER = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_FOLDER / "scripts" / "check_scenarios.py"
BUNDLED = SKILL_FOLDER / "scenarios" / "scenarios.json"
SKILL = "rsi"
MINIMUM_SCENARIOS = 6
REQUIRED_NAMES = (
    "skill_never_loaded",
    "final_cases_leaked_into_tuning",
    "candidate_changed_the_grader",
    "adoption_limited_to_local_copy",
    "agent_judge_is_not_user_taste",
    "improver_claim_without_downstream_proof",
)

SPEC = importlib.util.spec_from_file_location(f"{SKILL}_check_scenarios", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def scenario(identifier, name):
    return {
        "id": identifier,
        "name": name,
        "request": "Review The Synthetic Session.",
        "session": "A Short Synthetic Session With One Correction.",
        "feedback": "That Matches What I Saw.",
        "checks": [
            "Shows The First Behavior.",
            "Shows The Second Behavior.",
            "Shows The Third Behavior.",
        ],
    }


def sample():
    return {"skill": SKILL, "scenarios": [scenario(1, "first_case"), scenario(2, "second_case")]}


class BundledFile(unittest.TestCase):
    def setUp(self):
        self.data = checker.load(BUNDLED)

    def test_bundled_file_has_no_problems(self):
        self.assertEqual(checker.find_problems(self.data, SKILL, MINIMUM_SCENARIOS), [])

    def test_bundled_file_names_the_skill_it_ships_in(self):
        self.assertEqual(self.data["skill"], SKILL)
        self.assertEqual(checker.skill_name(), SKILL)

    def test_bundled_file_covers_the_required_situations(self):
        names = [item["name"] for item in self.data["scenarios"]]
        self.assertGreaterEqual(len(names), MINIMUM_SCENARIOS)
        for name in REQUIRED_NAMES:
            self.assertIn(name, names)

    def test_bundled_ids_count_up_from_one(self):
        ids = [item["id"] for item in self.data["scenarios"]]
        self.assertEqual(ids, list(range(1, len(ids) + 1)))


class ShapeRules(unittest.TestCase):
    def problems(self, data, skill=SKILL, minimum=1):
        return checker.find_problems(data, skill, minimum)

    def assert_problem(self, data, fragment, **options):
        found = self.problems(data, **options)
        self.assertTrue(any(fragment in problem for problem in found), found)

    def test_sound_sample_passes(self):
        self.assertEqual(self.problems(sample()), [])

    def test_top_level_must_be_an_object(self):
        for value in ([], "Text", 3, None):
            self.assertEqual(
                self.problems(value), ["Top Level Must Be An Object With skill And scenarios"]
            )

    def test_top_level_fields_are_exact(self):
        for field in ("skill", "scenarios"):
            data = sample()
            del data[field]
            self.assert_problem(data, f"Top Level Is Missing The Field {field}")
        data = sample()
        data["notes"] = "Extra"
        self.assert_problem(data, "Top Level Has An Unexpected Field notes")

    def test_skill_label_must_match(self):
        data = sample()
        data["skill"] = "other-skill"
        self.assert_problem(data, f"Top Level Field skill Must Be {SKILL}, Found other-skill")
        self.assertEqual(self.problems(data, skill="other-skill"), [])
        for value in ("", "   ", 7, None):
            data["skill"] = value
            self.assert_problem(data, "Top Level Field skill Must Be Non-Empty Text")

    def test_default_skill_label_comes_from_the_skill_folder(self):
        self.assertEqual(checker.find_problems(sample()), [])
        with tempfile.TemporaryDirectory() as folder:
            bare = Path(folder) / "sample-skill"
            bare.mkdir()
            self.assertEqual(checker.skill_name(bare), "sample-skill")
            (bare / "SKILL.md").write_text(
                "---\nname: named-skill\ndescription: A Synthetic Skill.\n---\n", encoding="utf-8"
            )
            self.assertEqual(checker.skill_name(bare), "named-skill")
            (bare / "SKILL.md").write_text("No Front Matter Here.\n", encoding="utf-8")
            self.assertEqual(checker.skill_name(bare), "sample-skill")

    def test_scenarios_must_be_a_list_of_objects(self):
        data = sample()
        data["scenarios"] = {"first": scenario(1, "first_case")}
        self.assert_problem(data, "Top Level Field scenarios Must Be A List")
        data = sample()
        data["scenarios"].append("Not An Object")
        self.assert_problem(data, "Scenario 3 Must Be An Object")

    def test_minimum_count_is_enforced_on_request(self):
        self.assertEqual(self.problems(sample(), minimum=2), [])
        self.assert_problem(sample(), "Expected At Least 3 Scenarios, Found 2", minimum=3)
        empty = {"skill": SKILL, "scenarios": []}
        self.assert_problem(empty, "Expected At Least 1 Scenario, Found 0")
        self.assertEqual(self.problems(empty, minimum=0), [])

    def test_every_scenario_field_is_required(self):
        for field in checker.SCENARIO_FIELDS:
            data = sample()
            del data["scenarios"][1][field]
            self.assert_problem(data, f"Is Missing The Field {field}")

    def test_unexpected_scenario_field_is_reported(self):
        data = sample()
        data["scenarios"][0]["check"] = ["A Misspelled Field Name."]
        self.assert_problem(data, "Scenario 1 (first_case) Has An Unexpected Field check")

    def test_ids_must_be_positive_whole_numbers(self):
        for value in ("1", 1.0, 1.5, True, 0, -3, None, [1]):
            data = sample()
            data["scenarios"][0]["id"] = value
            self.assert_problem(data, "Field id Must Be A Positive Whole Number")

    def test_ids_must_be_unique(self):
        data = sample()
        data["scenarios"][1]["id"] = 1
        self.assert_problem(data, "Scenario 2 (second_case) Repeats The id 1 Used By Scenario 1")

    def test_names_must_be_snake_case(self):
        for value in ("CamelCase", "has space", "trailing_", "_leading", "double__gap",
                      "kebab-case", "9starts_with_digit", "", "   ", 5, None):
            data = sample()
            data["scenarios"][0]["name"] = value
            self.assert_problem(data, "Field name Must Be snake_case")
        for value in ("a", "rule_2_ignored", "x9"):
            data = sample()
            data["scenarios"][0]["name"] = value
            self.assertEqual(self.problems(data), [])

    def test_names_must_be_unique(self):
        data = sample()
        data["scenarios"][1]["name"] = "first_case"
        self.assert_problem(data, "Repeats The name first_case Used By Scenario 1")

    def test_text_fields_must_be_filled(self):
        for field in checker.TEXT_FIELDS:
            for value in ("", " \n\t ", 12, None, ["Text In A List"]):
                data = sample()
                data["scenarios"][0][field] = value
                self.assert_problem(data, f"Field {field} Must Be Non-Empty Text")

    def test_checks_must_be_a_list_of_three_to_six(self):
        data = sample()
        data["scenarios"][0]["checks"] = "One Long Sentence."
        self.assert_problem(data, "Field checks Must Be A List")
        for size in (0, 2, 7):
            data = sample()
            data["scenarios"][0]["checks"] = [f"Shows Behavior {n}." for n in range(size)]
            self.assert_problem(data, f"Needs 3 To 6 Checks, Found {size}")
        for size in (3, 6):
            data = sample()
            data["scenarios"][0]["checks"] = [f"Shows Behavior {n}." for n in range(size)]
            self.assertEqual(self.problems(data), [])

    def test_each_check_must_be_filled_and_distinct(self):
        data = sample()
        data["scenarios"][0]["checks"][1] = "  "
        self.assert_problem(data, "Check 2 Must Be Non-Empty Text")
        data = sample()
        data["scenarios"][0]["checks"][2] = 3
        self.assert_problem(data, "Check 3 Must Be Non-Empty Text")
        data = sample()
        data["scenarios"][0]["checks"][2] = data["scenarios"][0]["checks"][0] + " "
        self.assert_problem(data, "Check 3 Repeats An Earlier Check")

    def test_all_problems_are_reported_together(self):
        data = sample()
        data["scenarios"][0]["id"] = 2
        data["scenarios"][0]["request"] = ""
        data["scenarios"][1]["checks"] = []
        found = self.problems(data)
        self.assertEqual(len(found), 3, found)


class FileLoading(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.work = Path(folder.name)

    def write(self, text, name="scenarios.json", encoding="utf-8"):
        path = self.work / name
        path.write_bytes(text.encode(encoding))
        return path

    def test_reads_utf8_with_or_without_a_byte_order_mark(self):
        text = json.dumps(sample(), ensure_ascii=False)
        self.assertEqual(checker.load(self.write(text)), sample())
        self.assertEqual(checker.load(self.write(text, encoding="utf-8-sig")), sample())

    def test_invalid_json_names_the_position(self):
        with self.assertRaises(ValueError) as caught:
            checker.load(self.write('{"skill": "sample",\n "scenarios": [}'))
        self.assertIn("Not Valid JSON At Line 2", str(caught.exception))

    def test_repeated_field_in_one_object_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            checker.load(self.write('{"skill": "a", "skill": "b", "scenarios": []}'))
        self.assertIn("Field skill Appears More Than Once", str(caught.exception))

    def test_missing_file_and_wrong_encoding_are_reported(self):
        with self.assertRaises(ValueError) as caught:
            checker.load(self.work / "absent.json")
        self.assertIn("Could Not Be Read", str(caught.exception))
        path = self.work / "latin.json"
        path.write_bytes(b'{"skill": "caf\xe9"}')
        with self.assertRaises(ValueError) as caught:
            checker.load(path)
        self.assertIn("Not UTF-8 Text", str(caught.exception))


class CommandLine(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.work = Path(folder.name)

    def cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), *map(str, args)],
            capture_output=True, encoding="utf-8", errors="replace", cwd=str(self.work), check=False,
        )

    def save(self, data):
        path = self.work / "candidate.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_bundled_file_passes_from_any_working_folder(self):
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"For {SKILL}. No Problems Found.", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_bundled_file_meets_the_product_minimum(self):
        result = self.cli("--minimum", MINIMUM_SCENARIOS)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_sound_file_at_a_given_path_passes(self):
        result = self.cli(self.save(sample()))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), f"Checked 2 Scenarios For {SKILL}. No Problems Found.")

    def test_problems_exit_one_and_go_to_standard_error(self):
        data = sample()
        data["scenarios"][1]["id"] = 1
        data["scenarios"][1]["feedback"] = ""
        result = self.cli(self.save(data))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("Repeats The id 1 Used By Scenario 1", result.stderr)
        self.assertIn("Field feedback Must Be Non-Empty Text", result.stderr)
        self.assertIn("Found 2 Problems In", result.stderr)

    def test_options_change_the_expected_skill_and_minimum(self):
        path = self.save(sample())
        self.assertEqual(self.cli(path, "--skill", "other-skill").returncode, 1)
        self.assertEqual(self.cli(path, "--minimum", 2).returncode, 0)
        result = self.cli(path, "--minimum", 3)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Expected At Least 3 Scenarios, Found 2", result.stderr)

    def test_unreadable_input_exits_one(self):
        result = self.cli(self.work / "absent.json")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Scenario File Could Not Be Read", result.stderr)
        broken = self.work / "broken.json"
        broken.write_text("{", encoding="utf-8")
        result = self.cli(broken)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Scenario File Is Not Valid JSON", result.stderr)

    def test_main_returns_exit_codes_in_process(self):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(checker.main([str(self.save(sample()))]), 0)
            self.assertEqual(checker.main([str(self.work / "absent.json")]), 1)
            with self.assertRaises(SystemExit) as stopped:
                checker.main(["--minimum", "-1"])
        self.assertEqual(stopped.exception.code, 2)
        self.assertIn("No Problems Found.", output.getvalue())
        self.assertIn("Enter A Nonnegative Whole Number For --minimum", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
