"""Check That The Skill's Guides, Links, Examples, And Record Template Are Intact."""

from pathlib import Path
import re
import unittest
from urllib.parse import unquote


SKILL_FOLDER = Path(__file__).resolve().parents[1]
SKILL = "rsi"
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
REQUIRED_FILES = (
    "SKILL.md",
    "assets/example-plan.json",
    "assets/example-trials.csv",
    "assets/example-split-trials.csv",
    "assets/experiment-record.md",
    "scenarios/README.md",
    "scenarios/scenarios.json",
    "scripts/compare.py",
    "scripts/check_scenarios.py",
)
DECISIONS = ("Revise Candidate", "Collect More Pairs", "Candidate Meets Trial Criteria", "Keep Baseline")
RECORD_SECTIONS = (
    "Target And Versions", "Authorization And Bounds", "Evidence And Diagnosis", "Prediction",
    "Candidate Diff", "Case Split", "Settings And Scoring", "Commands", "Outcomes", "Cost",
    "Decision", "Adoption And Rollback",
)


def guides():
    return sorted(SKILL_FOLDER.rglob("*.md"))


def front_matter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key, colon, value = line.partition(":")
        if colon:
            fields[key.strip()] = value.strip()
    return {}


class SkillFiles(unittest.TestCase):
    def setUp(self):
        self.guide = (SKILL_FOLDER / "SKILL.md").read_text(encoding="utf-8")

    def test_required_files_exist(self):
        for name in REQUIRED_FILES:
            self.assertTrue((SKILL_FOLDER / name).is_file(), name)

    def test_front_matter_names_the_skill(self):
        fields = front_matter(self.guide)
        self.assertEqual(sorted(fields), ["description", "name"])
        self.assertEqual(fields["name"], SKILL)
        description = fields["description"]
        self.assertTrue(0 < len(description) <= 1024, len(description))
        self.assertNotIn(": ", description)
        for phrase in ("Skills, Instructions, Tools, Or Process", "The Model Stays The Same"):
            self.assertIn(phrase, description)

    def test_relative_links_resolve(self):
        checked = 0
        for guide in guides():
            for target in LINK.findall(guide.read_text(encoding="utf-8")):
                if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
                    continue
                path = (guide.parent / unquote(target.split("#")[0])).resolve()
                if SKILL_FOLDER not in path.parents:
                    sibling = SKILL_FOLDER.parent / path.relative_to(SKILL_FOLDER.parent).parts[0]
                    if not sibling.exists():
                        continue
                self.assertTrue(path.exists(), f"{guide.name} Links To A Missing File: {target}")
                checked += 1
        self.assertGreater(checked, 0)

    def test_guide_links_the_helper_examples_template_and_scenarios(self):
        for target in ("scripts/compare.py", "assets/example-plan.json", "assets/example-trials.csv",
                       "assets/example-split-trials.csv", "assets/experiment-record.md",
                       "scenarios/README.md", "../reflect/SKILL.md"):
            self.assertIn(f"]({target})", self.guide)

    def test_guide_states_what_the_skill_does_not_supply(self):
        self.assertIn("It Does Not Run Tasks For You, Isolate Them, Schedule Them, Or Limit What They Spend.", self.guide)
        self.assertIn("Does Not Show Better Task Performance.", self.guide)

    def test_guide_keeps_the_owner_review_rule(self):
        self.assertIn(
            "The Project Owner Personally Reviews The Editable Project And Approves "
            "Before Any Video Export, Including Test Or Preview Files.", self.guide)

    def test_guide_documents_every_helper_decision_and_split(self):
        helper = (SKILL_FOLDER / "scripts" / "compare.py").read_text(encoding="utf-8")
        for decision in DECISIONS:
            self.assertIn(f'"{decision}"', helper)
            self.assertIn(f"`{decision}`", self.guide)
        for name in ("develop", "select", "final"):
            self.assertIn(f"`{name}`", self.guide)

    def test_record_template_has_every_promised_section(self):
        record = (SKILL_FOLDER / "assets" / "experiment-record.md").read_text(encoding="utf-8")
        headings = [line[3:].strip() for line in record.splitlines() if line.startswith("## ")]
        self.assertEqual(headings, list(RECORD_SECTIONS))
        self.assertIn("Rollback Pointer", record)
        self.assertIn("Keep Private Traces Local", record)


if __name__ == "__main__":
    unittest.main()
