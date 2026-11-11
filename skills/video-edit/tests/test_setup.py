"""Setup Check And Saved Defaults. Machine State Is Mocked, And The Defaults File Lives In A Temporary Home."""

import datetime
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import defaults
import setup_check

ENCODERS = ["libx264", "aac", "png", "pcm_s16le", "prores_ks"]
FILTERS = sorted({name for _, kind, names, _, _ in setup_check.FEATURES if kind == "filters" for name in names})


def machine(system="Windows", managers=("winget",), tools=("ffmpeg", "ffprobe", "node"), encoders=ENCODERS,
            filters=FILTERS, modules=("numpy", "cv2", "faster_whisper", "pip"), zones=True, browser="/apps/chrome",
            resolve=True, free=500e9, version="8.1.2-full_build", python=(3, 12, 4)):
    """Patch Every Probe Of The Machine With A Described Fake."""
    present = set(tools) | set(managers)

    def output(args):
        if args[-1] == "-version":
            return f"{Path(args[0]).name} version {version} Copyright (c) The FFmpeg Developers\nbuilt with a compiler\n"
        if args[-1] == "-encoders":
            return "Encoders:\n ------\n" + "".join(f" V....D {name:20s} Description Text\n" for name in encoders)
        if args[-1] == "-filters":
            return "Filters:\n" + "".join(f" T.. {name:17s} V->V       Description Text\n" for name in filters)
        if args[-1] == "--version":
            return "v22.11.0\n"
        return None

    found = {"application": "/apps/resolve", "bundled_python": "/apps/resolve/python", "scripting_sdk": "/apps/sdk"}
    missing = {"application": None, "bundled_python": None, "scripting_sdk": None}
    return patch.multiple(
        setup_check,
        which=lambda name: f"/tools/{name}" if name in present else None,
        system_name=lambda: system, tool_output=output, python_version=lambda: python,
        module_present=lambda name: name in modules, zone_available=lambda: zones,
        find_browser=lambda: browser, find_resolve=lambda: found if resolve else missing,
        free_bytes=lambda folder: free)


def by_id(report):
    return {row["id"]: row for row in report["items"]}


class SetupTests(unittest.TestCase):
    def test_complete_machine_is_ready_and_lists_every_piece(self):
        with machine():
            report, code = setup_check.check(".")
        self.assertEqual((code, report["ready"], report["missing_required"], report["missing_optional"]), (0, True, [], []))
        self.assertEqual(report["summary"], "Every Required Item Is Present.")
        items = by_id(report)
        self.assertEqual(list(items), [
            "python", "ffmpeg", "ffprobe", "ffmpeg-delivery-encoders", "ffmpeg-review-outputs",
            "ffmpeg-composition-filters", "ffmpeg-sound-filters", "ffmpeg-captions", "ffmpeg-detection",
            "ffmpeg-loudness", "ffmpeg-hdr", "ffmpeg-prores", "speech-recognizer", "camera-vision", "time-zones",
            "browser", "resolve", "node"])
        self.assertTrue(all(row["status"] == "present" and row["purpose"].endswith(".") for row in report["items"]))
        self.assertEqual([row["id"] for row in report["items"] if not row["required"]], [
            "ffmpeg-hdr", "ffmpeg-prores", "speech-recognizer", "camera-vision", "time-zones", "browser", "resolve", "node"])
        self.assertEqual(items["ffmpeg"]["version"], "8.1.2-full_build")
        self.assertEqual(items["ffmpeg-delivery-encoders"]["names"], ["libx264", "aac"])
        self.assertEqual(items["ffmpeg-hdr"]["names"], ["zscale", "tonemap"])
        self.assertIn("subtitles", items["ffmpeg-captions"]["names"])
        self.assertTrue({"silencedetect", "select"} <= set(items["ffmpeg-detection"]["names"]))
        self.assertEqual(items["ffmpeg-loudness"]["names"], ["ebur128"])
        self.assertEqual(report["system"]["package_managers"], ["winget"])
        self.assertIn("Installs Nothing", report["install_policy"])
        self.assertNotIn("install", json.dumps(report["items"]))

    def test_missing_ffmpeg_fails_with_a_command_for_the_package_managers_present(self):
        with machine(managers=("winget", "choco"), tools=("node",)):
            report, code = setup_check.check(".")
        self.assertEqual((code, report["ready"], report["missing_required"]), (1, False, ["ffmpeg", "ffprobe"]))
        self.assertEqual(report["summary"], "2 Required Items Are Missing.")
        items = by_id(report)
        self.assertEqual(items["ffmpeg"]["install"], "winget install --id Gyan.FFmpeg -e")
        self.assertEqual(items["ffmpeg"]["install_alternatives"], ["choco install ffmpeg-full -y"])
        self.assertIn("Same Package", items["ffprobe"]["install_note"])
        self.assertEqual({items[key]["status"] for key in items if key.startswith("ffmpeg-")}, {"unknown"})
        for system, managers, expected in (("Darwin", ("brew",), "brew install ffmpeg"),
                                           ("Linux", ("apt-get",), "sudo apt-get install -y ffmpeg"),
                                           ("Linux", ("pacman", "brew"), "sudo pacman -S --needed ffmpeg")):
            with self.subTest(system=system), machine(system, managers, tools=()):
                report, code = setup_check.check(".")
                self.assertEqual((code, by_id(report)["ffmpeg"]["install"]), (1, expected))

    def test_optional_gaps_keep_exit_zero_and_name_purpose_and_command(self):
        with machine("Darwin", ("brew",), tools=("ffmpeg", "ffprobe"), filters=[f for f in FILTERS if f != "zscale"],
                     encoders=ENCODERS[:4], modules=("numpy", "pip"), zones=False, browser=None, resolve=False):
            report, code = setup_check.check(".")
        self.assertEqual((code, report["ready"]), (0, True))
        self.assertEqual(report["missing_optional"], ["ffmpeg-hdr", "ffmpeg-prores", "speech-recognizer", "camera-vision",
                                                      "time-zones", "browser", "resolve", "node"])
        self.assertEqual(report["summary"], "Every Required Item Is Present. 8 Optional Items Are Missing.")
        items = by_id(report)
        self.assertEqual((items["ffmpeg-hdr"]["missing_names"], items["ffmpeg-hdr"]["install"]), (["zscale"], "brew install ffmpeg"))
        self.assertIn("HDR Phone Footage", items["ffmpeg-hdr"]["purpose"])
        command = setup_check.python_command()
        self.assertEqual(items["speech-recognizer"]["install"], f"{command} -m pip install faster-whisper")
        self.assertEqual(items["speech-recognizer"]["install_alternatives"], [f"{command} -m pip install openai-whisper"])
        self.assertEqual(items["camera-vision"]["install"], f"{command} -m pip install opencv-python-headless")
        self.assertEqual(items["camera-vision"]["missing_names"], ["opencv"])
        self.assertIn("Virtual Environment", items["camera-vision"]["install_note"])
        self.assertEqual(items["time-zones"]["install"], f"{command} -m pip install tzdata")
        self.assertEqual(items["browser"]["install"], "brew install --cask google-chrome")
        self.assertEqual(items["node"]["install"], "brew install node")
        self.assertNotIn("install", items["resolve"])
        self.assertIn("Blackmagic Design", items["resolve"]["manual"])
        for row in report["items"]:
            if row["status"] == "missing":
                self.assertTrue(row["purpose"])
                self.assertTrue("install" in row or "manual" in row, row["id"])

    def test_a_build_without_a_required_filter_fails(self):
        with machine("Linux", ("apt-get",), filters=[f for f in FILTERS if f not in ("subtitles", "ebur128")]):
            report, code = setup_check.check(".")
        self.assertEqual((code, report["missing_required"]), (1, ["ffmpeg-captions", "ffmpeg-loudness"]))
        captions = by_id(report)["ffmpeg-captions"]
        self.assertEqual(captions["detail"], "The Installed FFmpeg Build Lacks subtitles.")
        self.assertEqual(captions["install"], "sudo apt-get install -y ffmpeg")
        with machine("Linux", ("apt-get",), encoders=["aac", "png", "pcm_s16le"]):
            report, code = setup_check.check(".")
        self.assertEqual((code, by_id(report)["ffmpeg-delivery-encoders"]["missing_names"]), (1, ["libx264"]))

    def test_no_package_manager_gives_a_manual_step_and_linux_browser_skips_cask(self):
        with machine("Linux", (), tools=(), browser=None):
            report, _ = setup_check.check(".")
        items = by_id(report)
        for key in ("ffmpeg", "browser", "node"):
            self.assertNotIn("install", items[key])
            self.assertIn("No Supported Package Manager Was Found", items[key]["manual"])
        with machine("Linux", ("brew",), browser=None):
            self.assertNotIn("install", by_id(setup_check.check(".")[0])["browser"])
        with machine("Linux", ("dnf",), browser=None):
            self.assertEqual(by_id(setup_check.check(".")[0])["browser"]["install"], "sudo dnf install -y chromium")

    def test_old_python_old_ffmpeg_and_quoted_interpreter_paths(self):
        with machine(python=(3, 8, 10)):
            report, code = setup_check.check(".")
        self.assertEqual((code, report["missing_required"]), (1, ["python"]))
        self.assertIn("Python 3.8.10 Is Older Than 3.9", by_id(report)["python"]["detail"])
        self.assertEqual(by_id(report)["python"]["install"], "winget install --id Python.Python.3.12 -e")
        with machine(version="4.4.2-0ubuntu0.22.04.1"):
            self.assertIn("Versions Before 5.1 Lack Options It Uses", by_id(setup_check.check(".")[0])["ffmpeg"]["note"])
        with machine(version="N-118193-g5f38c82536"):
            self.assertNotIn("note", by_id(setup_check.check(".")[0])["ffmpeg"])
        with machine(modules=("numpy",)), patch.object(setup_check.sys, "executable", r"C:\Program Files\Python\python.exe"):
            vision = by_id(setup_check.check(".")[0])["camera-vision"]
        self.assertEqual(vision["install"], r'"C:\Program Files\Python\python.exe" -m pip install opencv-python-headless')
        self.assertIn("This Python Has No pip", vision["install_note"])
        self.assertIn("In PowerShell, Put & Before The Quoted Program Path", vision["install_note"])

    def test_disk_space_is_read_at_the_nearest_existing_folder_and_low_space_is_a_warning(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "New Project" / "Media"
            with machine(free=1.2e9):
                report, code = setup_check.check(target, 2.0)
            disk = report["disk"]
            self.assertEqual((code, disk["enough"], disk["free_gb"], disk["minimum_gb"]), (0, False, 1.2, 2.0))
            self.assertEqual((Path(disk["folder"]), Path(disk["measured_at"])), (target.resolve(), Path(folder).resolve()))
            self.assertTrue(report["summary"].endswith("Free Disk Space Is Low."))
            self.assertFalse(target.exists())
            with machine(free=3e9):
                self.assertTrue(setup_check.check(target, 2.0)[0]["disk"]["enough"])

    def test_listing_and_version_parsers(self):
        filters = " T.. zscale            V->V       Apply Resizing\n .S tonemap           V->V       Conversion\n ... anull   A->A  Pass\nFilters:\n"
        self.assertEqual(setup_check.names_in(filters, "filters"), {"zscale", "tonemap", "anull"})
        encoders = "Encoders:\n V..... = Video\n ------\n V....D libx264              H.264\n A....D aac                  AAC\n"
        self.assertEqual(setup_check.names_in(encoders, "encoders"), {"libx264", "aac"})
        self.assertEqual(setup_check.version_of("ffmpeg version n7.1-2 Copyright"), ("n7.1-2", (7, 1, 0)))
        self.assertEqual(setup_check.version_of(""), (None, None))

    def test_command_prints_json_and_matches_its_exit_code_on_this_machine(self):
        with tempfile.TemporaryDirectory() as folder:
            for script in (["setup_check.py"], ["edit_video.py", "setup"]):
                done = subprocess.run([sys.executable, "-B", str(SCRIPTS / script[0]), *script[1:], "--project-folder", folder],
                                      capture_output=True, text=True)
                report = json.loads(done.stdout)
                self.assertEqual(done.returncode, 0 if report["ready"] else 1)
                self.assertEqual(report["ready"], not report["missing_required"])
                self.assertEqual(by_id(report)["python"]["status"], "present")
                self.assertEqual(Path(report["disk"]["folder"]), Path(folder).resolve())
            self.assertEqual(list(Path(folder).iterdir()), [])
        bad = subprocess.run([sys.executable, "-B", str(SCRIPTS / "setup_check.py"), "--min-free-gb", "-1"], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2)


class DefaultsTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="kit home ")
        self.addCleanup(folder.cleanup)
        self.home = Path(folder.name)
        self.env = dict(os.environ, SOCIAL_CUT_KIT_HOME=str(self.home / "Kit Home"))
        self.file = self.home / "Kit Home" / "video-edit.md"

    def cli(self, *arguments, script=("defaults.py",)):
        done = subprocess.run([sys.executable, "-B", str(SCRIPTS / script[0]), *script[1:], *arguments],
                              capture_output=True, text=True, env=self.env)
        self.assertEqual(done.returncode, 0, done.stderr)
        return json.loads(done.stdout)

    def test_path_follows_the_home_folder_unless_overridden(self):
        with patch.dict(os.environ, {"SOCIAL_CUT_KIT_HOME": ""}), patch.object(defaults.Path, "home", return_value=self.home):
            self.assertEqual(defaults.defaults_path(), self.home / ".social-cut-kit" / "video-edit.md")
        with patch.dict(os.environ, {"SOCIAL_CUT_KIT_HOME": str(self.home / "Elsewhere")}):
            self.assertEqual(defaults.defaults_path(), self.home / "Elsewhere" / "video-edit.md")

    def test_show_reports_a_missing_file_without_creating_it(self):
        result = self.cli()
        self.assertEqual((Path(result["path"]), result["exists"], result["content"]), (self.file, False, None))
        self.assertIn("No Saved Defaults Yet", result["note"])
        self.assertFalse(self.file.parent.exists())

    def test_init_creates_headings_once_and_show_prints_the_content(self):
        created = self.cli("--init")
        self.assertEqual(created["changed"], "Created The Defaults File With Empty Headings.")
        text = self.file.read_text(encoding="utf-8")
        for heading in ("Where Videos Are Posted", "Usual Length", "Music And Effects", "Hook Headlines", "Caption Style",
                        "Editor", "Export Approval", "Asset Libraries", "Habits"):
            self.assertIn(f"\n## {heading}\n", text)
        self.assertIn("Current Instructions Always Override Them", text)
        self.file.write_text("# Mine\n\nPost To Shorts. Captions In Yellow — Café Style.\n", encoding="utf-8")
        kept = self.cli("--init")
        self.assertNotIn("changed", kept)
        self.assertEqual(kept["content"], "# Mine\n\nPost To Shorts. Captions In Yellow — Café Style.\n")
        self.assertEqual(self.cli(script=("edit_video.py", "defaults"))["content"], kept["content"])

    def test_add_records_a_dated_habit_in_the_named_section(self):
        today = datetime.date.today().isoformat()
        first = self.cli("--add", "  Keep   Captions In The Lower Third. ")
        self.assertEqual(first["changed"], "Recorded One Line Under Habits.")
        self.assertTrue(first["content"].endswith(f"## Habits\n\n- {today}: Keep Captions In The Lower Third.\n"))
        self.cli("--add", "Post To Shorts First.", "--section", "where videos are posted")
        self.cli("--add", "Never Export Before Review.", "--section", "Export Approval")
        self.cli("--add", "Second Habit.")
        text = self.file.read_text(encoding="utf-8")
        self.assertIn(f"## Where Videos Are Posted\n\n- {today}: Post To Shorts First.\n\n## Usual Length\n", text)
        self.assertIn(f"## Export Approval\n\n- {today}: Never Export Before Review.\n\n## Asset Libraries\n", text)
        self.assertTrue(text.endswith(f"- {today}: Keep Captions In The Lower Third.\n- {today}: Second Habit.\n"))
        self.cli("--add", "Use Resolve.", "--section", "New Area")
        self.assertTrue(self.file.read_text(encoding="utf-8").endswith(f"\n## New Area\n\n- {today}: Use Resolve.\n"))
        self.assertEqual([path.name for path in self.file.parent.iterdir()], ["video-edit.md"])

    def test_add_note_keeps_existing_lines_and_rejects_empty_text(self):
        day = datetime.date(2030, 1, 2)
        text = "# Notes\n\n## Habits\n\n- Old Line\n\n\n## Editor\nResolve\n"
        self.assertEqual(defaults.add_note(text, "New Line", "habits", day),
                         "# Notes\n\n## Habits\n\n- Old Line\n- 2030-01-02: New Line\n\n## Editor\nResolve\n")
        self.assertEqual(defaults.add_note("Plain Text", "Line", "Habits", day),
                         "Plain Text\n\n## Habits\n\n- 2030-01-02: Line\n")
        for note, section in (("  ", "Habits"), ("Line", " ")):
            with self.assertRaises(ValueError):
                defaults.add_note(text, note, section, day)
        failed = subprocess.run([sys.executable, "-B", str(SCRIPTS / "defaults.py"), "--add", " "],
                                capture_output=True, text=True, env=self.env)
        self.assertEqual(failed.returncode, 1)
        self.assertFalse(self.file.exists())


if __name__ == "__main__":
    unittest.main()
