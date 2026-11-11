"""The Remotion Subcommand: Wiring, Parity With The Timeline Model, And No Video Output."""

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import edit_video
from example import example
from timeline import EditError, load, prepare

NODE = shutil.which("node")
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".gif"}


def run(*arguments):
    quiet = io.StringIO()
    with contextlib.redirect_stdout(quiet):
        edit_video.main([str(item) for item in arguments])
    return json.loads(quiet.getvalue())


class WiringTests(unittest.TestCase):
    def test_subcommand_parses_its_folder_and_options(self):
        args = edit_video.parser().parse_args(["remotion", "cut/timeline.json", "Review Project", "--allow-hdr", "--link-media"])
        self.assertEqual((args.command, args.project, args.output), ("remotion", Path("cut/timeline.json"), Path("Review Project")))
        self.assertTrue(args.allow_hdr and args.link_media)
        plain = edit_video.parser().parse_args(["remotion", "timeline.json", "Out"])
        self.assertFalse(plain.allow_hdr or plain.link_media)
        listing = edit_video.parser().format_help()
        self.assertIn("Prepare A Remotion Project For Owner Review Without Writing A Video.", " ".join(listing.split()))

    def test_adapter_files_ship_with_the_skill(self):
        for name in ("cut-plan.cjs", "prepare-remotion.cjs", "remotion-entry.jsx", "render-reviewed.cjs", "README.md"):
            self.assertTrue((SKILL / "remotion" / name).is_file(), name)

    def test_missing_node_is_named(self):
        with mock.patch.object(edit_video.shutil, "which", return_value=None):
            with self.assertRaises(EditError) as caught:
                edit_video.remotion_project(Path("timeline.json"), Path("Out"), False, False)
        self.assertIn("Install Node.js", str(caught.exception))


@unittest.skipUnless(NODE, "The Remotion Adapter Needs Node.js.")
class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="remotion fixtures ", dir=Path(__file__).resolve().parent)
        cls.base = Path(cls.temp.name)
        cls.plain = example(cls.base / "Plain Cut")
        doc = load(cls.plain)
        doc["canvas"] = {"width": 1080, "height": 1920, "fps": 30, "fit": "contain"}
        doc["shots"] = [
            {"asset": "First", "in": 0.5, "out": 2.3, "lead": 0.2, "tail": 0.13, "speed": 1.5, "zoom": 2, "pan_x": -0.3, "pan_y": 0.7},
            {"asset": "Second", "in": 0, "out": 1.01, "speed": 0.5, "fit": "cover", "saturation": 0},
            {"asset": "First", "in": 0, "out": 0.77, "zoom": 1.37, "pan_x": 1, "pan_y": -1, "brightness": 0.9},
        ]
        doc["overlays"] = [{"asset": "Second", "at": 0.51, "end": 2.02, "x": -31, "y": 77, "width": 333},
                           {"asset": "First", "at": 1, "end": 3.9, "x": 400, "y": 1500, "width": 2000}]
        doc["audio"] = [{"asset": "Sound", "at": 0.26, "end": 3.31, "in": 0.4, "gain": 1.7, "fade_in": 0.3, "fade_out": 0.02}]
        doc["captions"] = [{"at": 0.04, "end": 1.26, "text": "Line One\nLine Two", "position": "center"},
                           {"at": 1.3, "end": 4.2, "text": "Top Words", "position": "top"}]
        doc["caption_style"] = {"font": "Verdana", "size": 77, "color": "#FFEE00", "outline": "#001122", "stroke": 3.5, "margin": 12.5}
        cls.rich = cls.base / "Plain Cut" / "rich.json"
        cls.rich.write_text(json.dumps(doc), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_project_matches_the_timeline_model_frame_for_frame(self):
        target = self.base / "Rich Project"
        summary = run("remotion", self.rich, target)
        model = prepare(load(self.rich), self.rich.parent)
        cut = json.loads((target / "src/cut.json").read_text(encoding="utf-8"))
        fps = model["fps"]
        frame = lambda seconds: round(seconds * fps)
        self.assertEqual(summary["command"], "remotion")
        self.assertEqual(summary["composition"], "VideoEdit")
        self.assertEqual(Path(summary["output"]), target.resolve())
        self.assertEqual(summary["frames"], frame(model["duration"]))
        self.assertEqual((cut["width"], cut["height"], cut["fps"], cut["frames"]),
                         (model["width"], model["height"], fps, frame(model["duration"])))
        self.assertEqual(cut["captionStyle"], model["caption_style"])
        self.assertEqual(len(cut["shots"]), len(model["shots"]))
        for made, shot in zip(cut["shots"], model["shots"]):
            geometry = shot["geometry"]
            self.assertEqual((made["from"], made["frames"]), (frame(shot["at"]), frame(shot["duration"])))
            self.assertEqual((made["start"], made["end"], made["speed"]), (shot["start"], shot["end"], shot["speed"]))
            self.assertEqual([made["box"][key] for key in ("left", "top", "width", "height")], geometry["pad"] + geometry["scale"])
            crop_w, crop_h, crop_x, crop_y = geometry["crop"]
            # The Placed Picture Shows Exactly The FFmpeg Crop Inside The Box.
            self.assertAlmostEqual(-made["media"]["left"] * crop_w / made["box"]["width"], crop_x, places=6)
            self.assertAlmostEqual(-made["media"]["top"] * crop_h / made["box"]["height"], crop_y, places=6)
            self.assertAlmostEqual(made["media"]["width"] * crop_w / made["box"]["width"], 160, places=6)
            self.assertAlmostEqual(made["media"]["height"] * crop_h / made["box"]["height"], 100, places=6)
        self.assertEqual(sum(shot["frames"] for shot in cut["shots"]), cut["frames"])
        for made, row in zip(cut["overlays"], model["overlays"]):
            self.assertEqual((made["from"], made["frames"], made["left"], made["top"], made["width"]),
                             (frame(row["at"]), frame(row["end"]) - frame(row["at"]), row["x"], row["y"], row["width"]))
            self.assertEqual(made["height"] % 2, 0)
            self.assertAlmostEqual(made["height"], row["width"] * 100 / 160, delta=1)
        self.assertEqual([row["id"] for row in cut["overlays"]], ["overlay-1", "overlay-2"])
        for made, row in zip(cut["audio"], model["audio"]):
            self.assertEqual((made["from"], made["frames"], made["start"], made["gain"], made["fadeIn"], made["fadeOut"]),
                             (frame(row["at"]), frame(row["end"]) - frame(row["at"]), row["start"], row["gain"],
                              row["fade_in"], row["fade_out"]))
        for made, row in zip(cut["captions"], model["captions"]):
            self.assertEqual((made["from"], made["frames"], made["text"], made["position"]),
                             (frame(row["at"]), frame(row["end"]) - frame(row["at"]), row["text"], row["position"]))
        notes = " ".join(summary["warnings"])
        for expected in ("Audio Cue 1 Has Gain 1.7.", "Audio Cue 1 Has A 20 Millisecond Fade Out.", "Captions Are Drawn By Chrome In Verdana"):
            self.assertIn(expected, notes)

    def test_project_holds_no_video_and_its_timeline_copy_validates(self):
        target = self.base / "Plain Project"
        summary = run("remotion", self.plain, target, "--link-media")
        self.assertEqual(summary["next_steps"][:2], ["npm install", "npm run studio"])
        files = [path for path in target.rglob("*") if path.is_file()]
        self.assertFalse([path.name for path in files if path.suffix.lower() in VIDEO_SUFFIXES])
        self.assertFalse((target / "node_modules").exists())
        self.assertEqual(summary["media_files"], 3)
        package = json.loads((target / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["scripts"], {"studio": "remotion studio src/index.jsx", "render-reviewed": "node render-reviewed.cjs"})
        copy = run("validate", target / "source-timeline.json")
        self.assertEqual((copy["duration_seconds"], copy["shots"]), (summary["duration_seconds"], summary["shots"]))

    def test_existing_folder_and_invalid_timeline_are_refused(self):
        taken = self.base / "Taken"
        taken.mkdir()
        with self.assertRaises(EditError) as caught:
            run("remotion", self.plain, taken)
        self.assertIn("Choose A New Output Directory.", str(caught.exception))
        self.assertEqual(list(taken.iterdir()), [])
        doc = load(self.plain)
        doc["shots"][0]["speed"] = 9
        broken = self.plain.with_name("broken.json")
        broken.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaises(EditError):
            run("remotion", broken, self.base / "Never")
        self.assertFalse((self.base / "Never").exists())

    def test_command_line_exit_codes(self):
        script = str(SCRIPTS / "edit_video.py")
        done = subprocess.run([sys.executable, "-B", script, "remotion", str(self.plain), str(self.base / "Shell Project")],
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["frames"], 96)
        again = subprocess.run([sys.executable, "-B", script, "remotion", str(self.plain), str(self.base / "Shell Project")],
                               capture_output=True, text=True)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("Choose A New Output Directory.", again.stderr)


if __name__ == "__main__":
    unittest.main()
