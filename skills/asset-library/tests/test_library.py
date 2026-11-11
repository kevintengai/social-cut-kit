"""Exercise Every Asset Library Command With Temporary Files. No Video Is Ever Written."""

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
import zlib


TOOL = Path(__file__).resolve().parents[1] / "scripts" / "library.py"
HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
META = ("--origin", "Test Fixture", "--rights", "Owned", "--context", "Unit Test")
OLD_SCHEMA = (
    "CREATE TABLE blobs (id INTEGER PRIMARY KEY, digest TEXT UNIQUE, size INTEGER NOT NULL)",
    """CREATE TABLE chunks (
        blob INTEGER REFERENCES blobs ON DELETE CASCADE, seq INTEGER, data BLOB NOT NULL,
        PRIMARY KEY(blob, seq)) WITHOUT ROWID""",
    """CREATE TABLE revisions (
        id INTEGER PRIMARY KEY, asset TEXT NOT NULL, version TEXT NOT NULL, kind TEXT NOT NULL,
        manifest TEXT, origin TEXT NOT NULL, rights TEXT NOT NULL, context TEXT NOT NULL,
        tags TEXT NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(asset, version))""",
    """CREATE TABLE pins (
        project TEXT NOT NULL, slot TEXT NOT NULL, revision INTEGER NOT NULL REFERENCES revisions,
        PRIMARY KEY(project, slot)) WITHOUT ROWID""",
)


def write_wav(path, seconds=0.5, rate=8000, channels=2, level=0.5, tone=440.0):
    frames = bytearray()
    for n in range(int(seconds * rate)):
        sample = int(32767 * level * math.sin(2 * math.pi * tone * n / rate))
        frames += struct.pack("<h", sample) * channels
    with wave.open(str(path), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(bytes(frames))


def write_png(path, width=8, height=6, color=(200, 40, 40)):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    row = b"\x00" + bytes(color) * width
    body = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(row * height)) + chunk(b"IEND", b""))
    Path(path).write_bytes(body)


class LibraryCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="asset library test ")
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)
        self.db = self.work / "library.sqlite"
        self.env = dict(os.environ)
        self.env.pop("SOCIAL_CUT_KIT_LIBRARY", None)
        self.ok("init")

    def call(self, *args, db=True, env=None):
        command = [sys.executable, "-B", str(TOOL)]
        if db:
            command += ["--db", str(self.db if db is True else db)]
        done = subprocess.run(command + [str(a) for a in args], capture_output=True, text=True,
                              encoding="utf-8", env=env or self.env, cwd=str(self.work))
        return done.returncode, done.stdout, done.stderr

    def ok(self, *args, **options):
        code, out, err = self.call(*args, **options)
        self.assertEqual(code, 0, err or out)
        return json.loads(out)

    def bad(self, *args, **options):
        code, out, err = self.call(*args, **options)
        self.assertNotEqual(code, 0, out)
        self.assertIn("Error: ", err)
        self.assertIn("Hint: ", err)
        return (json.loads(out) if out.strip() else None), err

    def text(self, name, content):
        path = self.work / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def add(self, asset, source, *extra):
        return self.ok("add", asset, source, *META, *extra)

    def no_tools_env(self):
        empty = self.work / "empty-path"
        empty.mkdir(exist_ok=True)
        return dict(self.env, PATH=str(empty))

    def rows(self, sql, *params):
        db = sqlite3.connect(str(self.db))
        try:
            return db.execute(sql, params).fetchall()
        finally:
            db.close()

    def assert_no_video(self):
        video = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
        self.assertEqual([p for p in self.work.rglob("*") if p.suffix.lower() in video], [])


class CoreCommands(LibraryCase):
    def test_original_commands_still_work(self):
        note = self.text("notes.md", "First Draft")
        first = self.add("review-notes", note, "--tag", "Handoff")
        self.assertEqual(first["kind"], "file")
        self.assertEqual(first["tags"], ["handoff"])
        self.assertEqual(self.add("review-notes", note, "--tag", "handoff")["version"], first["version"])
        self.bad("add", "review-notes", note, "--origin", "Other", "--rights", "Owned", "--context", "Unit Test")
        note.write_text("Second Draft", encoding="utf-8")
        second = self.add("review-notes", note)
        self.assertEqual([r["version"] for r in self.ok("history", "review-notes")],
                         [second["version"], first["version"]])
        self.assertEqual(len(self.ok("search", "--tag", "handoff", "--context", "unit")), 1)
        pinned = self.ok("pin", "Promo", "review-notes", "--use", "Editor Notes", "--version", first["version"])
        self.assertEqual((pinned["project"], pinned["use"], pinned["cut"]), ("Promo", "Editor Notes", None))
        self.bad("pin", "Promo", "review-notes", "--use", "Editor Notes", "--version", second["version"])
        self.ok("pin", "Promo", "review-notes", "--use", "Editor Notes", "--version", second["version"],
                "--replace", first["version"])
        self.assertEqual(self.ok("uses", "--project", "Promo")[0]["version"], second["version"])
        self.assertEqual(self.ok("uses", "--asset", "review-notes")[0]["use"], "Editor Notes")
        restored = self.ok("get", "review-notes", "restored.md", "--version", first["version"])
        self.assertEqual(restored["status"], "Restored")
        self.assertEqual((self.work / "restored.md").read_text(encoding="utf-8"), "First Draft")
        self.bad("check", "Promo", "--use", "Editor Notes", "--path", "restored.md")
        self.assertTrue(self.ok("check", "Promo", "--use", "Editor Notes", "--path", note)[0]["verified"])
        self.assertTrue(self.ok("check", "Promo")[0]["verified"])

    def test_bundle_round_trip(self):
        self.text("set/scene.py", "print('scene')")
        self.text("set/data/table.json", "{}")
        (self.work / "set" / "empty").mkdir()
        added = self.add("stage-set", self.work / "set")
        self.assertEqual((added["kind"], added["asset_kind"]), ("bundle", "code"))
        self.ok("get", "stage-set", "copy", "--version", added["version"])
        self.assertTrue((self.work / "copy" / "empty").is_dir())
        self.assertEqual((self.work / "copy" / "data" / "table.json").read_text(encoding="utf-8"), "{}")

    def test_failures_exit_non_zero_with_a_hint(self):
        self.bad("show", "missing-asset")
        self.bad("history", "x", db=self.work / "absent.sqlite")
        self.bad("check", "Nobody")
        code, _, err = self.call("search", "--kind", "nonsense")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)

    def test_kinds_given_inferred_and_filtered(self):
        write_png(self.work / "card.png")
        write_wav(self.work / "hit.wav", seconds=0.2)
        self.text("tool.py", "pass")
        (self.work / "room").mkdir()
        (self.work / "room" / "set.blend").write_bytes(b"BLENDER-FIXTURE")
        self.assertEqual(self.add("card", "card.png")["asset_kind"], "image")
        self.assertIn(self.add("hit", "hit.wav")["asset_kind"], ("sfx", "music"))
        self.assertEqual(self.add("tool", "tool.py")["asset_kind"], "code")
        self.assertEqual(self.add("room", "room")["asset_kind"], "model")
        host = self.add("host", self.text("host.txt", "Sheet"), "--kind", "character")
        self.assertEqual((host["asset_kind"], host["kind_source"]), ("character", "given"))
        self.assertEqual([r["asset"] for r in self.ok("search", "--kind", "character")], ["host"])
        self.assertEqual([r["asset"] for r in self.ok("search", "--kind", "model")], ["room"])
        self.bad("add", "host", self.text("host.txt", "Sheet Two"), *META, "--kind", "voice")
        self.assertEqual(self.ok("kind", "hit", "voice")["asset_kind"], "voice")
        self.assertEqual([r["asset"] for r in self.ok("search", "--kind", "voice")], ["hit"])

    @unittest.skipUnless(HAS_FFMPEG, "FFmpeg Required")
    def test_media_facts_and_duration_filters(self):
        write_wav(self.work / "short.wav", seconds=0.5, rate=8000, channels=2, level=0.5)
        write_wav(self.work / "long.wav", seconds=3.0, rate=8000, channels=1, level=0.25)
        write_png(self.work / "wide.png", width=64, height=20)
        short = self.add("short", "short.wav")["media"]
        self.assertAlmostEqual(short["duration"], 0.5, places=2)
        self.assertEqual((short["audio_channels"], short["sample_rate"], short["width"]), (2, 8000, None))
        self.assertAlmostEqual(short["peak_db"], -6.0, delta=0.5)
        self.assertAlmostEqual(self.add("long", "long.wav")["media"]["peak_db"], -12.0, delta=0.5)
        picture = self.add("wide", "wide.png")["media"]
        self.assertEqual((picture["width"], picture["height"], picture["duration"]), (64, 20, None))
        self.assertEqual([r["asset"] for r in self.ok("search", "--min-duration", "1")], ["long"])
        self.assertEqual([r["asset"] for r in self.ok("search", "--max-duration", "1")], ["short"])
        self.assertEqual(self.ok("search", "--min-duration", "1", "--max-duration", "2"), [])
        self.assertEqual(self.ok("show", "short")["revisions"][0]["media"]["sample_rate"], 8000)

    def test_add_succeeds_without_ffmpeg_and_says_why(self):
        write_wav(self.work / "tone.wav")
        write_png(self.work / "card.png")
        env = self.no_tools_env()
        sound = self.ok("add", "tone", "tone.wav", *META, env=env)
        self.assertIsNone(sound["media"])
        self.assertIn("FFprobe Was Not Found", sound["media_status"])
        picture = self.ok("add", "card", "card.png", *META, env=env)
        self.assertFalse(picture["has_preview"])
        self.assertIn("FFmpeg Was Not Found", picture["preview_status"])
        _, err = self.bad("preview", "card", "card.jpg")
        self.assertIn("FFmpeg Was Not Found", err)
        self.assertEqual(self.ok("search", "--max-duration", "10"), [])

    @unittest.skipUnless(HAS_FFMPEG, "FFmpeg Required")
    def test_preview_still_is_a_small_jpeg(self):
        write_png(self.work / "banner.png", width=1120, height=40)
        added = self.add("banner", "banner.png")
        self.assertTrue(added["has_preview"])
        self.bad("preview", "banner", "banner.mp4")
        written = self.ok("preview", "banner", "banner.jpg")
        data = (self.work / "banner.jpg").read_bytes()
        self.assertEqual(data[:2], b"\xff\xd8")
        self.assertEqual(written["bytes"], len(data))
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of",
                                "csv=p=0", str(self.work / "banner.jpg")], capture_output=True, text=True)
        self.assertEqual(probe.stdout.strip().split(",")[0], "560")
        self.assertEqual(self.ok("preview", "banner", "banner.jpg")["status"], "Already Present")
        write_wav(self.work / "tone.wav")
        self.add("tone", "tone.wav")
        self.bad("preview", "tone", "tone.jpg")
        self.assert_no_video()

    def test_duplicates_are_listed_and_collapsed(self):
        source = self.text("logo.txt", "Same Bytes")
        self.assertEqual(self.add("logo", source)["same_bytes_as"], [])
        twin = self.ok("add", "logo-client", source, "--origin", "Client", "--rights", "Client Only",
                       "--context", "Unit Test")
        self.assertEqual(twin["same_bytes_as"], ["logo"])
        found = self.ok("search")
        self.assertEqual([r["asset"] for r in found], ["logo"])
        self.assertEqual(found[0]["duplicates"], ["logo-client"])
        self.assertEqual(sorted(r["asset"] for r in self.ok("search", "--duplicates")), ["logo", "logo-client"])
        self.assertEqual(self.ok("show", "logo")["revisions"][0]["same_bytes_as"], ["logo-client"])

    def test_notes_and_show(self):
        added = self.add("bed", self.text("bed.txt", "Music Bed"), "--kind", "music")
        self.ok("pin", "Promo", "bed", "--use", "Underscore", "--version", added["version"])
        self.ok("note", "bed", "--kind", "opinion", "--text", "Too Busy Under Speech", "--source",
                "Owner Review Call", "--date", "2026-03-04")
        today = self.ok("note", "bed", "--kind", "caveat", "--text", "Agent Heard A Click At 0:12",
                        "--source", "Agent Listening Pass")
        self.assertRegex(today["date"], r"^\d{4}-\d{2}-\d{2}$")
        self.bad("note", "bed", "--kind", "rights", "--text", "T", "--source", "S", "--date", "March")
        self.bad("note", "absent", "--kind", "test", "--text", "T", "--source", "S")
        code, _, _ = self.call("note", "bed", "--kind", "praise", "--text", "T", "--source", "S")
        self.assertEqual(code, 2)
        record = self.ok("show", "bed")
        self.assertEqual(record["asset_kind"], "music")
        self.assertEqual({n["kind"] for n in record["notes"]}, {"opinion", "caveat"})
        self.assertEqual(record["notes"][0]["date"], "2026-03-04")
        self.assertEqual(record["revisions"][0]["rights"], "Owned")
        self.assertEqual((record["uses"][0]["project"], record["uses"][0]["use"]), ("Promo", "Underscore"))
        self.assertEqual(record["deliveries"], [])

    def test_archive_hides_and_undo_restores(self):
        added = self.add("old-sting", self.text("sting.txt", "Sting"))
        self.ok("pin", "Promo", "old-sting", "--use", "Open", "--version", added["version"])
        hidden = self.ok("archive", "old-sting")
        self.assertEqual((hidden["status"], hidden["pins_kept"]), ("Archived", 1))
        self.assertEqual(self.ok("search"), [])
        self.assertEqual(len(self.ok("search", "--archived")), 1)
        self.assertTrue(self.ok("check", "Promo")[0]["verified"])
        self.ok("get", "old-sting", "back.txt", "--version", added["version"])
        self.assertEqual(self.ok("stats")["archived"], 1)
        self.assertIsNone(self.ok("archive", "old-sting", "--undo")["archived"])
        self.assertEqual(len(self.ok("search")), 1)
        self.assertEqual(len(self.rows("SELECT * FROM revisions")), 1)

    def test_stats_counts(self):
        one = self.add("a", self.text("a.txt", "12345"), "--kind", "voice")
        self.add("b", self.text("b.txt", "1234567"))
        self.ok("pin", "P", "a", "--use", "U", "--version", one["version"])
        self.ok("pin", "P", "a", "--use", "U", "--version", one["version"], "--cut", "v1")
        stats = self.ok("stats")
        self.assertEqual((stats["assets"], stats["revisions"], stats["pins"], stats["cut_uses"]), (2, 2, 1, 1))
        self.assertEqual((stats["by_kind"]["voice"], stats["by_kind"]["other"]), (1, 1))
        self.assertEqual((stats["stored_bytes"], stats["deliveries"], stats["archived"]), (12, 0, 0))

class CutRecords(LibraryCase):
    def setUp(self):
        super().setUp()
        self.project = self.work / "proj"
        (self.project / "media").mkdir(parents=True)
        (self.project / "media" / "bed.txt").write_text("Music Bed", encoding="utf-8")
        self.bed = self.add("bed", self.project / "media" / "bed.txt", "--kind", "music")["version"]
        self.logo = self.add("logo", self.text("logo.txt", "Logo Art"), "--kind", "image")["version"]
        self.sting = self.add("sting", self.text("sting.txt", "Sting"), "--kind", "sfx")["version"]

    def declaration(self, entries=None, cut="v3", name="cut.json"):
        if entries is None:
            entries = [
                {"asset": "bed", "use": "Underscore", "path": "media/bed.txt", "cue": "Under The Hook", "time": 0},
                {"asset": "logo", "use": "End Card", "version": self.logo, "modified": True, "time": 27.5},
            ]
        path = self.project / name
        path.write_text(json.dumps({"project": "Promo", "cut": cut, "entries": entries}), encoding="utf-8")
        return path

    def test_pin_carries_a_cut_label(self):
        self.ok("pin", "Promo", "logo", "--use", "End Card", "--version", self.logo, "--cut", "v2")
        self.ok("pin", "Promo", "logo", "--use", "End Card", "--version", self.logo)
        cuts = [u["cut"] for u in self.ok("uses", "--project", "Promo")]
        self.assertEqual(cuts, [None, "v2"])
        self.assertEqual(len(self.ok("uses", "--cut", "v2")), 1)
        self.assertTrue(self.ok("check", "Promo", "--cut", "v2")[0]["verified"])

    def test_declaration_is_all_or_nothing(self):
        bad = self.declaration([
            {"asset": "logo", "use": "End Card", "version": self.logo},
            {"asset": "bed", "use": "Underscore", "version": "0" * 64},
            {"asset": "ghost", "use": "Whoosh", "path": "media/bed.txt"},
        ])
        report, err = self.bad("declare", bad)
        self.assertEqual(len(report["problems"]), 2)
        self.assertIn("add", report["problems"][0]["problem"])
        self.assertIn("Nothing Was Recorded", err)
        self.assertEqual(self.rows("SELECT COUNT(*) FROM cut_uses")[0][0], 0)
        (self.project / "media" / "bed.txt").write_text("Changed Bed", encoding="utf-8")
        report, _ = self.bad("declare", self.declaration())
        self.assertIn("Add It With The add Command", report["problems"][0]["problem"])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM cut_uses")[0][0], 0)
        (self.project / "media" / "bed.txt").write_text("Music Bed", encoding="utf-8")
        done = self.ok("declare", self.declaration())
        self.assertEqual((done["recorded"], done["status"]), (2, "Recorded"))
        self.assertEqual(done["entries"][0]["version"], self.bed)
        uses = {u["use"]: u for u in self.ok("uses", "--project", "Promo", "--cut", "v3")}
        self.assertEqual((uses["End Card"]["modified"], uses["End Card"]["time"]), (True, 27.5))
        self.assertEqual(uses["Underscore"]["cue"], "Under The Hook")
        swapped = self.ok("declare", self.declaration([{"asset": "sting", "use": "End Card", "version": self.sting}]))
        self.assertEqual(swapped["retired"], ["Underscore"])
        self.assertEqual([u["asset"] for u in self.ok("uses", "--cut", "v3")], ["sting"])
        self.assertEqual(self.rows("SELECT COUNT(*) FROM cut_uses")[0][0], 2)
        for broken in ({"project": "Promo", "cut": "v3", "entries": []},
                       {"project": "Promo", "cut": "v3", "entries": [{"asset": "logo", "use": "A"}]},
                       {"project": "Promo", "cut": "v3", "entries": [
                           {"asset": "logo", "use": "A", "version": self.logo},
                           {"asset": "bed", "use": "A", "version": self.bed}]}):
            path = self.project / "broken.json"
            path.write_text(json.dumps(broken), encoding="utf-8")
            self.bad("declare", path)

    def test_check_against_declaration(self):
        path = self.declaration()
        before = self.db.read_bytes()
        report, err = self.bad("check", "Promo", "--declaration", path)
        self.assertFalse(report["passed"])
        self.assertEqual(len(report["problems"]), 2)
        self.assertIn("Nothing Was Written", err)
        self.assertEqual(self.db.read_bytes(), before)
        self.bad("check", "Other Project", "--declaration", path)
        self.ok("declare", path)
        self.ok("pin", "Promo", "sting", "--use", "Extra Hit", "--version", self.sting, "--cut", "v3")
        (self.project / "notes.md").write_text("Try sting On The Button", encoding="utf-8")
        (self.project / "spare.bin").write_bytes(b"Sting")
        for folder in ("node_modules", ".cache"):
            (self.project / folder).mkdir()
            (self.project / folder / "copy.txt").write_bytes(b"Sting")
        report = self.ok("check", "Promo", "--declaration", path, "--scan", self.project)
        self.assertTrue(report["passed"])
        self.assertEqual([e["verified"] for e in report["entries"]], [True, True])
        self.assertEqual(report["recorded_but_undeclared"][0]["use"], "Extra Hit")
        found = {(e["asset"], e["match"]): e for e in report["scan"]["undeclared"]}
        self.assertEqual(set(found), {("sting", "bytes"), ("sting", "name")})
        self.assertEqual(found[("sting", "bytes")]["path"], "spare.bin")
        self.assertEqual(found[("sting", "bytes")]["places"], 1)
        self.assertFalse(report["scan"]["capped"])
        changed = self.declaration([{"asset": "bed", "use": "Underscore", "version": self.bed},
                                    {"asset": "sting", "use": "End Card", "version": self.sting}], name="other.json")
        report, _ = self.bad("check", "Promo", "--declaration", changed)
        self.assertEqual([p["use"] for p in report["problems"]], ["End Card"])
        db = sqlite3.connect(str(self.db))
        db.execute("DELETE FROM chunks WHERE blob=(SELECT id FROM blobs WHERE digest=?)", (self.logo,))
        db.commit()
        db.close()
        report, _ = self.bad("check", "Promo", "--declaration", path)
        self.assertIn("Failed Verification", report["problems"][0]["problem"])

    def test_deliver_records_only_a_passing_cut(self):
        path = self.declaration()
        report, err = self.bad("deliver", path)
        self.assertFalse(report["passed"])
        self.assertIn("No Delivery Record Was Stored", err)
        self.assertEqual(self.ok("deliveries"), [])
        self.ok("declare", path)
        self.bad("deliver", path, "--date", "Tomorrow")
        done = self.ok("deliver", path, "--date", "2026-05-06", "--scan", self.project)
        self.assertEqual((done["status"], done["delivered"]), ("Delivery Recorded", "2026-05-06"))
        self.assertEqual(self.ok("deliver", path)["status"], "Already Recorded")
        kept = self.ok("deliveries", "--project", "Promo")
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["declaration"]["entries"][0]["version"], self.bed)
        self.assertEqual(self.ok("stats")["deliveries"], 1)
        shown = self.ok("show", "logo")
        self.assertEqual(shown["deliveries"][0]["cut"], "v3")
        self.assertEqual(shown["uses"][0]["delivered"], "2026-05-06")
        swap = self.declaration([{"asset": "sting", "use": "End Card", "version": self.sting}])
        self.bad("declare", swap)
        self.bad("pin", "Promo", "sting", "--use", "End Card", "--version", self.sting, "--cut", "v3",
                 "--replace", self.logo)
        self.assertEqual(self.ok("declare", self.declaration(cut="v4"))["status"], "Recorded")
        self.ok("archive", "logo")
        self.assertTrue(self.ok("check", "Promo", "--declaration", self.declaration(cut="v4"))["passed"])


class BundleValidation(LibraryCase):
    SCRIPT = ("import json, os, pathlib, sys\n"
              "pathlib.Path('made-by-validation.txt').write_text('x')\n"
              "print(json.dumps(sorted(os.environ)))\n"
              "sys.exit(int(pathlib.Path('code.txt').read_text()))\n")

    def bundle(self, name, code="0"):
        self.text(f"{name}/check.py", self.SCRIPT)
        self.text(f"{name}/code.txt", code)
        return self.work / name

    def test_validation_runs_in_a_copy_with_a_minimal_environment(self):
        folder = self.bundle("rig")
        env = dict(self.env, KIT_SECRET_TOKEN="hidden", KIT_ALLOWED="yes")
        added = self.ok("add", "rig", folder, *META, "--validate", "python check.py",
                        "--validate-env", "KIT_ALLOWED", env=env)
        result = added["validation_result"]
        self.assertEqual((result["status"], result["exit_code"]), ("passed", 0))
        seen = json.loads(result["output_tail"].strip().splitlines()[-1])
        self.assertEqual([n for n in seen if n.startswith("KIT_")], ["KIT_ALLOWED"])
        self.assertIn("PATH", [n.upper() for n in seen])
        self.assertFalse((folder / "made-by-validation.txt").exists())
        again = self.ok("validate", "rig", "--env", "KIT_SECRET_TOKEN", env=env)
        self.assertIn("KIT_SECRET_TOKEN", json.loads(again["output_tail"].strip().splitlines()[-1]))
        shown = self.ok("show", "rig")["revisions"][0]["validation"]
        self.assertEqual((shown["command"], shown["runs"], shown["env"]), ("python check.py", 2, ["KIT_ALLOWED"]))
        self.assertEqual(shown["last_result"]["status"], "passed")
        self.ok("get", "rig", "rig-copy", "--version", added["version"])
        self.assertFalse((self.work / "rig-copy" / "made-by-validation.txt").exists())

    def test_failed_timed_out_and_deferred_validation(self):
        failing = self.ok("add", "broken", self.bundle("broken", "3"), *META, "--validate", "python check.py")
        self.assertEqual((failing["validation_result"]["status"], failing["validation_result"]["exit_code"]),
                         ("failed", 3))
        report, err = self.bad("validate", "broken")
        self.assertEqual(report["status"], "failed")
        self.assertIn("Validation Did Not Pass", err)
        self.text("slow/readme.txt", "Slow")
        slow = self.ok("add", "slow", self.work / "slow", *META, "--validate",
                       'python -c "import time; time.sleep(30)"', "--validate-timeout", "1")
        self.assertEqual((slow["validation_result"]["status"], slow["validation_result"]["exit_code"]),
                         ("failed", None))
        self.assertIn("Stopped After", slow["validation_result"]["detail"])
        later = self.ok("add", "later", self.bundle("later"), *META, "--validate", "python check.py",
                        "--validate-later")
        self.assertEqual(later["validation_result"]["status"], "not_run")
        self.assertEqual(self.ok("validate", "later")["status"], "passed")
        self.text("lost/readme.txt", "Lost")
        lost = self.ok("add", "lost", self.work / "lost", *META, "--validate", "no-such-program-xyz --flag")
        self.assertEqual(lost["validation_result"]["status"], "not_run")
        self.bad("add", "single", self.text("single.txt", "One"), *META, "--validate", "python check.py")
        self.text("plain/readme.txt", "Plain")
        self.add("plain", self.work / "plain")
        self.bad("validate", "plain")

class ExchangeAndSetup(LibraryCase):
    def test_export_and_import_round_trip(self):
        write_png(self.work / "card.png")
        card = self.add("card <one>", "card.png", "--tag", "title")
        self.text("kit/tool.py", "pass")
        self.add("kit", self.work / "kit", "--validate", "python tool.py", "--validate-later")
        self.ok("note", "card <one>", "--kind", "rights", "--text", "Licence On File", "--source", "Invoice 12",
                "--date", "2026-02-02")
        self.ok("pin", "Promo", "card <one>", "--use", "Title", "--version", card["version"])
        out = self.work / "export"
        done = self.ok("export", out, "--with-files")
        self.assertEqual((done["assets"], done["revisions"], done["uses"], done["files"]), (2, 2, 1, 2))
        self.assertTrue(done["contains_file_bytes"])
        page = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("card &lt;one&gt;", page)
        self.assertNotIn("card <one>", page)
        catalog = json.loads((out / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(catalog["uses"][0]["use"], "Title")
        self.assertEqual(catalog["assets"][0]["notes"][0]["text"], "Licence On File")
        self.assertFalse(self.ok("export", self.work / "plain-export")["contains_file_bytes"])
        self.assertFalse((self.work / "plain-export" / "files").exists())
        self.ok("export", out, "--with-files")
        self.text("busy/keep.txt", "Mine")
        self.bad("export", self.work / "busy")
        second = self.work / "second.sqlite"
        self.ok("init", db=second)
        first = self.ok("import", out / "catalog.json", "--files", out, db=second)
        self.assertEqual(sorted(a["asset"] for a in first["added"]), ["card <one>", "kit"])
        self.assertEqual(first["notes_added"], 1)
        again = self.ok("import", out / "catalog.json", "--files", out, db=second)
        self.assertEqual((len(again["unchanged"]), again["added"], again["notes_added"]), (2, [], 0))
        copy = self.ok("history", "card <one>", db=second)[0]
        self.assertEqual((copy["version"], copy["tags"], copy["asset_kind"]), (card["version"], ["title"], "image"))
        self.assertEqual(self.ok("show", "kit", db=second)["revisions"][0]["validation"]["command"], "python tool.py")
        self.ok("get", "kit", "kit-back", "--version", catalog["assets"][1]["revisions"][0]["version"], db=second)
        self.assertEqual((self.work / "kit-back" / "tool.py").read_text(encoding="utf-8"), "pass")
        catalog["assets"][0]["revisions"][0]["rights"] = "Changed Terms"
        catalog["assets"][1]["revisions"][0]["file"] = "files/gone/kit"
        catalog["assets"].append({"name": "card-twin", "file": catalog["assets"][0]["revisions"][0]["file"],
                                  "origin": "O", "rights": "R", "context": "C"})
        self.text("export/extra/fresh.txt", "Fresh")
        catalog["assets"].append({"name": "fresh", "kind": "voice", "file": "extra/fresh.txt",
                                  "origin": "O", "rights": "R", "context": "C", "tags": ["New"]})
        edited = self.text("edited.json", json.dumps(catalog))
        third = self.ok("import", edited, "--files", out, db=second)
        self.assertEqual(third["differing"][0]["fields"]["rights"], {"library": "Owned", "catalog": "Changed Terms"})
        self.assertEqual(third["missing"], [{"asset": "kit", "file": "files/gone/kit"}])
        self.assertEqual(third["duplicates"][0]["held_by"], ["card <one>"])
        self.assertEqual([a["asset"] for a in third["added"]], ["fresh"])
        self.assertEqual(self.ok("history", "card <one>", db=second)[0]["rights"], "Owned")
        self.assertEqual(self.ok("search", "--kind", "voice", db=second)[0]["tags"], ["new"])
        fourth = self.ok("import", edited, "--files", out, "--update", "card <one>", db=second)
        self.assertEqual(fourth["updated"][0]["asset"], "card <one>")
        self.assertEqual(self.ok("history", "card <one>", db=second)[0]["rights"], "Changed Terms")
        self.assert_no_video()

    def test_library_is_found_by_flag_environment_or_defaults_file(self):
        home = self.work / "home"
        (home / ".social-cut-kit").mkdir(parents=True)
        env = dict(self.env, HOME=str(home), USERPROFILE=str(home))
        _, err = self.bad("stats", db=False, env=env)
        self.assertIn("No Asset Library Was Named", err)
        self.assertIn("SOCIAL_CUT_KIT_LIBRARY", err)
        defaults = home / ".social-cut-kit" / "asset-library.md"
        defaults.write_text("# My Defaults\n\nReuse Rule: Ask Before Reusing Music.\n", encoding="utf-8")
        _, err = self.bad("stats", db=False, env=env)
        self.assertIn("No Library Line", err)
        defaults.write_text(f"# My Defaults\n\n- Library: `{self.db}`\n- Reuse Rule: Ask First.\n", encoding="utf-8")
        self.assertEqual(self.ok("stats", db=False, env=env)["database"], str(self.db.resolve()))
        other = self.work / "other.sqlite"
        self.ok("init", db=other)
        named = self.ok("init", db=False, env=dict(env, SOCIAL_CUT_KIT_LIBRARY=str(other)))
        self.assertEqual((named["database"], named["found_by"]), (str(other.resolve()), "SOCIAL_CUT_KIT_LIBRARY"))
        self.assertEqual(self.ok("init", env=dict(env, SOCIAL_CUT_KIT_LIBRARY=str(other)))["found_by"], "--db")

    def old_database(self, name="old.sqlite"):
        path = self.work / name
        data = b"Old Bytes"
        digest = hashlib.sha256(data).hexdigest()
        db = sqlite3.connect(str(path))
        for statement in OLD_SCHEMA:
            db.execute(statement)
        db.execute("PRAGMA application_id=%d" % 0x53434B31)
        db.execute("PRAGMA user_version=1")
        db.execute("INSERT INTO blobs(id,digest,size) VALUES(1,?,?)", (digest, len(data)))
        db.execute("INSERT INTO chunks VALUES(1,0,?)", (data,))
        db.execute("""INSERT INTO revisions(asset,version,kind,manifest,origin,rights,context,tags)
                      VALUES('legacy-card',?,'file',NULL,'Old Shoot','Owned','Promo','["legacy"]')""", (digest,))
        db.execute("INSERT INTO pins VALUES('Old Promo','Title',1)")
        db.commit()
        db.close()
        return path, digest

    def test_old_database_is_backed_up_then_upgraded_in_place(self):
        old, digest = self.old_database()
        code, out, err = self.call("history", "legacy-card", db=old)
        self.assertEqual(code, 0, err)
        self.assertIn("Upgraded The Library From Schema 1", err)
        record = json.loads(out)[0]
        self.assertEqual((record["version"], record["origin"], record["tags"], record["asset_kind"]),
                         (digest, "Old Shoot", ["legacy"], "other"))
        backups = list(self.work.glob("old.backup-v1-*.sqlite"))
        self.assertEqual(len(backups), 1)
        saved = sqlite3.connect(str(backups[0]))
        self.assertEqual(saved.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(saved.execute("SELECT COUNT(*) FROM revisions").fetchone()[0], 1)
        self.assertEqual(saved.execute("SELECT name FROM sqlite_master WHERE name='assets'").fetchall(), [])
        saved.close()
        code, _, err = self.call("uses", "--project", "Old Promo", db=old)
        self.assertEqual((code, err), (0, ""))
        self.assertEqual(len(list(self.work.glob("old.backup-v1-*.sqlite"))), 1)
        self.assertTrue(self.ok("check", "Old Promo", db=old)[0]["verified"])
        self.ok("get", "legacy-card", "legacy.bin", "--version", digest, db=old)
        self.assertEqual((self.work / "legacy.bin").read_bytes(), b"Old Bytes")
        self.ok("note", "legacy-card", "--kind", "caveat", "--text", "Kind Unknown", "--source", "Upgrade", db=old)
        self.ok("kind", "legacy-card", "image", db=old)
        self.assertEqual(self.ok("stats", db=old)["by_kind"]["image"], 1)
        self.assertEqual(self.ok("init", db=old)["schema_version"], 2)

    def test_newer_database_is_refused_untouched(self):
        newer, _ = self.old_database("newer.sqlite")
        db = sqlite3.connect(str(newer))
        db.execute("PRAGMA user_version=99")
        db.commit()
        db.close()
        before = newer.read_bytes()
        for command in (("stats",), ("init",), ("history", "legacy-card")):
            _, err = self.bad(*command, db=newer)
            self.assertIn("Newer Version", err)
        self.assertEqual(newer.read_bytes(), before)
        self.assertEqual(list(self.work.glob("newer.backup-*")), [])
        stray = self.work / "stray.sqlite"
        db = sqlite3.connect(str(stray))
        db.execute("CREATE TABLE unrelated (x)")
        db.commit()
        db.close()
        self.bad("init", db=stray)

    def test_concurrent_writers_keep_every_record(self):
        count = 8
        for n in range(count):
            self.text(f"clip-{n}.txt", f"Clip {n} " * 2000)
        base = [sys.executable, "-B", str(TOOL), "--db", str(self.db)]

        def together(commands):
            running = [subprocess.Popen(base + c, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        env=self.env, cwd=str(self.work)) for c in commands]
            results = [(p.communicate(), p.returncode) for p in running]
            for (out, err), code in results:
                self.assertEqual(code, 0, err.decode("utf-8", "replace"))
            return [json.loads(out) for (out, _), _ in results]

        added = together([["add", f"clip-{n}", f"clip-{n}.txt", *META] for n in range(count)]
                         + [["add", "shared", "clip-0.txt", *META] for _ in range(4)])
        versions = {r["asset"]: r["version"] for r in added}
        together([["pin", "Promo", f"clip-{n}", "--use", f"Shot {n}", "--version", versions[f"clip-{n}"]]
                  for n in range(count)]
                 + [["note", "shared", "--kind", "test", "--text", f"Pass {n}", "--source", "Suite"]
                    for n in range(count)])
        stats = self.ok("stats")
        self.assertEqual((stats["assets"], stats["revisions"], stats["pins"], stats["notes"]),
                         (count + 1, count + 1, count, count))
        self.assertEqual(stats["stored_files"], count)
        self.assertEqual(len(self.ok("check", "Promo")), count)
        self.assertEqual(self.rows("PRAGMA integrity_check"), [("ok",)])
        self.assertEqual(self.rows("PRAGMA foreign_key_check"), [])


if __name__ == "__main__":
    unittest.main()
