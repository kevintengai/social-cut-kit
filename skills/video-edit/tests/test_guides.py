"""The Guides: House Style, Working Links, And Command Examples That Match The Real Parsers."""

import contextlib
import io
import json
import re
import shlex
import sys
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import defaults
import edit_video
import setup_check
import speech
import takes

GUIDES = ["SKILL.md", "SPEECH.md", "TECHNICAL.md", "TITLES.md", "RECREATION.md", "CAMERA.md", "RESOLVE.md",
          "PUBLISH.md", "INSERTS.md", "assets/cue-bank/README.md", "remotion/README.md"]
# Units And Product Names Keep Their Own Spelling Inside Title Case Prose.
SPELLED = {"dB", "dBFS", "dBTP", "kHz", "macOS"}
WORKFLOWS = {"setup": setup_check.parser, "defaults": defaults.parser}


def prose(text):
    """Guide Text With Code, Link Targets, And Markup Removed."""
    # The Front Matter Name Is An Identifier. Its Description Is Prose.
    text = re.sub(r"\A---\nname: [\w-]+\ndescription: ", "---\n", text)
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"\]\([^)]*\)", "] ", text)
    return re.sub(r"<[^>]+>", " ", text)


def anchors(text):
    found = set()
    for heading in re.findall(r"^#{1,6}\s+(.*?)\s*$", re.sub(r"```.*?```", "", text, flags=re.S), flags=re.M):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        found.add(slug)
    return found


def commands(text):
    """Python Command Lines From Fenced Blocks And Inline Code."""
    lines = []
    for block in re.findall(r"```(?:sh|shell|text|powershell)\n(.*?)```", text, flags=re.S):
        lines += [line.strip() for line in block.splitlines()]
    lines += re.findall(r"`(python [^`\n]+)`", text)
    return [line for line in lines if re.search(r"\S+\.py\b", line) and "python" in line.lower()]


MESSAGE_FILES = ["scripts/setup_check.py", "scripts/defaults.py", "scripts/loudness.py", "scripts/media.py",
                 "scripts/timeline.py", "scripts/edit_video.py", "scripts/speech.py", "assets/cue-bank/build.py",
                 "scripts/working_copy.py", "scripts/takes.py"]
# Program, Filter, Package, And Literal Value Names That Appear Inside Messages.
NAMED = SPELLED | {"zscale", "tonemap", "libzimg", "libass", "ebur128", "pip", "ensurepip", "whisper", "faster",
                   "true", "false", "refuse", "cap", "bt2020"}
SCRIPT_FILES = ["remotion/cut-plan.cjs", "remotion/prepare-remotion.cjs", "remotion/render-reviewed.cjs"]
# Command Words That Appear Inside Node Messages As Typed.
TYPED = NAMED | {"node", "npm", "install", "run", "studio", "ffprobe"}


class MessageTests(unittest.TestCase):
    def test_help_text_and_messages_are_capitalized(self):
        import ast
        checked = 0
        for name in MESSAGE_FILES:
            tree = ast.parse((SKILL / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    text = node.value
                elif isinstance(node, ast.JoinedStr):
                    text = "".join(part.value if isinstance(part, ast.Constant) else " X " for part in node.values)
                else:
                    continue
                # Prose Has A Space And Two Capitalized Words In A Row. Filter Graphs And Keys Do Not.
                if " " not in text.strip() or not re.search(r"[A-Z][a-z]+ [A-Z]", text):
                    continue
                checked += 1
                for token in text.split():
                    bare = token.strip("\"'()[]{}*.,:;!?|#>+=&%")
                    # Option Names, Field Names, File Names, And Web Addresses Keep Their Own Spelling.
                    if bare.startswith("--") or "_" in bare or re.search(r"\w\.\w", bare):
                        continue
                    for part in re.split(r"[-/]", bare):
                        if part and part[0].isalpha() and part not in NAMED:
                            self.assertFalse(part[0].islower(), f"{name} Line {node.lineno}: {part!r} In {text.strip()[:90]!r}")
        self.assertGreater(checked, 150)

    def test_remotion_adapter_messages_are_capitalized(self):
        checked = 0
        for name in SCRIPT_FILES:
            source = (SKILL / name).read_text(encoding="utf-8")
            source = re.sub(r"^\s*//.*$", "", source, flags=re.M)
            for quote, body in re.findall(r"""(["`])((?:\\.|(?!\1).)*)\1""", source):
                text = re.sub(r"\$\{[^}]*\}", " X ", body) if quote == "`" else body
                # A Font Stack Is A Literal CSS Value, Not A Message.
                if " " not in text.strip() or not re.search(r"[A-Z][a-z]+ [A-Z]", text) or "serif" in text:
                    continue
                checked += 1
                for token in text.split():
                    bare = token.strip("\"'()[]{}*.,:;!?|#>+=&%")
                    if bare.startswith("--") or "_" in bare or re.search(r"\w\.\w", bare):
                        continue
                    for part in re.split(r"[-/]", bare):
                        if part and part[0].isalpha() and part not in TYPED:
                            self.assertFalse(part[0].islower(), f"{name}: {part!r} In {text.strip()[:90]!r}")
        self.assertGreater(checked, 60)

    def test_every_option_has_capitalized_help(self):
        parsers = [edit_video.parser(), speech.build_parser(), setup_check.parser(), defaults.parser(), takes.build_parser()]
        seen = 0
        while parsers:
            current = parsers.pop()
            for action in current._actions:
                if getattr(action, "choices", None) and isinstance(action.choices, dict):
                    parsers.extend(action.choices.values())
                    for choice in action._choices_actions:
                        self.assertTrue(choice.help and choice.help[0].isupper(), choice.dest)
                if action.option_strings and action.help and "show this help" not in action.help:
                    seen += 1
                    tokens = [token for token in action.help.split() if not token.startswith("--")]
                    words = [word for token in tokens for word in token.split("-") if word[:1].isalpha()]
                    lowered = [word for word in words if word[0].islower() and word.strip(".,") not in NAMED]
                    self.assertFalse(lowered, f"{action.option_strings[0]}: {action.help}")
        self.assertGreaterEqual(seen, 30)


class GuideTests(unittest.TestCase):
    def read(self, name):
        return (SKILL / name).read_text(encoding="utf-8")

    def test_every_prose_word_is_capitalized(self):
        for name in GUIDES:
            for number, line in enumerate(prose(self.read(name)).splitlines(), 1):
                for token in line.split():
                    for part in re.split(r"[-/—–]", token):
                        word = part.strip("\"'“”‘’()[]{}*_.,:;!?|#>+=&×−")
                        if word in SPELLED or not word or not word[0].isalpha():
                            continue
                        self.assertFalse(word[0].islower(), f"{name} Line {number}: {word!r} In {line.strip()[:90]!r}")

    def test_guides_avoid_marketing_marks(self):
        emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
        for name in GUIDES:
            text = prose(self.read(name))
            self.assertNotIn("!", text.replace("!\"", ""), name)
            self.assertIsNone(emoji.search(text), name)

    def test_relative_links_and_anchors_resolve(self):
        for name in GUIDES:
            text = self.read(name)
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if re.match(r"[a-z]+://", target):
                    continue
                path, _, anchor = target.partition("#")
                file = ((SKILL / name).parent / path.replace("%20", " ")).resolve() if path else SKILL / name
                # A Link To A Sibling Skill Resolves Only When That Skill Is Installed Beside This One.
                if SKILL not in file.parents and not file.exists():
                    continue
                with self.subTest(guide=name, link=target):
                    self.assertTrue(file.exists(), f"{name} Links To Missing {target}")
                    if anchor:
                        self.assertIn(anchor, anchors(file.read_text(encoding="utf-8")))

    def test_skill_entry_points_to_every_guide_and_states_the_rules(self):
        text = self.read("SKILL.md")
        front = re.match(r"---\nname: video-edit\ndescription: (.+)\n---\n", text)
        self.assertIsNotNone(front)
        for topic in ("Saved User Defaults", "Brief", "Style", "Phrase", "HDR", "Loudness", "Resolve", "Remotion", "Posting"):
            self.assertIn(topic, front[1])
        for guide in ("BRIEF.md", "STYLES.md", "TECHNICAL.md", "SPEECH.md", "TITLES.md", "RECREATION.md", "CAMERA.md",
                      "RESOLVE.md", "PUBLISH.md", "INSERTS.md", "assets/cue-bank/README.md", "remotion/README.md", "../reflect/SKILL.md"):
            self.assertIn(f"]({guide}", text)
        for rule in ("~/.social-cut-kit/video-edit.md", "Begin Your First Reply By Listing, In A Single Line, The Saved Defaults In Use",
                     "Current Instructions Always Override Stored Defaults", "Offer To Record It",
                     "Show A Command To The User And Run It Only After They Agree",
                     "Have Its Owner Personally Review This Version In The Editor",
                     "Including Preview Or Test Files", "--owner-approved", "Stays As Recorded By Default",
                     "Remotion Is The Default Route For Owner Review And The Finished Video",
                     "Remain The Way To Verify An Edit Before Approval", "Needs No Node Packages",
                     "Each Generated Project Needs Node.js And Its Own `npm install`", "Remotion Has Its Own License Terms",
                     "npm run studio", "npm run render-reviewed", "Neither Asks For Approval",
                     "Sound In The Remotion Route Has Not Been Verified"):
            self.assertIn(rule, text)
        brief = next(line for line in text.splitlines() if "](BRIEF.md)" in line)
        styles = next(line for line in text.splitlines() if "](STYLES.md)" in line and line.startswith("Read"))
        self.assertTrue(brief.startswith("Read [The Brief Guide](BRIEF.md) Before"))
        self.assertTrue(styles.startswith("Read [The Style Index](STYLES.md) Before"))
        reflection = text[text.index("## After The Edit"):text.index("## Verification")]
        for place in ("Reflect Skill", "This File", "Style's Guide", "Technical Reference", "Defaults File"):
            self.assertIn(place, reflection)

    def test_remotion_route_is_the_default_and_states_its_limits(self):
        text = self.read("SKILL.md")
        delivery = text[text.index("## Approved Delivery"):text.index("## After The Edit")]
        self.assertLess(delivery.index("edit_video.py remotion"), delivery.index("edit_video.py render"))
        self.assertLess(delivery.index("Owner Review."), delivery.index("npm run render-reviewed"))
        for check in ("`validate`", "`check`", "`still`", "`loudness`", "`mix`"):
            self.assertIn(check, delivery[:delivery.index("1. **Verify The Edit.**")])
        guide = self.read("remotion/README.md")
        for heading in ("### HDR Sources", "### Speed Changes And Pitch", "### Caption Fonts", "### Media Formats"):
            self.assertIn(heading, guide)
        for rule in ("It Never Writes A Video", "Sound In The Remotion Route Is Unverified", "Preparation Refuses A Timeline",
                     "Keeps The Pitch", "Falls Back To Another Font Without A Message", "Type APPROVE",
                     "Refuses To Replace An Existing File", "Neither Asks For Approval",
                     "Before Any Video Export, Including Test And Preview Exports",
                     "Each Generated Project Needs Node.js And Its Own `npm install`", "Remotion Has Its Own License Terms"):
            self.assertIn(rule, guide)
        # The Product Overview And Start Sheet Sit Above The Skills In The Download. An Installed Skill Has Neither.
        for name in ("README.md", "START-HERE.md"):
            sheet = SKILL.parents[1] / name
            if sheet.is_file() and (SKILL.parents[1] / "install.py").is_file():
                page = sheet.read_text(encoding="utf-8")
                with self.subTest(sheet=name):
                    self.assertIn("](skills/video-edit/remotion/README.md)", page)
                    self.assertIn("Remotion Has Its Own License Terms", page)
                    self.assertIn("Its Own `npm install`", page)

    def test_counts_in_the_guides_match_the_sound_index(self):
        count = len(json.loads((SKILL / "assets/cue-bank/sounds/index.json").read_text(encoding="utf-8")))
        self.assertIn(f"Holds {count} Original Sounds", self.read("SKILL.md"))
        self.assertIn(f"These {count} Original Synthesized Sounds", self.read("assets/cue-bank/README.md"))
        readme = self.read("assets/cue-bank/README.md")
        names = {record["file"][:-4] for record in json.loads((SKILL / "assets/cue-bank/sounds/index.json").read_text(encoding="utf-8"))}
        table = readme[readme.index("| You Need |"):readme.index("One Cue Per Event")]
        listed = set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", table))
        self.assertTrue(listed <= names, listed - names)
        self.assertGreaterEqual(len(listed), 45)

    def test_command_examples_use_real_scripts_subcommands_and_options(self):
        seen = 0
        for name in GUIDES:
            for line in commands(self.read(name)):
                tokens = shlex.split(line.lstrip("& "))
                index = next(i for i, token in enumerate(tokens) if token.endswith(".py"))
                script = tokens[index].replace("skills/video-edit/", "")
                base = SKILL / "assets/cue-bank" if script == "build.py" else SKILL
                arguments = tokens[index + 1:]
                with self.subTest(guide=name, command=line):
                    self.assertTrue((base / script).is_file(), f"Missing Script In {line}")
                    seen += 1
                    quiet = io.StringIO()
                    with contextlib.redirect_stderr(quiet), contextlib.redirect_stdout(quiet):
                        try:
                            if script == "scripts/edit_video.py" and arguments and arguments[0] in WORKFLOWS:
                                WORKFLOWS[arguments[0]]().parse_args(arguments[1:])
                            elif script == "scripts/edit_video.py" and arguments and arguments[0] not in edit_video.WORKFLOWS:
                                edit_video.parser().parse_args(arguments)
                            elif script == "scripts/speech.py":
                                speech.build_parser().parse_args(arguments)
                            else:
                                source = (base / script).read_text(encoding="utf-8")
                                for option in (token for token in arguments if token.startswith("--") and token != "--help"):
                                    self.assertIn(f'"{option}"', source, f"{option} Is Not An Option Of {script}")
                                if script == "scripts/edit_video.py" and arguments:
                                    self.assertIn(arguments[0], edit_video.WORKFLOWS)
                        except SystemExit as stop:
                            self.assertEqual(stop.code, 0, f"The Parser Rejects {line}. {quiet.getvalue()[-300:]}")
        self.assertGreaterEqual(seen, 60)


if __name__ == "__main__":
    unittest.main()
