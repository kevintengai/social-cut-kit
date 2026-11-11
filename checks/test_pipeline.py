"""Exercise The Customer Workflow With Temporary Projects And No Video Exports."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
EXAMPLE = ROOT / "examples" / "repair-desk"


def run(tool, *args, expect=True, env=None):
    p = subprocess.run(
        [sys.executable, str(tool), *map(str, args)],
        capture_output=True,
        text=True,
        env=env,
    )
    if expect and p.returncode:
        raise AssertionError(p.stderr or p.stdout)
    if not expect and p.returncode == 0:
        raise AssertionError("Expected Rejection")
    return p.stdout


class CommercialPackage(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="social cut test ")
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)

    def test_brief_to_review(self):
        campaign = SKILLS / "teng-campaign-brief/scripts/campaign.py"
        writer = SKILLS / "video-script/scripts/script_desk.py"
        director = SKILLS / "director/scripts/board.py"
        brief = self.work / "brief.json"
        script = self.work / "script.json"
        board = self.work / "board.html"
        timeline = self.work / "cut.json"
        run(
            campaign,
            "new",
            brief,
            "--title",
            "Demo <B>",
            "--viewer",
            "Studio Owners",
            "--offer",
            "A Demo",
            "--action",
            "Book A Demo",
            "--proof",
            "The Queue Filters",
            "Owned Capture",
            "One Job",
        )
        self.assertIn("Owned Capture", run(campaign, "show", brief))
        run(writer, "outline", brief, script, "--seconds", 17.5)
        obj = json.loads(script.read_bytes())
        self.assertAlmostEqual(sum(b["seconds"] for b in obj["beats"]), 17.5)
        run(director, "board", script, board)
        self.assertIn("Demo &lt;B&gt;", board.read_text(encoding="utf-8"))
        self.assertIn("Capture Needed", board.read_text(encoding="utf-8"))
        run(director, "timeline", script, timeline, expect=False)
        self.assertFalse(timeline.exists())
        run(
            director,
            "timeline",
            EXAMPLE / "beats.json",
            timeline,
            "--width",
            720,
            "--height",
            1280,
        )
        obj = json.loads(timeline.read_bytes())
        self.assertEqual(sum(b["out"] for b in obj["shots"]), 8)
        for rec in obj["assets"].values():
            self.assertTrue((timeline.parent / rec["path"]).is_file())

    def test_retention_and_subtitles(self):
        reader = SKILLS / "video-script/scripts/retention.py"
        report = json.loads(run(reader, "csv", EXAMPLE / "retention.csv"))
        self.assertLess(report["largest_drop"]["delta_points"], 0)
        speech = SKILLS / "video-edit/scripts/speech.py"
        words = self.work / "words.json"
        words.write_text(
            json.dumps(
                [
                    {"start": 0.3, "end": 0.6, "text": "First"},
                    {"start": 2.1, "end": 2.3, "text": "Later"},
                    {"start": 2.95, "end": 3.2, "text": "Crosses"},
                ]
            )
        )
        project = self.work / "edit.json"
        project.write_text(
            json.dumps(
                {
                    "canvas": {"fps": 25},
                    "assets": {"main": {"path": "camera.mp4"}},
                    "shots": [
                        {"asset": "main", "in": 2, "out": 3, "speed": 2},
                        {"asset": "main", "in": 0, "out": 1},
                    ],
                }
            )
        )
        out = self.work / "captioned.json"
        result = json.loads(
            run(
                speech,
                "captions",
                words,
                project,
                "--asset",
                "main",
                "--output",
                out,
                "--with-timeline",
            )
        )
        self.assertEqual(result["speech_units_cut_at_boundaries"], 1)
        cues = json.loads(out.read_bytes())["captions"]
        self.assertEqual([c["text"] for c in cues], ["Later", "First"])
        self.assertAlmostEqual(cues[0]["at"], 0.05)
        self.assertAlmostEqual(cues[1]["at"], 0.82)

    def test_installer_preserves_local_edits(self):
        install = ROOT / "install.py"
        for name, envvar in (("codex", "CODEX_HOME"), ("claude", "CLAUDE_CONFIG_DIR")):
            home = self.work / name
            settings = dict(os.environ, **{envvar: str(home)})
            run(install, "--agent", name, "director", env=settings)
            entry = home / "skills/director/SKILL.md"
            entry.write_text("Local Edits")
            run(install, "--agent", name, "director", env=settings)
            self.assertEqual(entry.read_text(), "Local Edits")
            run(install, "--agent", name, "--upgrade", "director", env=settings)
            copies = list(
                (home / "skills-social-cut-kit-backups").glob("*/director/SKILL.md")
            )
            self.assertEqual(len(copies), 1)
            self.assertEqual(copies[0].read_text(), "Local Edits")
            self.assertIn("# Director", entry.read_text(encoding="utf-8"))

    @unittest.skipUnless(
        shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg Required"
    )
    def test_chart_pixels_and_audio_alignment(self):
        chart = self.work / "chart.ppm"
        w, h = 50, 21
        pixels = bytearray([255] * (3 * w * h))
        for x in range(w):
            index = 3 * ((x // 5 + 3) * w + x)
            pixels[index : index + 3] = bytes([31, 66, 112])
        chart.write_bytes(f"P6\n{w} {h}\n255\n".encode() + pixels)
        cli = SKILLS / "video-script/scripts/retention.py"
        out = json.loads(
            run(
                cli,
                "image",
                chart,
                "--plot",
                0,
                0,
                49,
                20,
                "--color",
                31,
                66,
                112,
                "--seconds",
                10,
                "--top",
                100,
                "--bottom",
                0,
            )
        )
        self.assertEqual(out["chart_coverage"], 1)
        self.assertEqual(out["first_pct"], 85)
        self.assertEqual(out["last_pct"], 40)
        cue = SKILLS / "video-edit/assets/cue-bank/sounds/receipt-feed.wav"
        with wave.open(str(cue), "rb") as signal:
            params = signal.getparams()
            audio = signal.readframes(params.nframes)
        sounds = []
        for n in (0, 1):
            path = self.work / f"cue{n}.wav"
            with wave.open(str(path), "wb") as target:
                target.setparams(params)
                target.writeframes(
                    bytes(params.framerate * 2 * n // 4)
                    + audio
                    + bytes(params.framerate)
                )
            sounds.append(path)
        result = json.loads(
            run(
                SKILLS / "video-edit/scripts/speech.py",
                "sync",
                *sounds,
                "--seconds",
                2,
                "--lag",
                0.5,
            )
        )
        self.assertAlmostEqual(
            result["secondary_event_later_by_seconds"], 0.25, places=2
        )


if __name__ == "__main__":
    unittest.main()
