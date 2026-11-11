"""Check That The Skill's Guides, Links, And Agent Settings Are Intact."""

from pathlib import Path
import re
import unittest
from urllib.parse import unquote


SKILL_FOLDER = Path(__file__).resolve().parents[1]
SKILL = "reflect"
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
REQUIRED_FILES = (
    "SKILL.md",
    "CUT-REVIEW.md",
    "agents/openai.yaml",
    "scenarios/README.md",
    "scenarios/scenarios.json",
    "scripts/check_scenarios.py",
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
    def test_required_files_exist(self):
        for name in REQUIRED_FILES:
            self.assertTrue((SKILL_FOLDER / name).is_file(), name)

    def test_front_matter_names_the_skill_and_both_uses(self):
        fields = front_matter((SKILL_FOLDER / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(sorted(fields), ["description", "name"])
        self.assertEqual(fields["name"], SKILL)
        description = fields["description"]
        self.assertTrue(0 < len(description) <= 1024, len(description))
        self.assertNotIn(": ", description)
        for word in ("Session", "Cut"):
            self.assertIn(word, description)

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

    def test_session_guide_links_the_cut_review_and_the_trial_skill(self):
        text = (SKILL_FOLDER / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("](CUT-REVIEW.md)", text)
        self.assertIn("](../rsi/SKILL.md)", text)
        self.assertIn("](scenarios/README.md)", text)

    def test_codex_policy_file_is_exact(self):
        text = (SKILL_FOLDER / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertTrue(text.endswith("policy:\n  allow_implicit_invocation: false\n"))

    def test_guides_keep_the_owner_review_rule(self):
        session = (SKILL_FOLDER / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Never Authorizes", session)
        self.assertIn("Has Personally Reviewed The Editable Project And Approved", session)
        cut = (SKILL_FOLDER / "CUT-REVIEW.md").read_text(encoding="utf-8")
        self.assertIn("Before Any Video Export", cut)

    def test_cut_review_keeps_its_procedure_and_handoff_table(self):
        cut = (SKILL_FOLDER / "CUT-REVIEW.md").read_text(encoding="utf-8")
        for heading in ("## Review A Cut", "## Editor Handoff"):
            self.assertIn(heading, cut)
        steps = [line for line in cut.splitlines() if re.match(r"\d+\. ", line)]
        self.assertEqual(len(steps), 5)
        self.assertIn("| Timeline Or Source | Direct Observation | Effect | Revision To Try | Acceptance Check |", cut)


if __name__ == "__main__":
    unittest.main()
