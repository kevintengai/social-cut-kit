"""Exercise Script Drafting, The Table Read, The Check Command, And The Delivery Sheet."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
TOOL = SKILL / "scripts" / "script_desk.py"
BOARD = SKILL.parent / "director" / "scripts" / "board.py"
PRACTICE = SKILL / "assets" / "practice-script.json"

BRIEF = {
    "format": "school.campaign/1",
    "title": "Find The Ready Repair",
    "viewer": "Repair Shop Owners",
    "offer": "An Interactive Queue Demo",
    "action": "Open The Demo And Select Ready Only",
    "channel": "A Vertical Product Reel",
    "destination": "demo.html",
    "metric": "Ready Only Filter Activations",
    "reviewer": "Project Owner",
    "evidence": [
        {
            "id": "P1",
            "claim": "The Filter Shows Which Repair Is Ready",
            "source": "demo.html#ready",
            "visual": "The Queue Changes From Three Jobs To One Ready Job",
        }
    ],
}


def beat(key, purpose, seconds, voice, picture="A Clear Picture", **more):
    row = {
        "id": key,
        "purpose": purpose,
        "seconds": seconds,
        "voice": voice,
        "picture": picture,
        "proof": "",
        "media": "",
        "source_in": 0,
        "capture": "A Planned Recording",
    }
    row.update(more)
    return row


def script(beats, **more):
    data = {
        "format": "school.script/1",
        "title": "Practice Script",
        "reviewer": "Project Owner",
        "caption": "A Draft Caption With Its Caveat.",
        "openings": [
            {
                "angle": "Result First",
                "first_frame": "The Finished Result",
                "first_sentence": "Here Is The Result.",
                "second_sentence": "Here Is What It Cost.",
            }
        ],
        "evidence": [],
        "beats": beats,
    }
    data.update(more)
    return data


class DeskCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="script desk test ")
        self.addCleanup(folder.cleanup)
        self.work = Path(folder.name)
        self.home = self.work / "kit home"

    def run_tool(self, *args, code=0):
        env = dict(os.environ, PYTHONIOENCODING="utf-8", SOCIAL_CUT_KIT_HOME=str(self.home))
        done = subprocess.run(
            [sys.executable, "-B", str(TOOL), *map(str, args)],
            capture_output=True,
            env=env,
            check=False,
        )
        out, err = done.stdout.decode("utf-8"), done.stderr.decode("utf-8")
        self.assertEqual(done.returncode, code, err or out)
        return out.replace("\r\n", "\n"), err.replace("\r\n", "\n")

    def save(self, data, name="script.json"):
        path = self.work / name
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return path

    def check(self, data, *args, code=0):
        out, _ = self.run_tool("check", self.save(data), "--json", *args, code=code)
        return json.loads(out)

    def codes(self, result, level):
        return [issue["code"] for issue in result["issues"] if issue["level"] == level]


class ExistingCommands(DeskCase):
    def test_outline_draft_is_unchanged(self):
        brief = self.save(BRIEF, "brief.json")
        target = self.work / "draft.json"
        out, _ = self.run_tool("outline", brief, target, "--seconds", 17.5)
        self.assertEqual(out, f"Created {target}\n")
        draft = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(list(draft), ["format", "title", "reviewer", "openings", "evidence", "beats"])
        self.assertEqual(
            draft["openings"],
            [
                {"angle": "Outcome First", "first_frame": "The Queue Changes From Three Jobs To One Ready Job"},
                {"angle": "Question First", "first_frame": "Show The Decision Before Its Result"},
            ],
        )
        self.assertEqual(draft["evidence"], BRIEF["evidence"])
        self.assertEqual(
            draft["beats"][1],
            {
                "id": "B02",
                "purpose": "Context",
                "seconds": 3.5,
                "voice": "Here Is The Starting Point For Repair Shop Owners.",
                "picture": "Show The Starting State In The Same Recording",
                "proof": "",
                "media": "",
                "source_in": 0,
            },
        )
        self.assertEqual([b["purpose"] for b in draft["beats"]], ["Opening", "Context", "Demonstration", "Invitation"])
        self.assertEqual([b["seconds"] for b in draft["beats"]], [3.5, 3.5, 7.0, 3.5])
        self.assertEqual(draft["beats"][3]["picture"], "demo.html")
        _, err = self.run_tool("outline", brief, target, code=1)
        self.assertIn("exists", err.lower())
        _, err = self.run_tool("outline", brief, self.work / "short.json", "--seconds", 2, code=1)
        self.assertEqual(err, "Choose A Duration From 3 To 7200 Seconds.\n")
        empty = self.save(dict(BRIEF, evidence=[]), "empty.json")
        _, err = self.run_tool("outline", empty, self.work / "none.json", code=1)
        self.assertIn("Add At Least One Verified Proof", err)

    def test_table_read_is_unchanged(self):
        data = script(
            [
                beat("B01", "Opening", 3, "Which Repair Is Ready?", "All Three Jobs"),
                beat("B02", "Demonstration", 2.5, "Select Ready Only.", "One Job Remains", proof="P1"),
            ],
            evidence=BRIEF["evidence"],
        )
        out, _ = self.run_tool("read", self.save(data))
        self.assertEqual(
            out,
            "# Practice Script\n\n"
            "000.00 - 003.00 | Which Repair Is Ready? | All Three Jobs | \n"
            "003.00 - 005.50 | Select Ready Only. | One Job Remains | P1\n",
        )
        _, err = self.run_tool("read", self.save({"format": "other"}, "other.json"), code=1)
        self.assertEqual(err, "Expected A Script File.\n")

    @unittest.skipUnless(BOARD.is_file(), "The Director Skill Is Not Beside This One")
    def test_director_accepts_a_script_with_the_new_fields(self):
        board = self.work / "board.html"
        done = subprocess.run(
            [sys.executable, "-B", str(BOARD), "board", str(PRACTICE), str(board)],
            capture_output=True,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr.decode("utf-8", "replace"))
        self.assertIn("Your Repair Was Ready Two Days Ago", board.read_text(encoding="utf-8"))


class CheckCommand(DeskCase):
    def test_practice_script_passes_clean(self):
        out, _ = self.run_tool("check", PRACTICE)
        self.assertIn("Script Check | Your Repair Was Ready Two Days Ago", out)
        self.assertIn("Pace: 3 Words Per Second (From The Script File).", out)
        self.assertIn("Timed Runtime: 28 Seconds.", out)
        self.assertIn("Target: 30 Seconds.", out)
        self.assertIn("Result: 0 To Fix, 0 To Review.", out)
        self.assertNotIn("To Fix (", out)

    def test_opening_length_is_measured_at_the_given_pace(self):
        data = script(
            [
                beat("B01", "Opening", 4, "This Opening Sentence Runs For Exactly Ten Spoken Words Here."),
                beat("B02", "Payoff", 3, "Here Is The Payoff."),
            ]
        )
        result = self.check(data, code=1)
        self.assertEqual(self.codes(result, "fix"), ["opening-too-long"])
        issue = result["issues"][0]
        self.assertEqual((issue["where"], issue["line"]), ("B01 (Line 16)", 16))
        self.assertIn("Runs 10 Words And Ends At About 3.3 Seconds At 3 Words Per Second", issue["message"])
        self.assertEqual(result["opening"]["words"], 10)
        self.assertEqual(result["opening"]["ends_at"], 3.33)
        fast = self.check(data, "--pace", 4)
        self.assertEqual(fast["fix"], 0)
        self.assertEqual(fast["opening"]["ends_at"], 2.5)
        text, _ = self.run_tool("check", self.save(data), code=1)
        self.assertIn("To Fix (1)\n- B01 (Line 16): The Opening Sentence Runs 10 Words", text)
        self.assertIn("Result: 1 To Fix, 0 To Review.", text)

    def test_a_title_or_an_initial_does_not_end_the_opening_sentence(self):
        data = script(
            [
                beat("B01", "Opening", 5, "Dr. Lee Cut The Wait At J. Smith Repairs By Half In One Week."),
                beat("B02", "Payoff", 3, "Here Is How."),
            ]
        )
        result = self.check(data, code=1)
        self.assertEqual(result["opening"]["words"], 14)
        self.assertEqual(self.codes(result, "fix"), ["opening-too-long"])

    def test_a_late_or_greeting_opening_is_flagged(self):
        late = script(
            [
                beat("B01", "Cold Open", 2, ""),
                beat("B02", "Opening", 3, "Hey Everyone, Welcome Back."),
            ]
        )
        result = self.check(late, code=1)
        self.assertEqual(self.codes(result, "fix"), ["opening-too-long"])
        self.assertEqual(result["opening"]["beat"], "B02")
        self.assertEqual(result["opening"]["ends_at"], 3.33)
        self.assertEqual(self.codes(result, "review"), ["greeting-opening"])

    def test_pictures_and_capture_notes(self):
        data = script(
            [
                beat("B01", "Opening", 3, "Look At This Queue.", picture=""),
                beat("B02", "Payoff", 3, "Now It Is Sorted.", capture=""),
                beat("B03", "Hold", 2, "It Stays Sorted.", capture="", media="queue.mp4"),
            ]
        )
        result = self.check(data, code=1)
        self.assertEqual(self.codes(result, "fix"), ["missing-picture"])
        self.assertEqual(result["issues"][0]["where"], "B01 (Line 16)")
        self.assertEqual(self.codes(result, "review"), ["missing-capture"])
        self.assertEqual(result["issues"][1]["where"], "B02 (Line 27)")

    def test_claims_need_a_source(self):
        data = script(
            [
                beat("B01", "Opening", 3, "This Filter Is Quick.", proof="P1"),
                beat("B02", "Proof", 3, "It Is 40% Faster.", proof=""),
                beat("B03", "Proof", 3, "The Numbers Hold.", proof="P9"),
                beat("B04", "Payoff", 3, "So The List Is Short.", proof="P2"),
            ],
            evidence=[
                {"id": "P1", "claim": "The Filter Is Quick", "source": "", "visual": "A Timer"},
                {"id": "P2", "claim": "The List Is Short", "source": "Owned Recording", "visual": "Three Rows", "opened": False},
                {"id": "P3", "claim": "An Unused Claim", "source": "A Report", "visual": "A Chart"},
            ],
        )
        result = self.check(data, code=1)
        self.assertEqual(self.codes(result, "fix"), ["claim-without-source", "unknown-proof"])
        self.assertEqual(
            self.codes(result, "review"),
            ["source-not-opened", "claim-without-proof", "claim-not-shown"],
        )
        by_code = {issue["code"]: issue for issue in result["issues"]}
        self.assertEqual(by_code["claim-without-source"]["where"], "P1 (Line 15)")
        self.assertEqual(by_code["source-not-opened"]["where"], "P2 (Line 21)")
        self.assertEqual(by_code["claim-without-proof"]["where"], "B02 (Line 47)")
        self.assertIn("The Proof P9 Is Not In The Evidence List.", by_code["unknown-proof"]["message"])
        self.assertEqual(by_code["claim-not-shown"]["where"], "P3 (Line 28)")

    def test_one_call_to_action_and_it_comes_last(self):
        two = script(
            [
                beat("B01", "Opening", 3, "Look At This Queue."),
                beat("B02", "Invitation", 2, "Open The Demo."),
                beat("B03", "Payoff", 3, "Now It Is Sorted."),
                beat("B04", "Close", 2, "Book A Walkthrough.", cta=True),
            ]
        )
        result = self.check(two, code=1)
        self.assertEqual(self.codes(result, "fix"), ["second-ask", "ask-not-last"])
        self.assertEqual([i["where"] for i in result["issues"]], ["B04 (Line 49)", "B02 (Line 27)"])
        last = script(
            [
                beat("B01", "Opening", 3, "Look At This Queue."),
                beat("B02", "Payoff", 3, "Subscribe For More. Now It Is Sorted."),
                beat("B03", "Call To Action", 5, "Open The Demo And Try The Filter On Your Own Repair Jobs Today Before You Call Anyone."),
            ]
        )
        result = self.check(last)
        self.assertEqual(result["fix"], 0)
        self.assertEqual(self.codes(result, "review"), ["unmarked-ask", "long-ask", "line-over-time"])

    def test_runtime_is_held_against_the_target(self):
        beats = [
            beat("B01", "Opening", 3, "Look At This Queue."),
            beat("B02", "Payoff", 29, "Now It Is Sorted."),
        ]
        over = self.check(script(beats), "--target", 30, code=1)
        self.assertEqual(self.codes(over, "fix"), ["over-target"])
        self.assertIn("Runs 32 Seconds, 2 Over The 30-Second Target", over["issues"][0]["message"])
        self.assertEqual((over["runtime_seconds"], over["target_seconds"]), (32.0, 30.0))
        self.assertEqual(self.check(script(beats), "--target", "0:32")["fix"], 0)
        self.assertEqual(self.codes(self.check(script(beats), "--target", 60), "review"), ["under-target"])
        self.assertEqual(self.check(script(beats, target_seconds=20), code=1)["target_seconds"], 20.0)
        self.assertIsNone(self.check(script(beats))["target_seconds"])
        crowded = script(
            [
                beat("B01", "Opening", 2, "Look At This Queue."),
                beat("B02", "Payoff", 2, "Now It Is Sorted By Status So The Finished Jobs Rise To The Top Of The List."),
            ]
        )
        self.assertEqual(self.codes(self.check(crowded), "review"), ["line-over-time", "speech-over-runtime"])

    def test_ten_second_mark_is_located(self):
        data = script(
            [
                beat("B01", "Opening", 3, "Look At This Queue."),
                beat("B02", "Stakes", 5, "Every Job Sits In One List."),
                beat("B03", "Proof", 6, "Select Ready Only, And Three Jobs Remain On The Screen."),
                beat("B04", "Payoff", 4, "Call Those Three."),
            ]
        )
        result = self.check(data)
        self.assertEqual(
            result["ten_second_mark"],
            {
                "beat": "B03",
                "line": 38,
                "words_in": 6,
                "state": "speaking",
                "said_before": "Select Ready Only, And Three Jobs",
                "said_after": "Remain On The Screen.",
            },
        )
        self.assertEqual(result["seconds_3_to_10"], ["B02", "B03"])
        self.assertEqual(result["second_sentence"]["sentence"], "Every Job Sits In One List.")
        self.assertEqual(result["second_sentence"]["ends_at"], 5.0)
        text, _ = self.run_tool("check", self.save(data))
        self.assertIn('- Ten-Second Mark: Falls In B03 (Line 38), About 6 Words In. Said Before It: "Select Ready Only, And Three Jobs"', text)
        self.assertIn("- Seconds 3 To 10 Run Through B02, B03.", text)
        data["beats"][2]["voice"] = "Three Remain."
        self.assertEqual(self.check(data)["ten_second_mark"]["state"], "hold")
        short = self.check(script(data["beats"][:2]))
        self.assertEqual(short["ten_second_mark"], {"state": "ended", "runtime": 8.0})
        text, _ = self.run_tool("check", self.save(script(data["beats"][:2])))
        self.assertIn("The Script Ends At 8 Seconds, Before The Mark.", text)

    def test_pace_comes_from_the_flag_then_the_script_then_the_defaults(self):
        beats = [beat("B01", "Opening", 3, "Look At This Queue."), beat("B02", "Payoff", 3, "Now It Is Sorted.")]
        self.assertEqual(self.check(script(beats))["pace_source"], "Standard")
        self.home.mkdir()
        (self.home / "video-script.md").write_text(
            "# Video Script Defaults\n\n- Library: Nowhere\n- Pace: 2.5 Words Per Second\n", encoding="utf-8"
        )
        result = self.check(script(beats))
        self.assertEqual((result["pace"], result["pace_source"]), (2.5, "From The Defaults File"))
        result = self.check(script(beats, pace=3.5))
        self.assertEqual((result["pace"], result["pace_source"]), (3.5, "From The Script File"))
        result = self.check(script(beats, pace=3.5), "--pace", 2)
        self.assertEqual((result["pace"], result["pace_source"]), (2.0, "Given"))
        _, err = self.run_tool("check", self.save(script(beats)), "--pace", 0.1, code=1)
        self.assertEqual(err, "Use A Pace Between 0.5 And 8 Spoken Words Per Second.\n")

    def test_speakability_caption_and_openings(self):
        data = script(
            [
                beat("B01", "Opening", 3, "Look At This Queue."),
                beat("B02", "Payoff", 4, "See It At example.com Today."),
            ],
            caption="",
            openings=[{"angle": "Result First", "first_frame": "A Short List", "first_sentence": "Three Jobs Remain."}],
        )
        result = self.check(data)
        self.assertEqual(self.codes(result, "review"), ["link-in-speech", "no-caption", "opening-unwritten"])
        self.assertIn("Has No Second Sentence.", result["issues"][2]["message"])
        self.assertEqual(result["issues"][2]["where"], "Opening 1 (Line 7)")
        out, _ = self.run_tool("check", self.save(data), "--strict", code=1)
        self.assertIn("Result: 0 To Fix, 3 To Review.", out)
        bare = self.check(script(data["beats"], openings=[]))
        self.assertIn("no-alternatives", self.codes(bare, "review"))

    def test_structure_problems_are_reported_not_crashed_on(self):
        data = script(
            [
                beat("B01", "Opening", 3, "Look At This Queue."),
                beat("B01", "Payoff", 0, "Now It Is Sorted."),
            ]
        )
        result = self.check(data, code=1)
        self.assertEqual(self.codes(result, "fix"), ["beat-id", "beat-seconds"])
        self.assertEqual(result["runtime_seconds"], 3.0)
        silent = self.check(script([beat("B01", "Opening", 3, "")]), code=1)
        self.assertEqual(self.codes(silent, "fix"), ["no-speech"])
        compact = self.work / "compact.json"
        compact.write_text(json.dumps(script([beat("B01", "Opening", 3, "Look At This Queue.", picture="")])), encoding="utf-8-sig")
        out, _ = self.run_tool("check", compact, code=1)
        self.assertIn("- B01 (Line 1): No Picture.", out)
        _, err = self.run_tool("check", self.save({"format": "school.script/1", "beats": []}, "empty.json"), code=1)
        self.assertEqual(err, "Expected A Script File With At Least One Beat.\n")
        absent = self.work / "absent.json"
        _, err = self.run_tool("check", absent, code=1)
        self.assertEqual(err, f"No File At {absent}.\n")
        broken = self.work / "broken.json"
        broken.write_text('{"format": "school.script/1",\n "beats": [}', encoding="utf-8")
        _, err = self.run_tool("sheet", broken, code=1)
        self.assertEqual(err, f"{broken} Is Not Valid JSON Near Line 2, Column 12.\n")
        loose = script([beat("B01", "Opening", 3, "Look At This Queue.")], evidence={"P1": "A Claim"})
        _, err = self.run_tool("check", self.save(loose, "loose.json"), code=1)
        self.assertEqual(err, "Expected evidence To Be A List Of Objects.\n")

    def test_non_ascii_lines_print_on_a_narrow_console(self):
        data = script([beat("B01", "Opening", 3, "Café → 修理 Ready.")])
        env = dict(os.environ, PYTHONIOENCODING="cp1252", SOCIAL_CUT_KIT_HOME=str(self.home))
        done = subprocess.run(
            [sys.executable, "-B", str(TOOL), "check", str(self.save(data))],
            capture_output=True,
            env=env,
            check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(b"\\u2192", done.stdout)


class DeliverySheet(DeskCase):
    def test_sheet_lists_every_part_of_the_delivery(self):
        out, _ = self.run_tool("sheet", PRACTICE)
        for heading in (
            "# Your Repair Was Ready Two Days Ago",
            "## Timed Script",
            "## Capture List",
            "## Alternative Openings",
            "## Draft Caption",
            "## Claims To Verify",
        ):
            self.assertIn(heading + "\n", out)
        self.assertIn("- Runtime: 28 Seconds Timed. About 24 Seconds Spoken At 3 Words Per Second (From The Script File).", out)
        self.assertIn("| 06.00 - 11.00 | B03 Problem | Forty Jobs Share One List", out)
        self.assertIn("- B05: One Unbroken Screen Recording Across The Click | Capture Needed", out)
        self.assertIn("2. Result First | First Sentence: This List Is Every Repair Ready Today. | Second Sentence: Ten Seconds Ago It Showed Forty.", out)
        self.assertIn("Demo: example.com/repair-queue", out)
        self.assertIn("| Source Opened. Checked: Watched Against The Wording On 2026-11-10.", out)

    def test_sheet_marks_what_is_missing(self):
        data = script(
            [beat("B01", "Opening", 3, "Look At This | Queue.", capture="", media="queue.mp4", proof="P1")],
            caption="",
            openings=[],
            evidence=[{"id": "P1", "claim": "The Queue Sorts", "source": "A Page", "visual": "Rows", "opened": False}],
        )
        out, _ = self.run_tool("sheet", self.save(data), "--pace", 2)
        self.assertIn("At 2 Words Per Second (Given).", out)
        self.assertIn("| Look At This \\| Queue. |", out)
        self.assertIn("| Media: queue.mp4 | P1 |", out)
        self.assertIn("- B01: A Clear Picture | Have queue.mp4", out)
        self.assertIn("## Alternative Openings\n\nNot Written.", out)
        self.assertIn("## Draft Caption\n\nNot Written.", out)
        self.assertIn("| Source Could Not Be Opened, Unverified.", out)

    def test_help_uses_the_house_style(self):
        out, _ = self.run_tool("--help")
        self.assertIn("Usage: script_desk.py", out)
        self.assertIn("Show This Help And Exit", out)
        for command in ("outline", "read", "check", "sheet"):
            self.assertIn(f"    {command} ", out)


if __name__ == "__main__":
    unittest.main()
