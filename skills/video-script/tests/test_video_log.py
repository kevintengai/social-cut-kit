"""Exercise The Video Library: Records, Snapshots, Retention, The Index, And Findings."""

import argparse
from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import desk_support  # noqa: E402
import retention  # noqa: E402
import video_log  # noqa: E402

TOOL = SCRIPTS / "video_log.py"
READER = SCRIPTS / "retention.py"
FIRST = "2026-11-03-find-the-ready-repair"
THIRTY = [100, 86, 76, 70, 67, 65, 63.5, 62, 60.5, 59, 57, 51, 48, 47, 46.5, 46, 45.5,
          45, 44.5, 44, 43, 41.5, 40, 38.5, 37, 35, 32, 28, 25]
EIGHT = [100, 97, 94, 89, 83, 81, 80, 79, 78]


class LibraryCase(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="video log test ")
        self.addCleanup(folder.cleanup)
        self.work = Path(folder.name)
        self.library = self.work / "Video Library"
        self.home = self.work / "kit home"

    def run_tool(self, *args, code=0, library=True, encoding="utf-8"):
        env = dict(os.environ, PYTHONIOENCODING=encoding, SOCIAL_CUT_KIT_HOME=str(self.home))
        command = [sys.executable, "-B", str(TOOL)]
        if library:
            command += ["--library", str(self.library)]
        done = subprocess.run(command + list(map(str, args)), capture_output=True, env=env, check=False)
        out, err = done.stdout.decode(encoding), done.stderr.decode(encoding)
        self.assertEqual(done.returncode, code, err or out)
        return out.replace("\r\n", "\n"), err.replace("\r\n", "\n")

    def start(self):
        self.run_tool("init", "--platform", "Instagram Reels", "--audience", "Repair Shop Owners")

    def add_first(self):
        self.run_tool(
            "add", "--title", "Find The Ready Repair", "--posted", "2026-11-03",
            "--platform", "Instagram Reels", "--format", "Screen Demo With Voiceover",
            "--runtime", 28, "--stake", "Shop Owners Who Lose Time Hunting For Finished Jobs",
            "--first", "Which Repair Can Go Back To The Customer Today?",
            "--second", "One Filter Answers It.", "--project", "Projects/ready-repair",
            "--final", "Finals/ready-repair.mp4", "--captions", "Finals/ready-repair.srt",
        )

    def add_plain(self, title, posted, *more):
        self.run_tool("add", "--title", title, "--posted", posted, *more)
        return f"{posted}-{video_log.slug(title)}"

    def record(self, key):
        return json.loads((self.library / "videos" / f"{key}.json").read_text(encoding="utf-8"))

    def page(self, key):
        return (self.library / "videos" / f"{key}.md").read_text(encoding="utf-8")

    def report_file(self, values, name="report.json", curve=True, **options):
        a = argparse.Namespace(interval=3, count=3, at=None, reported_average=None, average_tolerance=3.0)
        vars(a).update(options)
        report, points = retention.measure([(float(i), float(v)) for i, v in enumerate(values)], None, a, None, None)
        path = self.work / name
        path.write_text(json.dumps(dict(report, curve=points) if curve else report), encoding="utf-8")
        return path

    def index_rows(self):
        out, _ = self.run_tool("index")
        return [[c.strip() for c in line.strip("|").split("|")] for line in out.splitlines() if line.startswith("| ") and "---" not in line][1:]


class Records(LibraryCase):
    def test_init_lays_out_the_library_once(self):
        out, _ = self.run_tool("init", "--platform", "Instagram Reels", "--audience", "Repair Shop Owners")
        self.assertIn("Started A Video Library At", out)
        marker = json.loads((self.library / "library.json").read_text(encoding="utf-8"))
        self.assertEqual(marker["format"], "school.video-library/1")
        self.assertEqual((marker["platform"], marker["audience"]), ("Instagram Reels", "Repair Shop Owners"))
        self.assertTrue((self.library / "videos").is_dir())
        self.assertTrue((self.library / "captures").is_dir())
        findings = json.loads((self.library / "findings.json").read_text(encoding="utf-8"))
        self.assertEqual(findings, {"format": "school.findings/1", "findings": []})
        for name in ("index.md", "findings.md", "backlog.md"):
            self.assertTrue((self.library / name).is_file(), name)
        self.assertIn("| | No Videos Yet |", (self.library / "index.md").read_text(encoding="utf-8"))
        _, err = self.run_tool("init", code=1)
        self.assertIn("A Video Library Already Exists At", err)

    def test_init_keeps_a_backlog_and_findings_that_are_already_there(self):
        self.library.mkdir()
        (self.library / "backlog.md").write_text("- [ ] 2026-01-01 | An Idea Saved Earlier\n", encoding="utf-8")
        self.run_tool("init")
        out, _ = self.run_tool("backlog", "list")
        self.assertEqual(out, "1. 2026-01-01 | An Idea Saved Earlier\n")

    def test_a_record_whose_id_and_file_name_disagree_is_reported(self):
        self.start()
        self.add_first()
        path = self.library / "videos" / f"{FIRST}.json"
        (self.library / "videos" / "renamed-by-hand.json").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        _, err = self.run_tool("index", code=1)
        self.assertIn("Needs A title And An id That Matches Its File Name, renamed-by-hand.", err)
        (self.library / "videos" / "renamed-by-hand.json").write_text("[1, 2]", encoding="utf-8")
        _, err = self.run_tool("index", code=1)
        self.assertIn("Expected A Video Record In", err)

    def test_commands_need_a_library(self):
        _, err = self.run_tool("index", code=1)
        self.assertIn("No Video Library At", err)
        self.assertIn("Start One With The init Command.", err)
        _, err = self.run_tool("index", code=1, library=False)
        self.assertEqual(err, "Name The Library Folder With --library, Or Create A Defaults File That Names It.\n")

    def test_add_a_posted_video(self):
        self.start()
        self.add_first()
        record = self.record(FIRST)
        self.assertEqual(record["format"], "school.video/1")
        self.assertEqual((record["id"], record["kind"], record["posted"]), (FIRST, "posted", "2026-11-03"))
        self.assertEqual(record["video_format"], "Screen Demo With Voiceover")
        self.assertEqual(record["runtime_seconds"], 28.0)
        self.assertEqual(record["opening"], {"first": "Which Repair Can Go Back To The Customer Today?", "second": "One Filter Answers It."})
        self.assertEqual(record["links"], {"project": "Projects/ready-repair", "final": "Finals/ready-repair.mp4", "captions": "Finals/ready-repair.srt"})
        self.assertEqual((record["snapshots"], record["retention"]), ([], []))
        page = self.page(FIRST)
        self.assertIn("# Find The Ready Repair\n", page)
        self.assertIn("- Status: Posted 2026-11-03\n", page)
        self.assertIn("- Runtime: 28 Seconds\n", page)
        self.assertIn("- Second Sentence: One Filter Answers It.\n", page)
        _, err = self.run_tool("add", "--title", "Find The Ready Repair", "--posted", "2026-11-03", code=1)
        self.assertIn(f"A Record Named {FIRST} Already Exists.", err)
        self.run_tool("add", "--title", "Find The Ready Repair", "--posted", "2026-11-03", "--id", "ready-repair-second-cut")
        self.assertEqual(self.record("ready-repair-second-cut")["title"], "Find The Ready Repair")

    def test_unknown_values_are_stored_as_not_captured(self):
        self.start()
        key = self.add_plain("Bare Record", "2026-10-01")
        record = self.record(key)
        for name in ("platform", "video_format", "runtime_seconds", "stake"):
            self.assertIsNone(record[name], name)
        self.assertEqual(record["opening"], {"first": None, "second": None})
        self.assertEqual(record["links"], {"project": None, "final": None, "captions": None})
        page = self.page(key)
        for label in ("Platform", "Format", "Runtime", "Stake", "First Sentence", "Captions"):
            self.assertIn(f"- {label}: Not Captured\n", page)

    def test_an_unposted_video_is_a_review_not_evidence(self):
        self.start()
        out, _ = self.run_tool("add", "--title", "Why The Queue Looks Empty", "--review")
        key = f"{date.today().isoformat()}-why-the-queue-looks-empty"
        self.assertIn(f"Added {key} As A Review Record, Not Evidence", out)
        record = self.record(key)
        self.assertEqual((record["kind"], record["posted"]), ("review", None))
        self.assertIn("- Status: Review, Not Evidence. This Video Is Unposted.\n", self.page(key))
        self.assertIn("None. A Review Holds No Audience Numbers.", self.page(key))
        for extra in ([], ["--posted", "2026-11-01", "--review"]):
            _, err = self.run_tool("add", "--title", "Unclear", *extra, code=1)
            self.assertIn("Supply --posted With The Posting Date, Or Mark An Unposted Video With --review.", err)
        _, err = self.run_tool("snapshot", key, "--views", 10, code=1)
        self.assertIn("Is A Review Of An Unposted Video.", err)
        out, _ = self.run_tool("update", key, "--posted", "2026-11-12", "--runtime", "0:31")
        self.assertIn("Status: Posted, No Numbers", out)
        record = self.record(key)
        self.assertEqual((record["kind"], record["posted"], record["runtime_seconds"]), ("posted", "2026-11-12", 31.0))
        self.run_tool("snapshot", key, "--captured", "2026-11-13", "--views", 10)

    def test_ids_are_built_from_plain_letters(self):
        self.assertEqual(video_log.slug("Café Déjà Vu: 100% Ready!"), "cafe-deja-vu-100-ready")
        self.assertEqual(video_log.slug("修理"), "video")
        self.assertLessEqual(len(video_log.slug("Word " * 40)), 48)
        self.start()
        _, err = self.run_tool("add", "--title", "Bad ID", "--posted", "2026-11-01", "--id", "Has Spaces", code=1)
        self.assertIn("A Video ID Uses Lower-Case Letters, Digits, And Hyphens", err)
        _, err = self.run_tool("show", "no-such-video", code=1)
        self.assertIn("No Video Record Named no-such-video.", err)
        _, err = self.run_tool("add", "--title", "Bad Date", "--posted", "Tuesday", code=1)
        self.assertIn("Write The Posting Date As 2026-11-05 Or 2026-11-05 09:30.", err)

    def test_update_changes_clears_and_notes(self):
        self.start()
        self.add_first()
        self.run_tool("update", FIRST, "--title", "Find The Ready Repair Fast", "--platform", "", "--runtime", 29.5, "--note", "Recut With A Shorter Close")
        record = self.record(FIRST)
        self.assertEqual(record["title"], "Find The Ready Repair Fast")
        self.assertIsNone(record["platform"])
        self.assertEqual(record["runtime_seconds"], 29.5)
        self.assertEqual(record["notes"][0]["text"], "Recut With A Shorter Close")
        page = self.page(FIRST)
        self.assertIn("- Runtime: 29.5 Seconds\n", page)
        self.assertIn("## Notes\n", page)
        _, err = self.run_tool("update", FIRST, "--runtime", 0, code=1)
        self.assertIn("Write A Runtime Above Zero Seconds.", err)

    def test_non_ascii_titles_survive_storage_and_a_narrow_console(self):
        self.start()
        self.run_tool("add", "--title", "Café → 修理", "--posted", "2026-11-02", "--id", "cafe-arrow")
        self.assertEqual(self.record("cafe-arrow")["title"], "Café → 修理")
        self.assertIn("# Café → 修理\n", self.page("cafe-arrow"))
        out, _ = self.run_tool("show", "cafe-arrow", encoding="cp1252")
        self.assertIn("# Café \\u2192 \\u4fee\\u7406", out)


class Snapshots(LibraryCase):
    def setUp(self):
        super().setUp()
        self.start()
        self.add_first()

    def full(self, *more, code=0):
        return self.run_tool(
            "snapshot", FIRST, "--captured", "2026-11-05 09:30", "--views", "12,840",
            "--viewers", 11020, "--average-watch", 9.4, "--follows", 31, "--likes", 402,
            "--comments", 18, "--shares", 55, "--saves", 61, "--reposts", 4,
            "--rate", "Skip Rate", "41.2%", "--rate", "Watched Full Video", 12.5,
            "--source", "Feed", "71%", "--source", "Explore", "2,311", "--source", "Profile", "6%",
            "--non-follower-share", "87.5%", "--note", "Read From The Insights Screen", *more,
            code=code,
        )

    def test_every_number_is_recorded_with_its_label(self):
        out, _ = self.full()
        self.assertEqual(out, f"Recorded A Snapshot Of {FIRST} Captured 2026-11-05 09:30\n")
        snap = self.record(FIRST)["snapshots"][0]
        self.assertEqual(snap["captured"], "2026-11-05T09:30")
        self.assertEqual([snap[name] for name in video_log.COUNTS], [12840, 11020, 31, 402, 18, 55, 61, 4])
        self.assertEqual(snap["average_watch_seconds"], 9.4)
        self.assertEqual(snap["non_follower_share_pct"], 87.5)
        self.assertIsNone(snap["follower_share_pct"])
        self.assertEqual(snap["rates"], [{"label": "Skip Rate", "percent": 41.2}, {"label": "Watched Full Video", "percent": 12.5}])
        self.assertEqual(
            snap["sources"],
            [
                {"label": "Feed", "views": None, "share_pct": 71.0},
                {"label": "Explore", "views": 2311, "share_pct": None},
                {"label": "Profile", "views": None, "share_pct": 6.0},
            ],
        )
        self.assertEqual(snap["note"], "Read From The Insights Screen")
        self.assertEqual(snap["not_captured"], [])
        page = self.page(FIRST)
        self.assertIn("| 2026-11-05 09:30 | Day 2 | 12,840 | 11,020 | 9.4 Seconds | 31 | 402 | 18 | 55 | 61 | 4 | 87.5% |", page)
        self.assertIn("- 2026-11-05 09:30 Rates: Skip Rate 41.2%. Watched Full Video 12.5%.", page)
        self.assertIn("- 2026-11-05 09:30 Views By Source: Feed 71%. Explore 2,311 Views. Profile 6%.", page)
        self.assertIn("| Average Watch As A Share Of Runtime | 33.6% | Snapshot 2026-11-05 09:30 |", page)
        self.assertIn("| Non-Follower Share Of Views | 87.5% | Snapshot 2026-11-05 09:30 |", page)
        self.assertIn("| Follows Per 1,000 Viewers | 2.81 | Snapshot 2026-11-05 09:30 |", page)
        self.assertIn("| Still Watching At 10 Seconds | Not Captured |", page)

    def test_missing_numbers_are_never_guessed(self):
        out, _ = self.run_tool("snapshot", FIRST, "--captured", "2026-11-04", "--views", "12.8K", "--follower-share", 40)
        self.assertIn("Not Captured: Viewers, Follows, Likes, Comments, Shares, Saves, Reposts, Average Watch", out)
        snap = self.record(FIRST)["snapshots"][0]
        self.assertEqual(snap["views"], 12800)
        self.assertEqual(snap["shown"], {"views": "12.8K"})
        self.assertEqual(
            snap["not_captured"],
            ["viewers", "follows", "likes", "comments", "shares", "saves", "reposts", "average_watch_seconds"],
        )
        for name in video_log.COUNTS[1:] + ("average_watch_seconds", "non_follower_share_pct"):
            self.assertIn(name, snap)
            self.assertIsNone(snap[name], name)
        page = self.page(FIRST)
        self.assertIn("| 2026-11-04 | Day 1 | 12,800 | Not Captured | Not Captured | Not Captured |", page)
        self.assertIn("- 2026-11-04 Entered In Rounded Form: Views 12.8K.", page)
        self.assertIn("| Non-Follower Share Of Views | 60.0% | Snapshot 2026-11-04 |", page)
        self.assertIn("| Follows Per 1,000 Viewers | Not Captured |", page)
        self.assertIn("| Average Watch As A Share Of Runtime | Not Captured |", page)

    def test_number_forms(self):
        self.assertEqual(video_log.whole("12,840", "Views"), (12840, None))
        self.assertEqual(video_log.whole("1.2M", "Views"), (1200000, "1.2M"))
        self.assertEqual(video_log.whole("12,8k", "Views"), (12800, "12,8k"))
        self.assertEqual(video_log.whole("1,234K", "Views"), (1234000, "1,234K"))
        self.assertEqual(video_log.percent("87,5 %", "A Share"), 87.5)
        self.assertEqual(video_log.duration("1:02.5", "Runtime"), 62.5)
        self.assertEqual(video_log.duration("9.4s", "Runtime"), 9.4)
        for bad in ("12.5", "12,84", "many", "-3", ""):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "Whole Count"):
                video_log.whole(bad, "Views")
        for flag, value, message in (
            ("--views", "12.5", "Write Views As A Whole Count Such As 12840, 12,840, Or 12.8K."),
            ("--average-watch", "soon", "Average Watch Time: Enter Seconds Such As 28, 28.5, Or 0:28."),
            ("--rate", ["Skip Rate", "high"], "Write Skip Rate As A Percent Such As 87.5 Or 87.5%."),
            ("--source", ["Feed", "lots"], "Write Feed Views As A Whole Count Such As 12840, 12,840, Or 12.8K."),
            ("--non-follower-share", "140", "The Non-Follower Share Cannot Exceed 100 Percent."),
            ("--non-follower-share", "most", "Write The Non-Follower Share As A Percent Such As 87.5 Or 87.5%."),
            ("--captured", "yesterday", "Write The Capture Time As 2026-11-05 Or 2026-11-05 09:30."),
            ("--captured", "2026-11-01", "The Snapshot Is Dated Before The Video Was Posted."),
        ):
            with self.subTest(flag=flag, value=value):
                extra = [] if flag == "--captured" else ["--captured", "2026-11-05"]
                more = ["--views", 5] if flag == "--captured" else []
                values = value if isinstance(value, list) else [value]
                _, err = self.run_tool("snapshot", FIRST, flag, *values, *extra, *more, code=1)
                self.assertEqual(err, message + "\n")
        _, err = self.run_tool("snapshot", FIRST, "--captured", "2026-11-05", "--note", "Nothing Read", code=1)
        self.assertEqual(err, "Supply At Least One Number From The Analytics Screen.\n")
        self.assertEqual(self.record(FIRST)["snapshots"], [])

    def test_snapshots_keep_their_capture_times(self):
        self.full()
        _, err = self.full(code=1)
        self.assertIn("A Snapshot Captured 2026-11-05 09:30 Already Exists. Pass --replace To Overwrite It.", err)
        self.full("--replace")
        self.assertEqual(len(self.record(FIRST)["snapshots"]), 1)
        self.run_tool("snapshot", FIRST, "--captured", "2026-11-10T08:00:00+08:00", "--views", 20100)
        self.run_tool("snapshot", FIRST, "--captured", "2026-11-04", "--views", 9000)
        stamps = [snap["captured"] for snap in self.record(FIRST)["snapshots"]]
        self.assertEqual(stamps, ["2026-11-04", "2026-11-05T09:30", "2026-11-10T08:00+08:00"])
        row = self.index_rows()[0]
        self.assertEqual((row[5], row[6], row[10]), ("20,100", "Not Captured", "Measured Day 7"))
        self.assertIn("| Average Watch As A Share Of Runtime | Not Captured |", self.page(FIRST))
        old = self.add_plain("An Older Video", "2020-01-01")
        out, _ = self.run_tool("snapshot", old, "--views", 20500)
        self.assertIn("The Capture Time Was Set To Now. Pass --captured When The Numbers Were Read Earlier.", out)
        self.assertTrue(self.record(old)["snapshots"][0]["captured"].startswith(date.today().isoformat()))


class Retention(LibraryCase):
    def setUp(self):
        super().setUp()
        self.start()
        self.add_first()

    def test_attach_a_report_made_by_the_retention_tool(self):
        saved = self.work / "retention.json"
        done = subprocess.run(
            [sys.executable, "-B", str(READER), "csv", str(SKILL / "assets" / "practice-retention.csv"),
             "--reported-average", "14.2", "--output", str(saved)],
            capture_output=True, check=False,
        )
        self.assertEqual(done.returncode, 0, done.stderr)
        out, _ = self.run_tool("attach", FIRST, saved, "--captured", "2026-11-05 09:30")
        self.assertEqual(out, f"Attached Retention To {FIRST} Captured 2026-11-05 09:30\n")
        entry = self.record(FIRST)["retention"][0]
        self.assertEqual((entry["captured"], entry["report"]), ("2026-11-05T09:30", "retention.json"))
        self.assertEqual(entry["duration_seconds"], 28.0)
        self.assertEqual(entry["readings"][4], {"seconds": 10, "retention_pct": 57.0})
        self.assertEqual(entry["drop_3_to_10_points"], 13.0)
        self.assertEqual(entry["reported_average_seconds"], 14.2)
        self.assertEqual(len(entry["curve"]), 29)
        page = self.page(FIRST)
        self.assertIn("## Retention\n\n### 2026-11-05 09:30\n", page)
        self.assertIn("| Seconds | 1 | 2 | 3 | 5 | 10 | 15 | 20 |", page)
        self.assertIn("| Still Watching | 86.0% | 76.0% | 70.0% | 65.0% | 57.0% | 46.0% | 43.0% |", page)
        self.assertIn("- Area-Based Average Watch: 14.41 Seconds, 51.5% Of Runtime. The App Reported 14.2 Seconds.", page)
        self.assertIn("- Drop From 3 To 10 Seconds: 13 Points.", page)
        self.assertIn("- Steepest Drops: 0 To 2.25 Seconds (-25.5 Points).", page)
        self.assertIn("- Flattest Stretches: 12.5 To 19.5 Seconds (-4 Points).", page)
        self.assertIn("| Still Watching At 10 Seconds | 57.0% | Retention 2026-11-05 09:30 |", page)
        self.assertIn("| Drop From 3 To 10 Seconds | 13 Points | Retention 2026-11-05 09:30 |", page)
        row = self.index_rows()[0]
        self.assertEqual((row[7], row[10]), ("57.0%", "Retention Only"))

    def test_a_report_with_values_that_are_not_numbers_is_refused(self):
        bad = self.work / "bad.json"
        bad.write_text(
            json.dumps({"readings": [{"seconds": "x", "retention_pct": 5}], "duration_seconds": "30", "curve": [[1]]}),
            encoding="utf-8",
        )
        _, err = self.run_tool("attach", FIRST, bad, code=1)
        self.assertIn("Holds Values That Are Not Numbers.", err)
        self.assertEqual(self.record(FIRST)["retention"], [])
        self.run_tool("index")

    def test_attach_guards(self):
        report = self.report_file(THIRTY)
        self.run_tool("attach", FIRST, report, "--captured", "2026-11-05")
        _, err = self.run_tool("attach", FIRST, report, "--captured", "2026-11-05", code=1)
        self.assertIn("Is Already Attached. Pass --replace To Overwrite It.", err)
        self.run_tool("attach", FIRST, report, "--captured", "2026-11-05", "--replace")
        self.assertEqual(len(self.record(FIRST)["retention"]), 1)
        other = self.work / "other.json"
        other.write_text(json.dumps({"format": "school.script/1"}), encoding="utf-8")
        _, err = self.run_tool("attach", FIRST, other, code=1)
        self.assertIn("Is Not A Retention Report.", err)
        self.assertIn("Create One With retention.py And Its --output Option.", err)
        self.run_tool("add", "--title", "Draft Cut", "--review", "--id", "draft-cut")
        _, err = self.run_tool("attach", "draft-cut", report, code=1)
        self.assertIn("It Has No Retention To Attach.", err)

    def test_attach_warns_about_mismatches_and_carries_report_warnings(self):
        short = self.report_file(EIGHT, "short.json", reported_average=2.0)
        out, _ = self.run_tool("attach", FIRST, short, "--captured", "2026-11-06")
        self.assertIn("Warning: The Report Covers 8 Seconds But The Record's Runtime Is 28 Seconds.", out)
        self.assertIn("Warning Carried From The Report: The Area Under The Curve Implies", out)
        self.assertIn("- Warning: The Area Under The Curve Implies 6.92 Seconds", self.page(FIRST))
        key = self.add_plain("No Runtime Yet", "2026-11-01")
        out, _ = self.run_tool("attach", key, short, "--captured", "2026-11-06")
        self.assertIn("The Record Has No Runtime. Set It With update --runtime.", out)

    def test_caption_files_are_read_in_both_common_forms(self):
        srt = self.work / "cut.srt"
        srt.write_text(
            "1\n00:00:00,000 --> 00:00:02,400\nFirst Line\nWraps Here\n\n"
            "2\n01:00:03,5 --> 01:00:05,000\n<i>Second</i> Line\n",
            encoding="utf-8-sig",
        )
        self.assertEqual(
            video_log.caption_cues(srt),
            [(0.0, 2.4, "First Line Wraps Here"), (3603.5, 3605.0, "Second Line")],
        )
        vtt = self.work / "cut.vtt"
        vtt.write_text(
            "WEBVTT\n\nNOTE Made For A Test\n\nintro\n00:01.250 --> 00:03.000 align:start\n"
            "<v Host>Hello <00:02.000>There\n\n00:00:04.000 --> 00:00:05.000\n\n",
            encoding="utf-8",
        )
        self.assertEqual(video_log.caption_cues(vtt), [(1.25, 3.0, "Hello There")])

    def test_lineup_quotes_captions_beside_each_drop_and_flat_stretch(self):
        report = self.report_file(THIRTY)
        self.run_tool("attach", FIRST, report, "--captured", "2026-11-05 09:30")
        captions = SKILL / "assets" / "practice-captions.srt"
        out, _ = self.run_tool("lineup", FIRST, "--captions", captions)
        lines = out.splitlines()
        self.assertEqual(lines[0], "| Stretch | Change | Said Just Before And During | Shown | Reading |")
        self.assertEqual(lines[2], '| Drop, 0 To 2.25 Seconds | -25.5 Points | 0: "Your Repair Was Ready Two Days Ago." | | |')
        self.assertEqual(
            lines[3],
            '| Drop, 9.75 To 11.5 Seconds | -8 Points | 6: "Forty Jobs Share One List," '
            '8.3: "So A Finished One Hides Between Two Broken Ones." 11: "Here Is The Fix." | | |',
        )
        self.assertTrue(lines[4].startswith("| Flat, 12.5 To 19.5 Seconds | -4 Points | "))
        self.assertTrue(lines[5].startswith("| Drop, 24.5 To 28 Seconds | -11 Points | "))
        self.assertIn('25: "Open The Demo And Try It."', lines[5])
        self.assertIn(f"Quotes And Times Come From {captions}.", out)
        self.assertIn("Retention Was Captured 2026-11-05 09:30.", out)
        out, _ = self.run_tool("lineup", FIRST, "--captions", captions, "--before", 0)
        self.assertEqual(
            out.splitlines()[3],
            '| Drop, 9.75 To 11.5 Seconds | -8 Points | 8.3: "So A Finished One Hides Between '
            'Two Broken Ones." 11: "Here Is The Fix." | | |',
        )

    def test_lineup_uses_the_linked_captions_and_refuses_to_guess(self):
        _, err = self.run_tool("lineup", FIRST, code=1)
        self.assertIn(f"No Retention Is Attached To {FIRST}.", err)
        self.run_tool("attach", FIRST, self.report_file(THIRTY), "--captured", "2026-11-05")
        _, err = self.run_tool("lineup", FIRST, code=1)
        self.assertIn(f"No Captions File Was Found For {FIRST}.", err)
        self.assertIn("Do Not Quote From Memory.", err)
        (self.library / "captures" / "cut.srt").write_text(
            "1\n00:00:09,000 --> 00:00:10,500\nA Line Before The Drop\n", encoding="utf-8"
        )
        self.run_tool("update", FIRST, "--captions", "captures/cut.srt")
        out, _ = self.run_tool("lineup", FIRST)
        self.assertIn('| Drop, 9.75 To 11.5 Seconds | -8 Points | 9: "A Line Before The Drop" | | |', out)
        self.assertIn("| Drop, 0 To 2.25 Seconds | -25.5 Points | No Captions In This Stretch | | |", out)
        (self.library / "captures" / "cut.srt").write_text("No Timings Here\n", encoding="utf-8")
        _, err = self.run_tool("lineup", FIRST, code=1)
        self.assertIn("Holds No Timed Captions In SRT Or WebVTT Form.", err)
        steady = self.add_plain("Steady Video", "2026-11-01", "--runtime", 30)
        self.run_tool("attach", steady, self.report_file([100 - 2 * i for i in range(31)], "steady.json"), "--captured", "2026-11-02")
        out, _ = self.run_tool("lineup", steady, "--captions", SKILL / "assets" / "practice-captions.srt")
        self.assertEqual(out, "No Steep Drop Or Flat Stretch Stood Out In This Curve. Read It As A Steady Slope.\n")

    def test_a_redirected_report_without_a_curve_still_attaches(self):
        report = self.report_file(THIRTY, "plain.json", curve=False)
        report.write_bytes(report.read_text(encoding="utf-8").encode("utf-16"))
        out, _ = self.run_tool("attach", FIRST, report, "--captured", "2026-11-05")
        self.assertIn("The Report Has No Curve, So compare Can Only Use Its Listed Seconds.", out)
        entry = self.record(FIRST)["retention"][0]
        self.assertIsNone(entry["curve"])
        self.assertEqual(video_log.level_at(entry, 10), 57.0)
        self.assertIsNone(video_log.level_at(entry, 12))
        self.assertEqual(video_log.level_at(entry, 40), video_log.PAST)


class IndexAndCompare(LibraryCase):
    def setUp(self):
        super().setUp()
        self.start()
        self.add_first()
        self.run_tool(
            "snapshot", FIRST, "--captured", "2026-11-05 09:30", "--views", 12840, "--viewers", 11020,
            "--average-watch", 9.4, "--follows", 31, "--non-follower-share", 87.5,
        )
        self.run_tool("attach", FIRST, self.report_file(THIRTY), "--captured", "2026-11-05 09:30")
        self.short = self.add_plain("Three Jobs, One Filter", "2026-10-20", "--format", "Screen Demo With Voiceover", "--runtime", 8)
        self.run_tool("attach", self.short, self.report_file(EIGHT, "eight.json"), "--captured", "2026-10-27")
        self.bare = self.add_plain("Queue Tour", "2026-11-08", "--format", "Talking Head")
        self.run_tool("add", "--title", "Why The Queue Looks Empty", "--review", "--id", "why-the-queue-looks-empty")

    def test_index_is_newest_first_with_derived_columns(self):
        rows = self.index_rows()
        self.assertEqual([row[11] for row in rows], ["`why-the-queue-looks-empty`", f"`{self.bare}`", f"`{FIRST}`", f"`{self.short}`"])
        self.assertEqual(
            rows[2],
            [
                "2026-11-03", f"[Find The Ready Repair](videos/{FIRST}.md)", "Instagram Reels",
                "Screen Demo With Voiceover", "28 Seconds", "12,840", "33.6%", "57.0%", "87.5%", "2.81",
                "Measured Day 2", f"`{FIRST}`",
            ],
        )
        self.assertEqual(rows[0][0], "Unposted")
        self.assertEqual(rows[0][10], "Review, Not Evidence")
        self.assertEqual(rows[0][5:10], ["Not Captured"] * 5)
        self.assertEqual(rows[1][10], "Posted, No Numbers")
        self.assertEqual((rows[3][7], rows[3][10]), ("Past The End", "Retention Only"))
        text = (self.library / "index.md").read_text(encoding="utf-8")
        self.assertIn("Platform: Instagram Reels. Audience: Repair Shop Owners.", text)
        self.assertIn("4 Records: 3 Posted, 1 Under Review. Newest First.", text)
        self.assertIn("Not Captured Means The Number Was Never Recorded.", text)

    def test_index_rebuilds_readable_files_from_hand_edited_json(self):
        path = self.library / "videos" / f"{self.bare}.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["title"] = "Queue Tour, Recut"
        path.write_text(json.dumps(record), encoding="utf-8")
        (self.library / "videos" / f"{self.bare}.md").unlink()
        rows = self.index_rows()
        self.assertEqual(rows[1][1], f"[Queue Tour, Recut](videos/{self.bare}.md)")
        self.assertIn("# Queue Tour, Recut\n", self.page(self.bare))
        out, _ = self.run_tool("show", self.bare)
        self.assertEqual(out, self.page(self.bare))

    def test_compare_reads_several_videos_at_the_same_seconds(self):
        out, _ = self.run_tool("compare", FIRST, self.short, self.bare)
        lines = out.splitlines()
        self.assertEqual(lines[0], "| Seconds | Find The Ready Repair (2026-11-03) | Three Jobs, One Filter (2026-10-20) | Queue Tour (2026-11-08) |")
        self.assertEqual(lines[2], "| 1 | 86.0% | 97.0% | Not Captured |")
        self.assertEqual(lines[4], "| 3 | 70.0% | 89.0% | Not Captured |")
        self.assertEqual(lines[6], "| 10 | 57.0% | Past The End | Not Captured |")
        self.assertEqual(lines[8], "| 20 | 43.0% | Past The End | Not Captured |")
        self.assertEqual(lines[9], "| Drop From 3 To 10 Seconds | 13 Points | Past The End | Not Captured |")
        self.assertEqual(lines[10], "| Average Watch Share | 33.6% | Not Captured | Not Captured |")
        self.assertEqual(lines[11], "| Runtime | 28 Seconds | 8 Seconds | Not Captured |")
        self.assertIn(f"No Retention Is Attached To: {self.bare}", out)
        self.assertIn("These Videos Use Different Formats.", out)
        out, _ = self.run_tool("compare", FIRST, self.short, "--at", 7, 2.5)
        self.assertEqual(out.splitlines()[2:4], ["| 2.5 | 73.0% | 91.5% |", "| 7 | 62.0% | 79.0% |"])
        self.assertNotIn("Different Formats", out)
        _, err = self.run_tool("compare", FIRST, code=1)
        self.assertEqual(err, "Name At Least Two Videos To Compare.\n")
        _, err = self.run_tool("compare", FIRST, "missing-video", code=1)
        self.assertIn("No Video Record Named missing-video.", err)

    def test_library_option_may_follow_the_command(self):
        out, _ = self.run_tool("show", FIRST, "--library", self.library, library=False)
        self.assertIn("# Find The Ready Repair", out)


class Findings(LibraryCase):
    def setUp(self):
        super().setUp()
        self.start()
        self.videos = []
        for day, title in ((1, "Question Open One"), (2, "Question Open Two"), (3, "Count Open One"), (4, "Count Open Two")):
            key = self.add_plain(title, f"2026-10-0{day}", "--runtime", 30)
            self.run_tool("snapshot", key, "--captured", f"2026-10-1{day}", "--views", 1000 * day)
            self.videos.append(key)
        self.run_tool("finding", "add", "A Question About Today's Work Holds More Viewers At Ten Seconds Than A Count.")

    def finding(self, key="F01"):
        data = json.loads((self.library / "findings.json").read_text(encoding="utf-8"))
        return next(item for item in data["findings"] if item["id"] == key)

    def cite(self, video, direction, *more, key="F01", code=0):
        return self.run_tool("finding", "evidence", key, video, direction, "--note", "Held 58 Percent At 10 Seconds.", *more, code=code)

    def test_status_changes_only_when_two_videos_agree(self):
        self.assertEqual(self.finding()["status"], "open")
        out, _ = self.cite(self.videos[0], "supports")
        self.assertEqual(out, "Recorded Evidence For F01. Supporting Videos: 1. Weakening Videos: 0. Status: Open\n")
        _, err = self.run_tool("finding", "status", "F01", "supported", code=1)
        self.assertEqual(err, "F01 Stays Open. A Status Changes Only When At Least Two Videos Agree. Supporting Videos: 1. Weakening Videos: 0.\n")
        self.assertEqual(self.finding()["status"], "open")
        out, _ = self.cite(self.videos[1], "supports")
        self.assertIn("Two Or More Videos Now Agree. If The Evidence Holds, Run: finding status F01 supported", out)
        self.assertEqual(self.finding()["status"], "open")
        out, _ = self.run_tool("finding", "status", "F01", "supported")
        self.assertEqual(out, "F01 Is Now Supported. Supporting Videos: 2. Weakening Videos: 0.\n")
        finding = self.finding()
        self.assertEqual(finding["status"], "supported")
        self.assertEqual(finding["history"][0]["supports"], self.videos[:2])
        self.assertEqual((finding["history"][0]["from"], finding["history"][0]["to"]), ("open", "supported"))
        _, err = self.run_tool("finding", "status", "F01", "supported", code=1)
        self.assertEqual(err, "F01 Is Already Supported.\n")
        text = (self.library / "findings.md").read_text(encoding="utf-8")
        self.assertIn("## Supported\n\n### F01. A Question About Today's Work Holds More Viewers", text)
        self.assertIn(f"- Status: Supported Since {date.today().isoformat()}. Supporting Videos: 2. Weakening Videos: 0.", text)
        self.assertIn(f"- Supports: [Question Open One](videos/{self.videos[0]}.md), Posted 2026-10-01. Held 58 Percent At 10 Seconds.", text)
        self.assertIn("## Open Hypotheses\n\nNone Yet.", text)
        self.assertIn("## Findings\n\n- F01 (Supported): Supports. Held 58 Percent At 10 Seconds.", self.page(self.videos[0]))

    def test_one_video_counts_once_and_split_evidence_blocks_a_change(self):
        self.cite(self.videos[0], "supports")
        _, err = self.cite(self.videos[0], "supports", code=1)
        self.assertIn(f"F01 Already Cites {self.videos[0]}. Pass --replace To Correct That Entry.", err)
        self.cite(self.videos[1], "supports")
        self.cite(self.videos[2], "weakens")
        self.cite(self.videos[3], "weakens")
        for target in ("supported", "weakened"):
            _, err = self.run_tool("finding", "status", "F01", target, code=1)
            self.assertEqual(err, "F01 Stays Open. The Agreeing Videos Must Outnumber The Others. Supporting Videos: 2. Weakening Videos: 2.\n")
        self.assertEqual(len(self.finding()["evidence"]), 4)

    def test_a_settled_finding_reopens_or_flips_only_on_two_videos(self):
        self.cite(self.videos[0], "supports")
        self.cite(self.videos[1], "supports")
        self.run_tool("finding", "status", "F01", "supported")
        self.cite(self.videos[2], "weakens")
        _, err = self.run_tool("finding", "status", "F01", "open", code=1)
        self.assertIn("F01 Stays Supported. A Status Changes Only When At Least Two Videos Agree.", err)
        self.cite(self.videos[3], "weakens")
        self.run_tool("finding", "status", "F01", "open")
        self.assertEqual(self.finding()["status"], "open")
        self.assertEqual(len(self.finding()["history"]), 2)

    def test_a_correction_that_removes_the_basis_returns_the_finding_to_open(self):
        self.cite(self.videos[2], "weakens")
        self.cite(self.videos[3], "weakens")
        out, _ = self.run_tool("finding", "status", "F01", "weakened")
        self.assertIn("F01 Is Now Weakened.", out)
        out, _ = self.cite(self.videos[3], "supports", "--replace")
        self.assertIn("Supporting Videos: 1. Weakening Videos: 1. Status: Open", out)
        self.assertIn("F01 Returned To Open Because Fewer Than Two Videos Still Agree With Its Earlier Status.", out)
        finding = self.finding()
        self.assertEqual(finding["status"], "open")
        self.assertEqual(finding["history"][-1]["reason"], "Fewer Than Two Videos Still Agree")
        self.assertEqual([proof["direction"] for proof in finding["evidence"]], ["weakens", "supports"])

    def test_evidence_from_a_removed_record_no_longer_counts(self):
        self.cite(self.videos[0], "supports")
        self.cite(self.videos[1], "supports")
        for suffix in (".json", ".md"):
            (self.library / "videos" / (self.videos[1] + suffix)).unlink()
        _, err = self.run_tool("finding", "status", "F01", "supported", code=1)
        self.assertIn("Supporting Videos: 1. Weakening Videos: 0.", err)
        out, _ = self.run_tool("finding", "--library", self.library, "list", library=False)
        self.assertIn("(Record Missing)", out)
        self.assertIn("- Status: Open. Supporting Videos: 1. Weakening Videos: 0.", out)

    def test_evidence_must_be_a_posted_video_with_numbers(self):
        self.run_tool("add", "--title", "Draft Cut", "--review", "--id", "draft-cut")
        _, err = self.cite("draft-cut", "supports", code=1)
        self.assertEqual(err, "draft-cut Is A Review Of An Unposted Video. A Review Is Not Evidence.\n")
        bare = self.add_plain("No Numbers Yet", "2026-10-09")
        _, err = self.cite(bare, "supports", code=1)
        self.assertIn("Has No Recorded Numbers. Record A Snapshot Or Attach Retention Before Citing It As Evidence.", err)
        _, err = self.cite("missing-video", "supports", code=1)
        self.assertIn("No Video Record Named missing-video.", err)
        _, err = self.cite(self.videos[0], "supports", key="F09", code=1)
        self.assertIn("No Finding Named F09.", err)
        _, err = self.run_tool("finding", "evidence", "F01", self.videos[0], "supports", "--note", " ", code=1)
        self.assertEqual(err, "State The Number That Makes This Video Evidence In --note.\n")
        self.assertEqual(self.finding()["evidence"], [])

    def test_a_missing_or_malformed_findings_file_is_handled(self):
        path = self.library / "findings.json"
        path.write_text('{"format": "school.findings/1", "findings": [{"id": "F01"}]}', encoding="utf-8")
        _, err = self.run_tool("finding", "list", code=1)
        self.assertIn("Needs An id And A hypothesis.", err)
        path.write_text('{"format": "school.findings/1", "findings": [', encoding="utf-8")
        _, err = self.run_tool("index", code=1)
        self.assertIn("Is Not Valid JSON Near Line 1, Column", err)
        path.unlink()
        out, _ = self.run_tool("finding", "list")
        self.assertEqual(out.count("None Yet."), 3)
        out, _ = self.run_tool("finding", "add", "A Fresh Hypothesis After The File Was Lost.")
        self.assertEqual(out, "Added F01 As An Open Hypothesis\n")
        self.assertTrue(path.is_file())

    def test_findings_are_numbered_and_listed(self):
        out, _ = self.run_tool("finding", "add", "Showing The Result In The First Frame Raises Shares.")
        self.assertEqual(out, "Added F02 As An Open Hypothesis\n")
        out, _ = self.run_tool("finding", "list")
        self.assertEqual(out, (self.library / "findings.md").read_text(encoding="utf-8"))
        self.assertIn("### F02. Showing The Result In The First Frame Raises Shares.\n\n- Status: Open. Supporting Videos: 0. Weakening Videos: 0.\n- Evidence: None Yet.", out)
        self.assertIn("A Status Changes Only When At Least Two Posted Videos Agree", out)


class BacklogAndDefaults(LibraryCase):
    def test_backlog_saves_lists_and_marks_lines(self):
        self.start()
        out, _ = self.run_tool("backlog", "list")
        self.assertEqual(out, "The Backlog Has No Open Lines.\n")
        out, _ = self.run_tool("backlog", "add", "Show The Filter Before Naming The Product", "--tests", "F01")
        self.assertEqual(out, "Saved To The Backlog: Show The Filter Before Naming The Product\n")
        self.run_tool("backlog", "add", "What A Full Queue Costs Per Day")
        path = self.library / "backlog.md"
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\nA Line Someone Typed By Hand\n- [ ] 2026-01-01 | A Hand-Written Idea\n")
        today = date.today().isoformat()
        out, _ = self.run_tool("backlog", "list")
        self.assertEqual(
            out,
            f"1. {today} | Show The Filter Before Naming The Product | Tests F01\n"
            f"2. {today} | What A Full Queue Costs Per Day\n"
            "3. 2026-01-01 | A Hand-Written Idea\n",
        )
        out, _ = self.run_tool("backlog", "done", 1)
        self.assertIn("Marked As Used: ", out)
        out, _ = self.run_tool("backlog", "list", "--all")
        self.assertEqual(
            out,
            f"1. {today} | What A Full Queue Costs Per Day\n"
            "2. 2026-01-01 | A Hand-Written Idea\n"
            f"Used. {today} | Show The Filter Before Naming The Product | Tests F01 | Used {today}\n",
        )
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Idea Backlog\n"))
        self.assertIn("A Line Someone Typed By Hand\n", text)
        self.assertIn(f"- [x] {today} | Show The Filter Before Naming The Product | Tests F01 | Used {today}\n", text)
        _, err = self.run_tool("backlog", "done", 7, code=1)
        self.assertIn("The Backlog Has 2 Open Lines.", err)
        _, err = self.run_tool("backlog", "add", "  ", code=1)
        self.assertEqual(err, "Write The Idea As One Line.\n")

    def test_defaults_file_is_created_once_and_names_the_library(self):
        self.start()
        out, _ = self.run_tool("defaults", library=False)
        self.assertIn("No Defaults File At", out)
        self.assertIn("Create One With defaults write After The Creator Agrees.", out)
        _, err = self.run_tool("defaults", "write", code=1, library=False)
        self.assertEqual(err, "Name The Library Folder With --library.\n")
        out, _ = self.run_tool(
            "defaults", "write", "--platform", "Instagram Reels", "--audience", "Repair Shop Owners",
            "--pace", 2.8, "--voice", "Plain And Direct, Short Sentences",
            "--platform-note", "Views Count Replays",
        )
        path = self.home / "video-script.md"
        self.assertEqual(out, f"Created {path}\n")
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Video Script Defaults\n"))
        self.assertIn(f"- Library: {self.library.resolve().as_posix()}\n", text)
        self.assertIn(f"- Findings: {(self.library.resolve() / 'findings.md').as_posix()}\n", text)
        self.assertIn("- Pace: 2.8 Words Per Second\n", text)
        self.assertIn("- Voice: Plain And Direct, Short Sentences\n", text)
        self.assertIn("## Platform Notes\n\n- Views Count Replays\n", text)
        out, _ = self.run_tool("defaults", "show", library=False)
        self.assertIn(f"Defaults File: {path}", out)
        self.assertIn("Platform: Instagram Reels\n", out)
        self.assertIn("Pace: 2.8 Words Per Second\n", out)
        _, err = self.run_tool("defaults", "write", code=1)
        self.assertIn("A Defaults File Already Exists At", err)
        self.assertIn("Edit It By Hand.", err)
        self.assertEqual(path.read_text(encoding="utf-8"), text)
        out, _ = self.run_tool("index", library=False)
        self.assertIn("# Video Library Index", out)
        self.assertEqual(desk_support.pace_from(desk_support.read_defaults(path)), 2.8)

    def test_defaults_need_a_real_library_and_a_speakable_pace(self):
        _, err = self.run_tool("defaults", "write", "--pace", 40, code=1)
        self.assertEqual(err, "Write The Pace As Spoken Words Per Second, Between 0.5 And 8.\n")
        _, err = self.run_tool("defaults", "write", code=1)
        self.assertIn("No Video Library At", err)
        self.assertFalse((self.home / "video-script.md").exists())

    def test_help_uses_the_house_style(self):
        out, _ = self.run_tool("--help", library=False)
        self.assertIn("Usage: video_log.py", out)
        self.assertIn("Show This Help And Exit", out)
        for command in ("init", "add", "update", "snapshot", "attach", "index", "show", "compare", "lineup", "finding", "backlog", "defaults"):
            self.assertIn(f"    {command} ", out)


if __name__ == "__main__":
    unittest.main()
