"""Check A Scenario File For Shape, Unique Ids And Names, And Filled Fields."""

import argparse
import json
from pathlib import Path
import re
import sys


SKILL_FOLDER = Path(__file__).resolve().parents[1]
DEFAULT_FILE = SKILL_FOLDER / "scenarios" / "scenarios.json"
TOP_FIELDS = ("skill", "scenarios")
SCENARIO_FIELDS = ("id", "name", "request", "session", "feedback", "checks")
TEXT_FIELDS = ("request", "session", "feedback")
MINIMUM_CHECKS = 3
MAXIMUM_CHECKS = 6
SNAKE_CASE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")


def skill_name(folder=SKILL_FOLDER):
    """Return The name In The Skill's Front Matter, Or The Folder Name Without One."""
    try:
        lines = (Path(folder) / "SKILL.md").read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError):
        return Path(folder).name
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, colon, value = line.partition(":")
            value = value.strip().strip("'\"").strip()
            if colon and key.strip() == "name" and value:
                return value
    return Path(folder).name


def count(number, noun):
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def unique_fields(pairs):
    record = {}
    for key, value in pairs:
        if key in record:
            raise ValueError(f"Field {key} Appears More Than Once In One Object")
        record[key] = value
    return record


def load(path):
    """Read A Scenario File. Raise ValueError With A Readable Message On Failure."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Scenario File Is Not UTF-8 Text: {path}") from exc
    except OSError as exc:
        raise ValueError(f"Scenario File Could Not Be Read: {path}") from exc
    try:
        return json.loads(text, object_pairs_hook=unique_fields)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Scenario File Is Not Valid JSON At Line {exc.lineno}, Column {exc.colno}"
        ) from exc


def filled(value):
    return isinstance(value, str) and bool(value.strip())


def check_problems(label, checks):
    if not isinstance(checks, list):
        return [f"{label} Field checks Must Be A List"]
    problems = []
    if not MINIMUM_CHECKS <= len(checks) <= MAXIMUM_CHECKS:
        problems.append(
            f"{label} Needs {MINIMUM_CHECKS} To {MAXIMUM_CHECKS} Checks, Found {len(checks)}"
        )
    seen = set()
    for number, check in enumerate(checks, 1):
        if not filled(check):
            problems.append(f"{label} Check {number} Must Be Non-Empty Text")
        elif check.strip() in seen:
            problems.append(f"{label} Check {number} Repeats An Earlier Check")
        else:
            seen.add(check.strip())
    return problems


def scenario_problems(scenarios):
    problems = []
    seen_ids = {}
    seen_names = {}
    for position, scenario in enumerate(scenarios, 1):
        label = f"Scenario {position}"
        if not isinstance(scenario, dict):
            problems.append(f"{label} Must Be An Object")
            continue
        name = scenario.get("name")
        if filled(name):
            label = f"{label} ({name.strip()})"
        for field in SCENARIO_FIELDS:
            if field not in scenario:
                problems.append(f"{label} Is Missing The Field {field}")
        for field in sorted(set(scenario) - set(SCENARIO_FIELDS)):
            problems.append(f"{label} Has An Unexpected Field {field}")
        if "id" in scenario:
            identifier = scenario["id"]
            if type(identifier) is not int or identifier < 1:
                problems.append(f"{label} Field id Must Be A Positive Whole Number")
            elif identifier in seen_ids:
                problems.append(
                    f"{label} Repeats The id {identifier} Used By Scenario {seen_ids[identifier]}"
                )
            else:
                seen_ids[identifier] = position
        if "name" in scenario:
            if not isinstance(name, str) or not SNAKE_CASE.fullmatch(name):
                problems.append(f"{label} Field name Must Be snake_case, Such As ignored_rule")
            elif name in seen_names:
                problems.append(
                    f"{label} Repeats The name {name} Used By Scenario {seen_names[name]}"
                )
            else:
                seen_names[name] = position
        for field in TEXT_FIELDS:
            if field in scenario and not filled(scenario[field]):
                problems.append(f"{label} Field {field} Must Be Non-Empty Text")
        if "checks" in scenario:
            problems.extend(check_problems(label, scenario["checks"]))
    return problems


def find_problems(data, skill=None, minimum=1):
    """Return Every Problem Found. An Empty List Means The File Is Sound."""
    expected = skill_name() if skill is None else skill
    if not isinstance(data, dict):
        return ["Top Level Must Be An Object With skill And scenarios"]
    problems = []
    for field in TOP_FIELDS:
        if field not in data:
            problems.append(f"Top Level Is Missing The Field {field}")
    for field in sorted(set(data) - set(TOP_FIELDS)):
        problems.append(f"Top Level Has An Unexpected Field {field}")
    if "skill" in data:
        if not filled(data["skill"]):
            problems.append("Top Level Field skill Must Be Non-Empty Text")
        elif data["skill"] != expected:
            problems.append(f"Top Level Field skill Must Be {expected}, Found {data['skill']}")
    if "scenarios" in data:
        scenarios = data["scenarios"]
        if not isinstance(scenarios, list):
            problems.append("Top Level Field scenarios Must Be A List")
        else:
            if len(scenarios) < minimum:
                problems.append(
                    f"Expected At Least {count(minimum, 'Scenario')}, Found {len(scenarios)}"
                )
            problems.extend(scenario_problems(scenarios))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path", nargs="?", type=Path, default=DEFAULT_FILE,
        help="Scenario File To Check. Defaults To scenarios/scenarios.json In This Skill Folder",
    )
    parser.add_argument(
        "--skill", metavar="NAME",
        help="Skill Name The File Must Declare. Defaults To The name In This Skill's SKILL.md",
    )
    parser.add_argument(
        "--minimum", type=int, default=1, metavar="COUNT",
        help="Smallest Acceptable Number Of Scenarios. Defaults To 1",
    )
    args = parser.parse_args(argv)
    if args.minimum < 0:
        parser.error("Enter A Nonnegative Whole Number For --minimum")
    try:
        data = load(args.path)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    problems = find_problems(data, args.skill, args.minimum)
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        print(f"Found {count(len(problems), 'Problem')} In {args.path}", file=sys.stderr)
        return 1
    print(f"Checked {count(len(data['scenarios']), 'Scenario')} For {data['skill']}. No Problems Found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
