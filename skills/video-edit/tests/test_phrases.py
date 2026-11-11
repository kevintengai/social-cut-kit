"""Phrase Captions: Grouping, Number Joining, Spelling Fixes, Cut Safety, And The SRT And Handoff Path."""

import json
import math
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import speech
from example import example
from handoff import otio
from timeline import load, prepare, srt

FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")
WORDS = [
    (0.10, 0.30, "So"), (0.32, 0.55, "this"), (0.58, 0.80, "costs"), (0.82, 1.00, "$2"), (1.00, 1.30, ",000"),
    (1.35, 1.60, "a"), (1.62, 1.95, "month."), (2.40, 2.60, "About"), (2.62, 2.80, "3"), (2.80, 3.00, ".5"),
    (3.02, 3.30, "times"), (3.32, 3.60, "more,"), (3.62, 3.80, "or"), (3.82, 4.00, "50"), (4.00, 4.10, "%"),
    (4.12, 4.40, "of"), (4.42, 4.90, "revenue"), (4.95, 5.30, "for"), (5.32, 5.70, "kevin"), (5.72, 6.10, "tang."),
]
SHOTS = [{"asset": "main", "in": 0, "out": 2.9}, {"asset": "main", "in": 2.9, "out": 4.45, "speed": 1.25},
         {"asset": "main", "in": 4.8, "out": 6.2, "lead": 0.1}, {"asset": "main", "in": 0.3, "out": 1.4}]
# Output Of The Caption Mapper Before Phrase Options Existed, For The Fixture Above.
LEGACY = [
    {"at": 0.1, "end": 1.95, "text": "So this costs $2 ,000 a month.", "position": "bottom"},
    {"at": 2.4, "end": 2.8, "text": "About 3", "position": "bottom"},
    {"at": 2.996, "end": 4.1, "text": "times more, or 50 % of", "position": "bottom"},
    {"at": 4.383, "end": 5.533, "text": "for kevin tang.", "position": "bottom"},
    {"at": 5.653, "end": 6.633, "text": "this costs $2 ,000", "position": "bottom"},
]
OPTIONS = dict(speech.PHRASE_DEFAULTS, sentence_breaks=True, join_numbers=True, fixes=[])


def timeline(shots=SHOTS, fps=30, asset="camera.bin"):
    return {"version": 1, "title": "Phrase Fixture", "canvas": {"fps": fps},
            "assets": {"main": {"path": asset, "kind": "video"}}, "shots": [dict(shot) for shot in shots],
            "captions": [{"at": 0.5, "end": 1.0, "text": "Existing", "position": "top"}]}


def shot_frames(doc):
    """First And Last Frame Of Every Shot On The Edit's Frame Grid."""
    fps, at, spans = doc["canvas"]["fps"], 0, []
    for shot in doc["shots"]:
        length = (shot["out"] + shot.get("tail", 0) - shot.get("in", 0) + shot.get("lead", 0)) / shot.get("speed", 1)
        frames = math.floor(length * fps + 0.5)
        spans.append((at, at + frames))
        at += frames
    return spans


class WordTests(unittest.TestCase):
    def test_number_fragments_join_into_one_spoken_number(self):
        joined, count = speech.join_numbers(WORDS)
        texts = [text for _, _, text in joined]
        self.assertEqual(count, 3)
        for whole in ("$2,000", "3.5", "50%"):
            self.assertIn(whole, texts)
        self.assertEqual(next(w for w in joined if w[2] == "$2,000")[:2], (0.82, 1.30))
        cases = [
            ([(0, .2, "$"), (.2, .4, "40")], ["$40"]),
            ([(0, .2, "2,"), (.2, .5, "000")], ["2,000"]),
            ([(0, .2, "1"), (.2, .3, "st")], ["1st"]),
            ([(0, .2, "9"), (.2, .4, ":30")], ["9:30"]),
            ([(0, .2, "3."), (.2, .4, "5")], ["3.", "5"]),
            ([(0, .2, "50"), (.9, 1.0, "%")], ["50", "%"]),
            ([(0, .2, "top"), (.2, .4, ".5")], ["top", ".5"]),
            ([(0, .2, "2,"), (.2, .5, "and")], ["2,", "and"]),
        ]
        for words, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual([text for _, _, text in speech.join_numbers(words)[0]], expected)

    def test_spelling_fixes_change_caption_text_only(self):
        words = [(0, .3, "Hello,"), (.3, .6, "kevin"), (.6, .9, "TANG!"), (1, 1.2, "um"), (1.2, 1.5, "chat"),
                 (1.5, 1.8, "gpt."), (2, 2.4, "(teh)")]
        rules = speech.read_fixes(["kevin tang=Kevin Teng", "um=", "chat gpt=ChatGPT", "teh=the", "tang=Wrong"], None)
        fixed, used = speech.apply_fixes(words, rules)
        self.assertEqual([text for _, _, text in fixed], ["Hello,", "Kevin", "Teng!", "ChatGPT.", "(the)"])
        self.assertEqual(used, 4)
        self.assertEqual(fixed[3][:2], (1.2, 1.8))
        self.assertEqual(words[1][2], "kevin")
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "fixes.json"
            file.write_text(json.dumps({"gpt": "GPT"}), encoding="utf-8")
            self.assertEqual(speech.read_fixes(None, file), [(["gpt"], "GPT")])
            file.write_text(json.dumps(["gpt"]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON Object"):
                speech.read_fixes(None, file)
        with self.assertRaisesRegex(ValueError, "Heard=Shown"):
            speech.read_fixes(["no equals sign"], None)

    def test_units_with_several_words_get_estimated_word_times(self):
        words, estimated = speech.single_words([(1.0, 2.0, "one two"), (3.0, 3.4, "three")])
        self.assertEqual(estimated, 1)
        self.assertEqual([text for _, _, text in words], ["one", "two", "three"])
        self.assertEqual((words[0][0], words[1][1]), (1.0, 2.0))
        self.assertAlmostEqual(words[0][1], words[1][0])

    def test_sentence_ends_ignore_titles_initials_and_decimals(self):
        self.assertEqual([speech.ends_sentence(text) for text in ("month.", "ready?", "wow!\"", "Dr.", "J.", "3.5", "more,", "I.")],
                         [True, True, True, False, False, False, False, True])


class PhraseTests(unittest.TestCase):
    def phrases(self, words=WORDS, doc=None, **changes):
        doc = doc or timeline()
        options = dict(OPTIONS, **changes)
        if options["join_numbers"]:
            words = speech.join_numbers(words)[0]
        pieces, clamped, dropped, crossing, fps, total = speech.project_phrases(words, doc, "main")
        cues, short = speech.phrase_captions(pieces, fps, options)
        return cues, short, clamped, dropped, crossing, doc

    def test_phrases_stay_inside_their_shot_and_never_overlap(self):
        for changes in ({}, {"max_words": 2}, {"max_chars": 12}, {"min_seconds": 1.5}, {"pause": 0.05}):
            with self.subTest(changes=changes):
                cues, _, _, _, _, doc = self.phrases(**changes)
                fps, spans = doc["canvas"]["fps"], shot_frames(doc)
                previous_end = 0
                for cue in cues:
                    start, stop = cue["at"] * fps, cue["end"] * fps
                    self.assertAlmostEqual(start, round(start), places=4)
                    self.assertAlmostEqual(stop, round(stop), places=4)
                    start, stop = round(start), round(stop)
                    self.assertGreater(stop, start)
                    self.assertGreaterEqual(start, previous_end)
                    self.assertTrue(any(first <= start and stop <= last for first, last in spans), cue)
                    previous_end = stop
                self.assertLessEqual(previous_end, spans[-1][1])

    def test_limits_pauses_and_sentences_break_phrases(self):
        cues, *_ = self.phrases(max_words=3)
        self.assertEqual([cue["text"] for cue in cues][:3], ["So this costs", "$2,000 a month.", "About 3.5"])
        for cue in cues:
            self.assertLessEqual(len(cue["text"].split()), 3)
        tight, *_ = self.phrases(max_chars=12)
        for cue in tight:
            self.assertTrue(len(cue["text"]) <= 12 or " " not in cue["text"], cue)
        run_on, *_ = self.phrases(max_words=40, max_chars=400, sentence_breaks=False, pause=5)
        self.assertEqual(run_on[0]["text"], "So this costs $2,000 a month. About 3.5")
        sentences, *_ = self.phrases(max_words=40, max_chars=400, pause=5)
        self.assertEqual(sentences[0]["text"], "So this costs $2,000 a month.")
        paused, *_ = self.phrases(max_words=40, max_chars=400, sentence_breaks=False, pause=0.4)
        self.assertEqual(paused[0]["text"], "So this costs $2,000 a month.")
        split, *_ = self.phrases(join_numbers=False, max_words=40, max_chars=400)
        self.assertIn("$2 ,000", split[0]["text"])

    def test_gaps_close_and_short_phrases_extend_only_into_free_time(self):
        cues, short, *_ = self.phrases(max_words=3)
        self.assertEqual(cues[0]["end"], cues[1]["at"])
        self.assertLess(cues[1]["end"], cues[2]["at"])
        words = [(0.0, 0.1, "Yes."), (0.15, 0.6, "Go"), (2.0, 2.05, "Now.")]
        doc = timeline([{"asset": "main", "in": 0, "out": 3}])
        cues, short, *_ = self.phrases(words, doc, min_seconds=1.0)
        self.assertEqual([(cue["text"], cue["at"], cue["end"]) for cue in cues],
                         [("Yes.", 0.0, 0.166667), ("Go", 0.166667, 1.166667), ("Now.", 2.0, 3.0)])
        self.assertEqual(short, [{"text": "Yes.", "at": 0.0, "seconds": 0.166667}])
        cues, short, *_ = self.phrases(words, timeline([{"asset": "main", "in": 0, "out": 2.5}]), min_seconds=1.0)
        self.assertEqual((cues[-1]["at"], cues[-1]["end"]), (2.0, 2.5))
        self.assertEqual(short[-1]["text"], "Now.")

    def test_words_trimmed_by_a_cut_are_reported_for_a_listening_check(self):
        cues, _, clamped, dropped, crossing, _ = self.phrases()
        # "3.5" Meets Both Sides Of The Split At 2.9. "revenue" Meets The End Of Shot Two And The
        # Start Of Shot Three. "a" Meets The End Of Shot Four.
        self.assertEqual(crossing, 5)
        # The Split At 2.9 Seconds Continues One Take, So The Sound Carries Across It.
        self.assertEqual([(row["text"], row["shot"], row["trimmed"], row["sound_continues_across_cut"]) for row in clamped],
                         [("3.5", 1, "end", True)])
        kept = clamped[0]
        self.assertEqual((kept["source_seconds"], kept["kept_source_seconds"], kept["timeline_seconds"]),
                         ([2.62, 3.0], [2.62, 2.9], [2.62, 2.9]))
        # The Cut From 4.45 To 4.7 Removes The Middle Of "revenue", So Neither Side Shows It.
        self.assertEqual([(row["text"], row["shot"]) for row in dropped],
                         [("revenue", 2), ("revenue", 3), ("a", 4)])
        self.assertEqual(dropped[0]["seconds_inside_shot"], 0.03)
        texts = " ".join(cue["text"] for cue in cues)
        self.assertNotIn("revenue", texts)
        self.assertEqual(texts.count("3.5"), 1)
        # A Real Cut At 2.85 Removes The End Of "3.5". Most Of The Word Plays, So It Stays And Is Flagged.
        real_cut = timeline([{"asset": "main", "in": 0, "out": 2.85}, {"asset": "main", "in": 4.0, "out": 6.2}])
        cues, _, clamped, dropped, crossing, _ = self.phrases(doc=real_cut)
        self.assertEqual([(row["text"], row["trimmed"], row["sound_continues_across_cut"]) for row in clamped],
                         [("3.5", "end", False)])
        self.assertEqual(clamped[0]["kept_source_seconds"], [2.62, 2.85])
        self.assertEqual(([row["text"] for row in dropped], crossing), (["50%"], 2))
        # The Shot Lasts 86 Whole Frames At 30 FPS, And The Phrase Ends With It.
        self.assertEqual(max(cue["end"] for cue in cues if "3.5" in cue["text"]), round(86 / 30, 6))

    def test_speed_handles_and_repeated_shots_map_to_edit_time(self):
        cues, *_ = self.phrases(max_words=40, max_chars=400, pause=5, sentence_breaks=False)
        by_text = {cue["text"]: cue for cue in cues}
        # Shot Two Starts At 2.9 Seconds And Plays 1.25 Times Faster.
        faster = by_text["times more, or 50% of"]
        self.assertAlmostEqual(faster["at"], 2.9 + (3.02 - 2.9) / 1.25, delta=1 / 30)
        self.assertAlmostEqual(faster["end"], 2.9 + (4.40 - 2.9) / 1.25, delta=1 / 30)
        # Shot Four Replays Source Seconds 0.3 To 1.4 After 169 Frames Of Earlier Shots.
        repeat = by_text["this costs $2,000"]
        self.assertAlmostEqual(repeat["at"], 169 / 30 + (0.32 - 0.3), delta=1 / 30)
        self.assertAlmostEqual(repeat["end"], 169 / 30 + (1.30 - 0.3), delta=1 / 30)
        missing_rate = timeline()
        del missing_rate["canvas"]
        pieces, *_, fps, total = speech.project_phrases(WORDS, missing_rate, "main")
        self.assertEqual(fps, 30)
        with self.assertRaisesRegex(ValueError, "Unknown Timeline Asset"):
            speech.project_phrases(WORDS, timeline(), "other")


class CommandTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="phrase fixtures ")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.words = self.root / "words.json"
        self.words.write_text(json.dumps({"words": [{"start": s, "end": e, "text": t} for s, e, t in WORDS]}), encoding="utf-8")
        self.edit = self.root / "edit.json"
        self.edit.write_text(json.dumps(timeline()), encoding="utf-8")

    def cli(self, *arguments, edit=None, words=None):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / "speech.py"), "captions", str(words or self.words),
                               str(edit or self.edit), "--asset", "main", *map(str, arguments)], capture_output=True, text=True)

    def test_without_phrase_options_the_output_is_unchanged(self):
        done = self.cli("--output", self.root / "legacy.json")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, '{"cues": 5, "speech_units_cut_at_boundaries": 5}\n')
        self.assertEqual(json.loads((self.root / "legacy.json").read_text(encoding="utf-8")), LEGACY)
        done = self.cli("--output", self.root / "merged.json", "--with-timeline")
        merged = json.loads((self.root / "merged.json").read_text(encoding="utf-8"))
        self.assertEqual(merged["captions"], sorted(timeline()["captions"] + LEGACY, key=lambda c: c["at"]))
        self.assertEqual(done.stdout, '{"cues": 5, "speech_units_cut_at_boundaries": 5}\n')

    def test_phrase_run_reports_and_writes_cues_and_subrip(self):
        done = self.cli("--output", self.root / "phrases.json", "--phrases", "--max-words", "3",
                        "--fix", "kevin tang=Kevin Teng", "--srt", self.root / "phrases.srt", "--position", "center")
        self.assertEqual(done.returncode, 0, done.stderr)
        report = json.loads(done.stdout)
        self.assertEqual((report["mode"], report["cues"], report["joined_numbers"], report["spelling_fixes"]), ("phrases", 7, 3, 1))
        self.assertEqual(report["speech_units_cut_at_boundaries"], 5)
        self.assertEqual([row["text"] for row in report["clamped_words"]], ["3.5"])
        self.assertEqual([row["text"] for row in report["dropped_words"]], ["revenue", "revenue", "a"])
        self.assertEqual((report["estimated_word_timings"], report["below_minimum_time"]), (0, []))
        cues = json.loads((self.root / "phrases.json").read_text(encoding="utf-8"))
        self.assertEqual([cue["text"] for cue in cues], [
            "So this costs", "$2,000 a month.", "About 3.5", "times more, or", "50% of", "for Kevin Teng.",
            "this costs $2,000"])
        self.assertEqual({cue["position"] for cue in cues}, {"center"})
        subrip = (self.root / "phrases.srt").read_text(encoding="utf-8")
        self.assertTrue(subrip.startswith("1\n00:00:00,100 --> 00:00:00,833\nSo this costs\n\n2\n00:00:00,833 --> "))
        self.assertEqual(subrip.count(" --> "), 7)
        self.assertIn("for Kevin Teng.", subrip)

    def test_each_phrase_option_turns_phrases_on_and_bad_values_are_refused(self):
        for index, option in enumerate((("--max-words", "2"), ("--max-chars", "10"), ("--pause", "0.2"), ("--min-seconds", "0.5"),
                                        ("--sentence-breaks", "off"), ("--join-numbers", "off"), ("--fix", "tang=Teng"))):
            with self.subTest(option=option):
                done = self.cli("--output", self.root / f"option {index}.json", *option)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(json.loads(done.stdout)["mode"], "phrases")
        positioned = self.cli("--output", self.root / "top.json", "--position", "top")
        self.assertEqual(positioned.stdout, '{"cues": 5, "speech_units_cut_at_boundaries": 5}\n')
        self.assertEqual(json.loads((self.root / "top.json").read_text(encoding="utf-8")),
                         [dict(cue, position="top") for cue in LEGACY])
        (self.root / "taken.srt").write_text("Keep", encoding="utf-8")
        for bad in (("--max-words", "0"), ("--max-chars", "0"), ("--pause", "0"), ("--min-seconds", "-1"),
                    ("--fix", "broken"), ("--phrases", "--replace-existing"), ("--phrases", "--srt", self.root / "taken.srt")):
            with self.subTest(bad=bad):
                failed = self.cli("--output", self.root / "never.json", *bad)
                self.assertNotEqual(failed.returncode, 0)
                self.assertFalse((self.root / "never.json").exists())
        self.assertEqual((self.root / "taken.srt").read_text(encoding="utf-8"), "Keep")

    def test_subtitle_cues_are_split_with_estimated_times(self):
        subtitles = self.root / "words.srt"
        subtitles.write_text("1\n00:00:00,100 --> 00:00:01,950\nSo this costs $2,000 a month.\n", encoding="utf-8")
        done = self.cli("--output", self.root / "from srt.json", "--phrases", "--max-words", "2", words=subtitles)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["estimated_word_timings"], 1)
        texts = [cue["text"] for cue in json.loads((self.root / "from srt.json").read_text(encoding="utf-8"))]
        self.assertEqual(texts[:3], ["So this", "costs $2,000", "a month."])

    @unittest.skipUnless(FFMPEG, "FFmpeg Required")
    def test_phrase_captions_travel_through_timeline_subrip_handoff_and_the_null_sink_check(self):
        project = example(self.root / "Cut")
        doc = load(project)
        doc["assets"]["main"] = dict(doc["assets"]["First"])
        doc["shots"] = [{"asset": "main", "in": 0, "out": 2.9}, {"asset": "main", "in": 2.9, "out": 4.45}]
        doc["captions"] = [{"at": 0.25, "end": 1.5, "text": "Old Bottom Line", "position": "bottom"},
                           {"at": 0.25, "end": 1.5, "text": "Headline", "position": "top"}]
        doc["overlays"], doc["audio"] = [], []
        edit = project.with_name("uncaptioned.json")
        edit.write_text(json.dumps(doc), encoding="utf-8")
        captioned = project.with_name("captioned.json")
        done = self.cli("--output", captioned, "--with-timeline", "--replace-existing", "--phrases", "--max-words", "3", edit=edit)
        self.assertEqual(done.returncode, 0, done.stderr)
        model = prepare(load(captioned), captioned.parent)
        texts = [cue["text"] for cue in model["captions"]]
        self.assertNotIn("Old Bottom Line", texts)
        self.assertIn("Headline", texts)
        self.assertIn("$2,000 a month.", texts)
        self.assertIn("00:00:00,833 --> 00:00:01,958\n$2,000 a month.", srt(model))
        self.assertIn("$2,000 a month.", [marker["name"] for marker in otio(model)["tracks"]["markers"]])
        tool = [sys.executable, "-B", str(SCRIPTS / "edit_video.py")]
        for command, target in (("captions", "Dialogue.srt"), ("handoff", "Assembly.otio")):
            subprocess.run(tool + [command, str(captioned), str(captioned.with_name(target))], check=True, capture_output=True)
            self.assertIn("$2,000 a month.", captioned.with_name(target).read_text(encoding="utf-8"))
        checked = subprocess.run(tool + ["check", str(captioned)], capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertFalse(list(self.root.rglob("*.mp4")))


if __name__ == "__main__":
    unittest.main()
