"""Take Detection: Nearby Repeats As Before, Full Retakes Far Apart, Completeness Hints, And Script Alignment."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import takes


def say(at, text, pace=0.3, length=0.25):
    return [(round(at + n * pace, 3), round(at + n * pace + length, 3), word) for n, word in enumerate(text.split())]


# A 3 Minute 40 Second Recording With A Restart Inside A Sentence, A Full Retake A Minute Later, And Three Endings.
RECORDING = sorted(
    say(0, "Most people edit their videos the slow way.")
    + say(4, "The first thing you need to the first thing you need to know is that cuts follow the words.")
    + say(12, "Second, keep every breath that sounds natural.")
    + say(80, "Second, keep every breath that sounds natural.")
    + say(150, "Follow for more and comment guide to get the")
    + say(160, "Follow for more and comment guide to get the free checklist.")
    + say(200, "Follow for more and comment guide and I will send you the free checklist.")
)
SCRIPT = """HOOK: Most people edit their videos the slow way.
[B-ROLL Of The Timeline]

1. The first thing you need to know is that cuts follow the words.
- Second, keep every breath that sounds natural. Third, never trim the last word.
0:35 - CTA: Follow for more and comment GUIDE to get the free checklist.
"""
# What The Tool Printed For This Recording Before Retake Detection Existed.
NEARBY = [
    {"phrase": "the first thing", "first_attempt": [4.0, 4.85], "next_attempt": [5.8, 6.65],
     "audition_ranges": [[3.85, 5.0], [5.65, 6.8]]},
    {"phrase": "follow for more", "first_attempt": [150.0, 150.85], "next_attempt": [160.0, 160.85],
     "audition_ranges": [[149.85, 151.0], [159.85, 161.0]]},
]


class NearbyRepeatTests(unittest.TestCase):
    def test_existing_output_is_unchanged_for_existing_options(self):
        self.assertEqual(takes.candidates(RECORDING, 3, 30, 0.15), NEARBY)
        self.assertEqual(takes.candidates(RECORDING, 3, 5, 0.15), NEARBY[:1])
        wide = takes.candidates(RECORDING, 3, 100, 0)
        self.assertEqual([row["phrase"] for row in wide],
                         ["the first thing", "second keep every", "follow for more", "follow for more", "the free checklist"])
        self.assertEqual(wide[0]["audition_ranges"], [[4.0, 4.85], [5.8, 6.65]])

    def test_the_short_window_misses_what_retakes_finds(self):
        phrases = {row["phrase"] for row in takes.candidates(RECORDING, 3, 30, 0.15)}
        self.assertNotIn("second keep every", phrases)
        groups = takes.retakes(RECORDING, 3, 30, 0.15)["retakes"]
        self.assertIn("Second, keep every breath that sounds natural.", [group["line"] for group in groups])


class RetakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = takes.retakes(RECORDING, 3, 30, 0.15)
        cls.groups = cls.report["retakes"]

    def test_report_shape_and_listening_note(self):
        self.assertEqual((self.report["mode"], self.report["words"], self.report["sentence_punctuation"],
                          self.report["estimated_word_timings"]), ("retakes", 75, True, 0))
        self.assertEqual(self.report["nearby_repeats"], NEARBY)
        self.assertNotIn("script", self.report)
        self.assertIn("The Tool Cannot Hear Performance.", self.report["notes"][0])
        self.assertIn("Offer The Owner The Choice.", self.report["notes"][0])
        self.assertEqual(len(self.groups), 3)
        self.assertEqual([group["attempts"][0]["source_seconds"][0] for group in self.groups], [4.0, 12.0, 150.0])

    def test_a_restart_inside_a_sentence_is_one_interrupted_and_one_complete_attempt(self):
        group = self.groups[0]
        first, second = group["attempts"]
        self.assertEqual((first["text"], first["hint"], first["interrupted"], first["reaches_sentence_end"], first["complete"]),
                         ("The first thing you need to", "interrupted", True, False, False))
        self.assertEqual((second["hint"], second["reaches_sentence_end"], second["complete"], second["words"]),
                         ("complete", True, True, 13))
        self.assertEqual(first["share_of_longest_attempt"], 0.46)
        self.assertTrue(first["split_at_repeat"])
        self.assertEqual((group["decision"], group["complete_takes"]), ("one_complete_take", [2]))
        self.assertIn("Can Be Deliberate", group["caution"])
        self.assertEqual(group["line"], "the first thing you need to know is that cuts follow the words.")

    def test_a_full_retake_a_minute_later_is_grouped_and_left_to_the_owner(self):
        group = self.groups[1]
        self.assertEqual([row["source_seconds"] for row in group["attempts"]], [[12.0, 14.05], [80.0, 82.05]])
        self.assertEqual([row["hint"] for row in group["attempts"]], ["complete", "complete"])
        self.assertEqual((group["decision"], group["complete_takes"], group["latest_complete_take"]), ("owner_choice", [1, 2], 2))
        self.assertIn("Look Equally Complete. The Tool Cannot Hear Performance. Offer The Owner The Choice", group["note"])
        self.assertNotIn("caution", group)

    def test_three_endings_are_one_group_with_the_unfinished_one_marked(self):
        group = self.groups[2]
        self.assertEqual([row["take"] for row in group["attempts"]], [1, 2, 3])
        self.assertEqual([row["hint"] for row in group["attempts"]], ["no_sentence_end", "complete", "complete"])
        self.assertEqual([row["complete"] for row in group["attempts"]], [False, True, True])
        self.assertEqual([row["source_seconds"][0] for row in group["attempts"]], [150.0, 160.0, 200.0])
        self.assertEqual((group["decision"], group["complete_takes"], group["latest_complete_take"]), ("owner_choice", [2, 3], 3))
        self.assertEqual(group["attempts"][0]["share_of_longest_attempt"], 0.64)

    def test_handles_stop_short_of_the_neighboring_words(self):
        first, second = self.groups[0]["attempts"]
        # The Restart Follows Its False Start After 0.05 Seconds, So Neither Handle Reaches Into The Other Attempt.
        self.assertEqual((first["handles"], first["audition_range"]), ({"lead": 0.15, "tail": 0.05}, [3.85, 5.8]))
        self.assertEqual((second["handles"], second["audition_range"]), ({"lead": 0.05, "tail": 0.15}, [5.75, 9.8]))
        opening = takes.retakes(say(0, "Hello there friend. Hello there friend."), 3, 30, 0.4)["retakes"][0]["attempts"]
        self.assertEqual(opening[0]["handles"]["lead"], 0)
        self.assertEqual(opening[0]["audition_range"][0], 0)
        self.assertEqual(opening[1]["handles"], {"lead": 0.05, "tail": 0.4})
        wide = takes.retakes(RECORDING, 3, 30, 0)["retakes"][1]["attempts"][0]
        self.assertEqual(wide["audition_range"], wide["source_seconds"])

    def test_trailing_off_and_quick_restarts_read_as_interrupted(self):
        words = sorted(say(0, "So the plan for today is—") + say(3, "So the plan for today is simple.")
                       + say(10, "We keep the price where it") + say(12.2, "We keep the price where it is today."))
        groups = takes.retakes(words, 3, 30, 0.15)["retakes"]
        self.assertEqual([[row["hint"] for row in group["attempts"]] for group in groups],
                         [["interrupted", "complete"], ["interrupted", "complete"]])
        self.assertEqual([group["decision"] for group in groups], ["one_complete_take", "one_complete_take"])
        self.assertNotIn("split_at_repeat", groups[0]["attempts"][0])

    def test_without_punctuation_completeness_comes_from_pauses_and_length(self):
        words = sorted(say(0, "follow for more and comment guide to get") + say(10, "follow for more and comment guide to get the free checklist")
                       + say(30, "follow for more and comment guide to get the free checklist"))
        report = takes.retakes(words, 3, 30, 0.15)
        self.assertFalse(report["sentence_punctuation"])
        self.assertIn("No Sentence Punctuation", " ".join(report["notes"]))
        group = report["retakes"][0]
        self.assertEqual([row["reaches_sentence_end"] for row in group["attempts"]], [None, None, None])
        self.assertEqual([row["hint"] for row in group["attempts"]], ["ends_at_a_pause"] * 3)
        self.assertEqual([row["complete"] for row in group["attempts"]], [False, True, True])
        self.assertEqual(group["decision"], "owner_choice")

    def test_different_sentences_and_short_emphasis_are_not_grouped(self):
        words = sorted(say(0, "It works. It works.") + say(5, "The first tip is to plan your shots carefully.")
                       + say(20, "The second tip is to light your face evenly.") + say(40, "Thanks for watching this one."))
        self.assertEqual(takes.retakes(words, 3, 30, 0.15)["retakes"], [])

    def test_subtitle_cues_are_split_into_estimated_words(self):
        cues = [(0.0, 3.0, "Second, keep every breath that sounds natural."), (60.0, 63.0, "Second, keep every breath that sounds natural.")]
        report = takes.retakes(cues, 3, 30, 0.15)
        self.assertEqual(report["estimated_word_timings"], 2)
        self.assertIn("Word Times Are Estimates", " ".join(report["notes"]))
        self.assertEqual(report["retakes"][0]["decision"], "owner_choice")
        self.assertEqual(report["retakes"][0]["attempts"][1]["source_seconds"], [60.0, 63.0])


class ScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = takes.retakes(RECORDING, 3, 30, 0.15, script=SCRIPT)
        cls.lines = cls.report["script"]["lines"]

    def test_script_lines_drop_directions_labels_marks_and_timecodes(self):
        self.assertEqual(takes.script_lines(SCRIPT), [
            "Most people edit their videos the slow way.",
            "The first thing you need to know is that cuts follow the words.",
            "Second, keep every breath that sounds natural.",
            "Third, never trim the last word.",
            "Follow for more and comment GUIDE to get the free checklist.",
        ])
        self.assertEqual(takes.script_lines("# Notes\n(Smile) Dr. Lee said yes. Tip 1: Start early\n\n[Cut]\n"),
                         ["Dr. Lee said yes.", "Tip 1: Start early"])

    def test_each_line_lists_its_attempts_and_a_decision(self):
        self.assertEqual([entry["decision"] for entry in self.lines],
                         ["one_complete_take", "one_complete_take", "owner_choice", "not_spoken", "owner_choice"])
        self.assertEqual([[row["hint"] for row in entry["attempts"]] for entry in self.lines],
                         [["complete"], ["interrupted", "complete"], ["complete", "complete"], [],
                          ["no_sentence_end", "complete", "complete"]])
        self.assertEqual([entry["complete_takes"] for entry in self.lines], [[1], [2], [1, 2], [], [2, 3]])
        self.assertEqual(self.lines[1]["attempts"][1]["source_seconds"], [5.8, 9.65])
        self.assertEqual(self.lines[2]["latest_complete_take"], 2)
        self.assertEqual(self.lines[0]["attempts"][0]["script_coverage"], 1.0)

    def test_a_reworded_ending_is_complete_but_flagged(self):
        first, second, third = self.lines[4]["attempts"]
        self.assertEqual((first["reaches_line_end"], first["complete"], first["script_coverage"]), (False, False, 0.82))
        self.assertNotIn("wording_differs_from_script", second)
        self.assertEqual((third["complete"], third["reaches_line_end"], third["wording_differs_from_script"]), (True, True, True))
        self.assertEqual(third["script_coverage"], 0.82)

    def test_lines_without_a_complete_take_and_unscripted_speech_are_listed(self):
        script = self.report["script"]
        self.assertEqual(script["lines_without_a_complete_take"],
                         [{"line": 4, "script_text": "Third, never trim the last word.", "decision": "not_spoken"}])
        self.assertEqual(script["spoken_but_not_in_script"], [])
        extra = sorted(RECORDING + say(100, "Honestly this next part was never planned at all."))
        report = takes.retakes(extra, 3, 30, 0.15, script=SCRIPT)["script"]
        self.assertEqual(report["spoken_but_not_in_script"],
                         [{"source_seconds": [100.0, 102.65], "text": "Honestly this next part was never planned at all."}])
        only_false_starts = takes.retakes(say(0, "The first thing you need to") + say(5, "The first thing you"), 3, 30, 0.15,
                                          script="The first thing you need to know is that cuts follow the words.")["script"]
        self.assertEqual(only_false_starts["lines"][0]["decision"], "no_complete_take")
        self.assertEqual(only_false_starts["lines_without_a_complete_take"][0]["decision"], "no_complete_take")
        self.assertEqual(len(only_false_starts["lines"][0]["attempts"]), 2)

    def test_deliberate_parallel_phrasing_still_counts_as_one_complete_line(self):
        words = say(0, "The more you post, the more you grow.")
        report = takes.retakes(words, 3, 30, 0.15, script="The more you post, the more you grow.")
        line = report["script"]["lines"][0]
        self.assertEqual((line["decision"], len(line["attempts"])), ("one_complete_take", 1))
        self.assertEqual(line["attempts"][0]["source_seconds"], [0.0, 2.35])
        self.assertTrue(line["attempts"][0]["split_at_repeat"])
        self.assertIn("Can Be Deliberate", report["retakes"][0]["caution"])


class CommandTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="take fixtures ")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.words = self.root / "words.json"
        self.words.write_text(json.dumps({"words": [{"start": s, "end": e, "word": t} for s, e, t in RECORDING]}), encoding="utf-8")
        self.script = self.root / "script.txt"
        self.script.write_text(SCRIPT, encoding="utf-8")

    def cli(self, *arguments):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / "takes.py"), str(self.words), *map(str, arguments)],
                              capture_output=True, text=True, encoding="utf-8")

    def test_plain_run_prints_the_same_list_as_before(self):
        done = self.cli()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout), NEARBY)
        self.assertEqual(json.loads(self.cli("--words", "3", "--window", "30", "--handle", "0.15").stdout), NEARBY)

    def test_retakes_and_script_options_print_the_report(self):
        done = self.cli("--retakes")
        self.assertEqual(done.returncode, 0, done.stderr)
        report = json.loads(done.stdout)
        self.assertEqual((report["mode"], len(report["retakes"])), ("retakes", 3))
        self.assertNotIn("script", report)
        scripted = json.loads(self.cli("--script", self.script).stdout)
        self.assertEqual([entry["line"] for entry in scripted["script"]["lines_without_a_complete_take"]], [4])
        self.assertEqual(len(scripted["retakes"]), 3)
        strict = json.loads(self.cli("--retakes", "--min-words", "12", "--gap", "0.2").stdout)
        self.assertEqual(strict["mode"], "retakes")

    def test_bad_values_and_bad_scripts_are_refused(self):
        for bad in (("--words", "1"), ("--window", "0"), ("--handle", "9"), ("--retakes", "--min-words", "1"),
                    ("--retakes", "--gap", "0")):
            done = self.cli(*bad)
            self.assertEqual(done.returncode, 2, bad)
        empty = self.root / "empty.txt"
        empty.write_text("[Only A Direction]\n", encoding="utf-8")
        done = self.cli("--script", empty)
        self.assertEqual((done.returncode, done.stderr.strip()), (1, "The Script File Holds No Spoken Lines."))
        data = self.root / "script.json"
        data.write_text("{}", encoding="utf-8")
        self.assertEqual(self.cli("--script", data).stderr.strip(), "Supply The Script As A Plain Text File.")
        self.assertEqual(self.cli("--script", self.root / "missing.txt").returncode, 1)

    def test_help_is_capitalized_and_names_the_new_options(self):
        listing = takes.build_parser().format_help()
        for option in ("--retakes", "--script", "--min-words", "--gap"):
            self.assertIn(option, listing)
        for action in takes.build_parser()._actions:
            if action.option_strings and action.help and "show this help" not in action.help:
                words = [word for token in action.help.split() if not token.startswith("--") for word in token.split("-") if word[:1].isalpha()]
                self.assertFalse([word for word in words if word[0].islower()], action.help)


if __name__ == "__main__":
    unittest.main()
