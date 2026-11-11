"""Caption Defaults Follow The Canvas, Explicit Values Win, And Every Guide States The Same Numbers And Rules."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import speech
import timeline
from media import ass
from timeline import EditError, caption_style

NODE = shutil.which("node")
WORDS = [(0.0, 0.3, "Stop"), (0.3, 0.6, "quoting"), (0.6, 0.9, "by"), (0.9, 1.2, "the"), (1.2, 1.5, "hour"),
         (1.5, 1.8, "and"), (1.8, 2.1, "charge"), (2.1, 2.4, "for"), (2.4, 2.7, "the"), (2.7, 3.0, "result.")]


def edit(canvas=None):
    doc = {"version": 1, "title": "Captions", "assets": {"main": {"path": "camera.bin", "kind": "video"}},
           "shots": [{"asset": "main", "in": 0, "out": 3.2}]}
    if canvas is not None:
        doc["canvas"] = canvas
    return doc


def model(style, w=1080, h=1920, captions=()):
    return {"width": w, "height": h, "caption_style": caption_style({"caption_style": style} if style is not None else {}, w, h),
            "captions": list(captions)}


class StyleDefaultTests(unittest.TestCase):
    def test_vertical_canvas_defaults_match_the_safe_area_guidance(self):
        self.assertEqual(caption_style({}, 1080, 1920),
                         {"font": "Arial", "size": 65, "color": "#FFFFFF", "outline": "#101010", "stroke": 5,
                          "margin": 25, "top_margin": 12})
        self.assertEqual([caption_style({}, w, h)["size"] for w, h in ((720, 1280), (360, 640), (2160, 3840), (1080, 1350))],
                         [43, 22, 130, 65])
        self.assertEqual(caption_style({}, 100, 180)["size"], 12)

    def test_horizontal_and_square_canvases_keep_the_earlier_defaults(self):
        wide = caption_style({}, 1920, 1080)
        self.assertEqual((wide["size"], wide["stroke"], wide["margin"], wide["top_margin"]), (84, 6, 7, 7))
        square = caption_style({}, 1080, 1080)
        self.assertEqual((square["size"], square["margin"], square["top_margin"]), (84, 7, 7))

    def test_explicit_values_override_every_default(self):
        style = caption_style({"caption_style": {"size": 92, "margin": 7}}, 1080, 1920)
        self.assertEqual((style["size"], style["stroke"], style["margin"], style["top_margin"]), (92, 6, 7, 7))
        self.assertEqual(caption_style({"caption_style": {"margin": 30}}, 1080, 1920)["top_margin"], 30)
        both = caption_style({"caption_style": {"margin": 30, "top_margin": 10}}, 1080, 1920)
        self.assertEqual((both["margin"], both["top_margin"]), (30, 10))
        only_top = caption_style({"caption_style": {"top_margin": 20}}, 1080, 1920)
        self.assertEqual((only_top["margin"], only_top["top_margin"]), (25, 20))
        self.assertEqual(caption_style({"caption_style": {"top_margin": 3}}, 1920, 1080)["margin"], 7)
        for bad in ({"top_margin": 60}, {"top_margin": "12"}, {"bottom_margin": 5}):
            with self.assertRaises(EditError):
                caption_style({"caption_style": bad}, 1080, 1920)

    def test_a_timeline_with_explicit_style_renders_the_same_subtitle_file_as_before(self):
        cues = [{"at": 0, "end": 1, "text": "Low", "position": "bottom"}, {"at": 1, "end": 2, "text": "High", "position": "top"}]
        text = ass(model({"size": 92, "stroke": 6, "margin": 7}, captions=cues))
        legacy = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\n[V4+ Styles]\n"
                  "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
                  "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
                  "MarginR, MarginV, Encoding\n"
                  "Style: Default,Arial,92,&H00FFFFFF,&H00FFFFFF,&H00101010,&H00000000,-1,0,0,0,100,100,0,0,1,6,0,2,59,59,134,1\n"
                  "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
                  "Dialogue: 0,00:00:00.00,00:00:01.00,Default,,0,0,0,,{\\an2}Low\n"
                  "Dialogue: 0,00:00:01.00,00:00:02.00,Default,,0,0,0,,{\\an8}High\n")
        self.assertEqual(text, legacy)

    def test_default_vertical_captions_sit_clear_of_the_platform_edges(self):
        cues = [{"at": 0, "end": 1, "text": "Low", "position": "bottom"}, {"at": 1, "end": 2, "text": "High", "position": "top"},
                {"at": 2, "end": 3, "text": "Middle", "position": "center"}]
        lines = ass(model(None, captions=cues)).splitlines()
        styles = [line for line in lines if line.startswith("Style: ")]
        self.assertEqual([line.split(",")[0] for line in styles], ["Style: Default", "Style: Top"])
        self.assertEqual([line.split(",")[2] for line in styles], ["65", "65"])
        self.assertEqual([line.split(",")[-2] for line in styles], ["480", "230"])
        events = [line.split(",")[3] for line in lines if line.startswith("Dialogue: ")]
        self.assertEqual(events, ["Default", "Top", "Default"])


class PhraseDefaultTests(unittest.TestCase):
    def test_phrase_defaults_follow_the_canvas(self):
        tall = {"max_words": 3, "max_chars": 20, "pause": 0.4, "min_seconds": 0.3}
        wide = {"max_words": 4, "max_chars": 28, "pause": 0.4, "min_seconds": 0.3}
        self.assertEqual(speech.phrase_defaults(edit()), tall)
        self.assertEqual(speech.phrase_defaults(edit({"width": 1080, "height": 1920})), tall)
        self.assertEqual(speech.phrase_defaults(edit({"fps": 30})), tall)
        self.assertEqual(speech.phrase_defaults(edit({"width": 1920, "height": 1080})), wide)
        self.assertEqual(speech.phrase_defaults(edit({"width": 1080, "height": 1080})), wide)
        self.assertEqual(speech.phrase_defaults(), wide)
        self.assertEqual(speech.PHRASE_DEFAULTS, wide)

    def test_default_vertical_phrases_fit_the_middle_of_the_frame_on_one_line(self):
        # At The Default Size An Average Bold Arial Character Is About 0.556 Of The Caption Size Wide.
        size = caption_style({}, 1080, 1920)["size"]
        limit = speech.VERTICAL_PHRASES["max_chars"]
        self.assertLessEqual(limit * 0.556 * size, 1080 * 0.70)
        self.assertGreater((limit + 2) * 0.556 * size, 1080 * 0.70)

    def cli(self, folder, canvas, *options):
        words = folder / "words.json"
        if not words.exists():
            words.write_text(json.dumps([{"start": s, "end": e, "text": t} for s, e, t in WORDS]), encoding="utf-8")
        project = folder / f"edit {len(list(folder.glob('edit *.json')))}.json"
        project.write_text(json.dumps(edit(canvas)), encoding="utf-8")
        target = folder / f"cues {len(list(folder.glob('cues *.json')))}.json"
        done = subprocess.run([sys.executable, "-B", str(SCRIPTS / "speech.py"), "captions", str(words), str(project),
                               "--asset", "main", "--output", str(target), *options], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout), json.loads(target.read_text(encoding="utf-8"))

    def test_command_uses_canvas_defaults_and_explicit_options_override_them(self):
        with tempfile.TemporaryDirectory(prefix="phrase defaults ") as tmp:
            folder = Path(tmp)
            report, cues = self.cli(folder, {"width": 1080, "height": 1920, "fps": 30}, "--phrases")
            self.assertEqual(report["phrase_limits"], {"max_words": 3, "max_chars": 20, "pause": 0.4, "min_seconds": 0.3})
            self.assertEqual([cue["text"] for cue in cues], ["Stop quoting by", "the hour and", "charge for the", "result."])
            self.assertTrue(all(len(cue["text"].split()) <= 3 and len(cue["text"]) <= 20 for cue in cues))
            report, cues = self.cli(folder, {"width": 1920, "height": 1080, "fps": 30}, "--phrases")
            self.assertEqual((report["phrase_limits"]["max_words"], report["phrase_limits"]["max_chars"]), (4, 28))
            self.assertEqual([cue["text"] for cue in cues], ["Stop quoting by the", "hour and charge for", "the result."])
            report, cues = self.cli(folder, {"width": 1080, "height": 1920, "fps": 30}, "--max-words", "5", "--max-chars", "40")
            self.assertEqual((report["phrase_limits"]["max_words"], report["phrase_limits"]["max_chars"]), (5, 40))
            self.assertEqual([cue["text"] for cue in cues], ["Stop quoting by the hour", "and charge for the result."])
            report, cues = self.cli(folder, {"width": 1080, "height": 1920, "fps": 30}, "--max-words", "4")
            self.assertEqual((report["phrase_limits"]["max_words"], report["phrase_limits"]["max_chars"]), (4, 20))
            report, _ = self.cli(folder, None, "--phrases")
            self.assertEqual(report["phrase_limits"]["max_words"], 3)

    def test_option_help_states_both_defaults(self):
        listing = " ".join(speech.build_parser().format_help().split())
        captions = next(action for action in speech.build_parser()._actions if getattr(action, "choices", None)).choices["captions"]
        text = " ".join(captions.format_help().split())
        self.assertIn("The Phrase Default Is 3 On A Vertical Canvas And 4 Otherwise", text)
        self.assertIn("The Phrase Default Is 20 On A Vertical Canvas And 28 Otherwise", text)
        self.assertTrue(listing)


@unittest.skipUnless(NODE, "The Remotion Adapter Needs Node.js.")
class AdapterParityTests(unittest.TestCase):
    def test_remotion_adapter_computes_the_same_caption_style(self):
        cases = [({}, 1080, 1920), ({}, 720, 1280), ({}, 1920, 1080), ({}, 1080, 1080), ({"margin": 7}, 1080, 1920),
                 ({"size": 80, "top_margin": 15}, 1080, 1920), ({"margin": 10, "top_margin": 4, "stroke": 2}, 1920, 1080)]
        script = ("const Cut = require(process.argv[1]); const cases = JSON.parse(process.argv[2]);"
                  "console.log(JSON.stringify(cases.map(([style, w, h]) => {const look = Cut.captionStyle({caption_style: style}, w, h);"
                  "const layout = Cut.captionLayout(look, w, h); return [look, layout.edge, layout.topEdge];})));")
        done = subprocess.run([NODE, "-e", script, str(SKILL / "remotion" / "cut-plan.cjs"), json.dumps(cases)],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        for (style, w, h), (look, edge, top) in zip(cases, json.loads(done.stdout)):
            expected = caption_style({"caption_style": style}, w, h)
            with self.subTest(style=style, canvas=(w, h)):
                self.assertEqual(look, expected)
                self.assertEqual((edge, top), (round(h * expected["margin"] / 100), round(h * expected["top_margin"] / 100)))


class GuideAgreementTests(unittest.TestCase):
    def read(self, name):
        return (SKILL / name).read_text(encoding="utf-8")

    def test_every_guide_states_the_same_vertical_caption_numbers(self):
        self.assertEqual(timeline.VERTICAL_CAPTIONS, {"size": 0.06, "margin": 25, "top_margin": 12})
        self.assertEqual(speech.VERTICAL_PHRASES, {"max_words": 3, "max_chars": 20})
        skill, technical, speaking, head = (self.read(name) for name in ("SKILL.md", "TECHNICAL.md", "SPEECH.md", "styles/talking-head.md"))
        self.assertIn("On A Vertical Canvas A Phrase Holds Up To 3 Words And 20 Characters", skill)
        self.assertIn("Bottom Captions Sit 25 Percent Above The Bottom Edge", skill)
        self.assertIn("Which Is 65 On A 1080 Wide Canvas, A `margin` Of 25, And A `top_margin` Of 12", skill)
        self.assertIn("| `caption_style.size` | 6 Percent Of The Canvas Width, Which Is 65 At 1080 Wide |", technical)
        self.assertIn("| `caption_style.margin`, For Bottom Captions | 25 | 7 |", technical)
        self.assertIn("| `caption_style.top_margin`, For Top Captions | 12 | 7 |", technical)
        self.assertIn("| Phrase Words, `--max-words` | 3 | 4 |", technical)
        self.assertIn("| Phrase Characters, `--max-chars` | 20 | 28 |", technical)
        self.assertIn("| `--max-words 3` | The Most Words In One Phrase. The Default Is 3 On A Vertical Canvas And 4 On A Horizontal Or Square Canvas.", speaking)
        self.assertIn("| `--max-chars 20` | The Most Characters In One Phrase. The Default Is 20 On A Vertical Canvas And 28 On A Horizontal Or Square Canvas.", speaking)
        self.assertIn("Phrases Of Up To 3 Words And 20 Characters, A `size` Of 65, And A Bottom `margin` Of 25", head)
        for text in (skill, technical, speaking, head):
            for stale in ("The Default Of 7 Suits Horizontal Video", "Set It Near 25", "`--max-words 4`", "`--max-chars 28`", "At 64, About 21"):
                self.assertNotIn(stale, text)
        # The Safe Area Table And The Defaults Describe The Same Box.
        self.assertIn("| Bottom | About 25 Percent | 480 |", technical)
        self.assertIn("| Top | About 12 Percent | 230 |", technical)
        self.assertEqual((round(1920 * 25 / 100), round(1920 * 12 / 100)), (480, 230))

    def test_the_frame_rate_rule_is_stated_once_and_every_guide_points_to_it(self):
        skill = self.read("SKILL.md")
        self.assertEqual(skill.count("## Canvas Frame Rate"), 1)
        rule = skill[skill.index("## Canvas Frame Rate"):skill.index("## Timeline Fields")]
        for part in ("The Standard Rates Are 24, 25, 30, 48, 50, 60, 100, And 120.", "Halve It While It Is Above 30.",
                     "A 23.976 Source Counts As 24, 29.97 As 30, And 59.94 As 60.", "Mixed Sources Follow The Main Source.",
                     "The Result Is Always 24, 25, Or 30.", "Only When The Owner Asks For That Delivery Rate"):
            self.assertIn(part, rule)
        self.assertEqual(timeline.STANDARD_RATES, (24, 25, 30, 48, 50, 60, 100, 120))
        for row, rates in (("| 23.976 Or 24 | 24 |", (23.976, 24)), ("| 25 Or 50 | 25 |", (25, 50)),
                           ("| 29.97, 30, 59.94, 60, Or 120 | 30 |", (29.97, 30, 59.94, 60, 120))):
            self.assertIn(row, rule)
            expected = int(row.split("|")[2])
            self.assertEqual({timeline.canvas_rate(rate) for rate in rates}, {expected})
        self.assertIn("Set The Frame Rate By The [Canvas Frame Rate](#canvas-frame-rate) Rule", skill)
        self.assertIn("(SKILL.md#canvas-frame-rate) Rule", self.read("TECHNICAL.md"))
        self.assertIn("(../SKILL.md#canvas-frame-rate) Rule", self.read("styles/talking-head.md"))
        guides = ["SKILL.md", "TECHNICAL.md", "SPEECH.md", "BRIEF.md", "STYLES.md", "RECREATION.md", "remotion/README.md",
                  "styles/talking-head.md", "styles/skit.md", "styles/screen-demo.md"]
        for name in guides:
            text = self.read(name)
            for stale in ("Whole-Number Rate Nearest The Source", "Choose A Canvas Rate The Main Source Divides Into Evenly",
                          "Set The Output Frame Rate Before Timing", "Prefer Those Rates"):
                self.assertNotIn(stale, text, name)
        # Only The Skill Guide Spells The Rule Out. Other Guides Link To It.
        for name in guides[1:]:
            self.assertNotIn("Halve It While It Is Above 30", self.read(name), name)
        self.assertIn("Halve It While It Is Above 30", timeline.CANVAS_RATE_RULE)

    def test_script_working_copy_and_cue_guidance_is_present(self):
        skill, brief = self.read("SKILL.md"), self.read("BRIEF.md")
        self.assertIn("**Look For A Script.** Search The Project Folder For A Script Or Outline", skill)
        self.assertIn("It Is Not A Word List To Enforce.", skill)
        self.assertIn("](BRIEF.md#the-script-or-outline)", skill)
        section = brief[brief.index("## The Script Or Outline"):brief.index("## Staged Scope")]
        for part in ("Story Order", "Take Choice", "Caption Spellings", "Claims", "It Is Not A Word List To Enforce.",
                     "When The Spoken Words Depart From The Script", "Keep The Spoken Words.", "Do Not Build It From Fragments.",
                     "Is Never Settled By The Agent.", "The Agent Cannot Hear Performance.", "takes.py words.json --script script.txt"):
            self.assertIn(part, section)
        hdr = skill[skill.index("### When A Browser Cannot Play The Source"):skill.index("## Captions")]
        for part in ("**Ask The Owner Once, In Plain Words.**", "--owner-agreed-working-copy", "Leave `path` On The Original",
                     "Keep Reading The Original", "**Deliver From The Original.**", "`--owner-approved` Never Makes A Working Copy",
                     "Do Not Stop There."):
            self.assertIn(part, hdr)
        self.assertIn("**The FFmpeg Render From The Original Files Produces The Master For HDR Footage.**", skill)
        self.assertNotIn("Refuses An HDR Timeline And Points To The FFmpeg Render", skill)
        technical = self.read("TECHNICAL.md")
        self.assertIn("## Working Copies For Review", technical)
        self.assertIn("In This Kit Only Two Commands Write A Video", technical)
        self.assertIn("**The Master Comes From The Original.**", technical)
        remotion = self.read("remotion/README.md")
        self.assertIn("Preparation Then Accepts The Timeline Without `--allow-hdr`", remotion)
        self.assertIn("Picture Color In Remotion Comes From The Working Copy", remotion)
        self.assertIn("The FFmpeg Render From The Original Files Is The Faithful Master For HDR Footage.", remotion)
        head, bank = self.read("styles/talking-head.md"), self.read("assets/cue-bank/README.md")
        cues = head[head.index("## Sound Cues"):head.index("## Playful Sounds")]
        for text in (cues, bank):
            for part in ("The Hook Text Arriving Or Leaving", "An On-Screen Keyword Or Number Appearing", "A Punch-In",
                         "An Inserted Visual Arriving Or Leaving", "Propose One Or Two Events To The Owner"):
                self.assertIn(part, text)
        self.assertIn("A Plain Talking Head Still Has Visible Events.", cues)
        self.assertIn("Do Not Scatter Cues Across The Cuts", cues)
        self.assertIn("Do Not Add None Silently", bank)
        names = {record["file"][:-4] for record in json.loads(self.read("assets/cue-bank/sounds/index.json"))}
        for text in (cues, bank[bank.index("## Attach Each Cue To A Visible Event"):bank.index("## Place A Cue")]):
            listed = set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", text))
            self.assertTrue(listed and listed <= names, listed - names)
        takes = self.read("RECREATION.md")
        for part in ("--retakes", "--script", "**The Agent Cannot Hear Performance.**", "Offer The Owner The Choice",
                     "Without Either Option The Output Is The Same List As Before."):
            self.assertIn(part, takes)

    def test_added_guides_follow_the_house_style(self):
        spelled = {"dB", "dBFS", "dBTP", "kHz", "macOS"}
        for name in ("BRIEF.md", "STYLES.md", "styles/talking-head.md", "styles/skit.md", "styles/screen-demo.md"):
            text = self.read(name)
            text = re.sub(r"```.*?```", " ", text, flags=re.S)
            text = re.sub(r"`[^`\n]*`", " ", text)
            text = re.sub(r"\]\([^)]*\)", "] ", text)
            self.assertNotIn("!", text, name)
            for number, line in enumerate(text.splitlines(), 1):
                for token in line.split():
                    for part in re.split(r"[-/—–]", token):
                        word = part.strip("\"'“”‘’()[]{}*_.,:;!?|#>+=&×−")
                        if word in spelled or not word or not word[0].isalpha():
                            continue
                        self.assertFalse(word[0].islower(), f"{name} Line {number}: {word!r} In {line.strip()[:90]!r}")


if __name__ == "__main__":
    unittest.main()
