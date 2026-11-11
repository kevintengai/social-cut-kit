"""Working Copies: The Owner Gate, The Planned Command And Graph, Timeline Use, And Playback Hints.

No Test Here Converts A File. The Checks Read The Command That Would Run, Exercise Every Refusal, Run The
Picture Chain On Generated Patterns Into A Null Sink Or A Pipe, And Stand In For FFmpeg With Placeholder Bytes.
"""

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import edit_video
import media
import setup_check
import timeline
import working_copy
from media import graph, tone_filters
from review import make_server
from timeline import EditError, browser_playback, canvas_rate, canvas_rate_hint, framing, picture_info, prepare

FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")
CONTAINER = "mov,mp4,m4a,3gp,3g2,mj2"
PHONE = {
    "index": 0, "codec_name": "hevc", "codec_type": "video", "width": 3840, "height": 2160,
    "pix_fmt": "yuv420p10le", "sample_aspect_ratio": "1:1", "color_range": "tv", "color_space": "bt2020nc",
    "color_transfer": "arib-std-b67", "color_primaries": "bt2020", "bits_per_raw_sample": "10",
    "avg_frame_rate": "60000/1001", "r_frame_rate": "60000/1001", "nb_frames": "13187",
    "side_data_list": [{"side_data_type": "DOVI configuration record", "dv_profile": 8, "dv_level": 4,
                        "dv_bl_signal_compatibility_id": 4},
                       {"side_data_type": "Display Matrix", "rotation": -90}],
}
COPY = {"index": 0, "codec_name": "h264", "codec_type": "video", "width": 1080, "height": 1920,
        "pix_fmt": "yuv420p", "sample_aspect_ratio": "1:1", "color_range": "tv", "color_space": "bt709",
        "color_transfer": "bt709", "color_primaries": "bt709", "bits_per_raw_sample": "8",
        "avg_frame_rate": "60000/1001", "nb_frames": "13187"}
PLAIN = {"index": 0, "codec_name": "h264", "codec_type": "video", "width": 1920, "height": 1080,
         "pix_fmt": "yuv420p", "color_range": "tv", "color_space": "bt709", "color_transfer": "bt709",
         "color_primaries": "bt709", "bits_per_raw_sample": "8", "avg_frame_rate": "30/1"}
AAC = {"index": 1, "codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "48000"}
PCM = dict(AAC, codec_name="pcm_s24le")
SECONDS = 220.02


def meta(video, audio=AAC, seconds=SECONDS, container=CONTAINER):
    return {"duration": seconds, "video": video, "audio": audio, "format": container, "picture": picture_info(video)}


class RateAndPlaybackHintTests(unittest.TestCase):
    def test_canvas_rate_is_the_nearest_standard_rate_halved_above_30(self):
        cases = {23.976: 24, 24: 24, 25: 25, 29.97: 30, 30: 30, 48: 24, 50: 25, 59.94: 30, 60: 30, 100: 25,
                 119.88: 30, 120: 30, 240: 30, 27.5: 30, 15: 24}
        for rate, expected in cases.items():
            with self.subTest(rate=rate):
                self.assertEqual(canvas_rate(rate), expected)
        for odd in (None, 0, -5, float("nan"), "60"):
            self.assertEqual(canvas_rate(odd), 30)

    def test_hint_names_the_source_rate_the_result_and_the_rule(self):
        hint = canvas_rate_hint(meta(PHONE))
        self.assertEqual(hint["suggested"], 30)
        self.assertAlmostEqual(hint["source_fps"], 59.94, places=2)
        self.assertIn("Source Rate Of 59.94 FPS", hint["reason"])
        self.assertIn("Is 60, Which Is Above 30, So It Is Halved To 30.", hint["reason"])
        self.assertEqual(hint["rule"], timeline.CANVAS_RATE_RULE)
        steady = canvas_rate_hint(meta(dict(PLAIN, avg_frame_rate="24000/1001")))
        self.assertEqual(steady["suggested"], 24)
        self.assertIn("24 Is The Standard Rate Nearest The Source Rate Of 23.976 FPS.", steady["reason"])
        still = {"duration": None, "video": {"codec_name": "png", "width": 8, "height": 8, "avg_frame_rate": "25/1"},
                 "audio": None, "format": "png_pipe", "picture": picture_info({"width": 8, "height": 8, "avg_frame_rate": "25/1"})}
        self.assertIsNone(canvas_rate_hint(still))

    def test_phone_footage_is_flagged_as_unlikely_to_play_in_a_browser(self):
        report = browser_playback(meta(PHONE))
        self.assertFalse(report["likely"])
        text = " ".join(report["reasons"])
        for expected in ("HEVC Video Plays In A Browser Only", "The Picture Is HLG HDR", "3840 By 2160 At 59.94 FPS Is Heavy"):
            self.assertIn(expected, text)
        self.assertIn("Ask The Owner Once", report["advice"])
        self.assertIn("working_copy", report["advice"])
        self.assertEqual(browser_playback(meta(PLAIN)), {"likely": True, "reasons": []})
        self.assertEqual(browser_playback(meta(COPY)), {"likely": True, "reasons": []})
        prores = browser_playback(meta(dict(PLAIN, codec_name="prores", pix_fmt="yuv422p10le"), PCM))
        self.assertIn("Browsers Do Not Play prores Video.", prores["reasons"])
        deep = browser_playback(meta(dict(PLAIN, pix_fmt="yuv420p10le", bits_per_raw_sample="10")))
        self.assertIn("Browsers Rarely Play 10-Bit H.264 Video.", deep["reasons"])
        self.assertIn("Browsers Do Not Play ac3 Sound.", browser_playback(meta(PLAIN, dict(AAC, codec_name="ac3")))["reasons"])
        tiff = {"duration": None, "video": {"codec_name": "tiff"}, "audio": None, "format": "tiff_pipe", "picture": None}
        self.assertFalse(browser_playback(tiff)["likely"])
        self.assertNotIn("advice", browser_playback(tiff))

    def test_probe_command_prints_both_hints_beside_the_streams(self):
        output = io.StringIO()
        with patch.object(edit_video, "probe", return_value=meta(PHONE)), contextlib.redirect_stdout(output):
            edit_video.main(["probe", "clip.mov"])
        report = json.loads(output.getvalue())
        self.assertFalse(report["browser_playback"]["likely"])
        self.assertEqual(report["canvas_fps"]["suggested"], 30)
        self.assertEqual(report["picture"]["displayed_size"], [2160, 3840])
        output = io.StringIO()
        sound = {"duration": 3.0, "video": None, "audio": dict(AAC, codec_name="pcm_s16le"), "format": "wav", "picture": None}
        with patch.object(edit_video, "probe", return_value=sound), contextlib.redirect_stdout(output):
            edit_video.main(["probe", "tone.wav"])
        report = json.loads(output.getvalue())
        self.assertTrue(report["browser_playback"]["likely"])
        self.assertNotIn("canvas_fps", report)

    def test_setup_lists_project_sources_with_the_same_hints(self):
        with tempfile.TemporaryDirectory(prefix="setup sources ") as folder:
            root = Path(folder)
            (root / "Footage").mkdir()
            (root / "Footage" / "Phone Clip.mov").write_bytes(b"Placeholder")
            (root / "Screen.mp4").write_bytes(b"Placeholder")
            (root / "notes.txt").write_text("Not Media", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "skip.mp4").write_bytes(b"Placeholder")
            sources = {"Phone Clip.mov": meta(PHONE), "Screen.mp4": meta(PLAIN)}
            with patch.object(setup_check, "which", return_value="ffprobe"), \
                    patch.object(timeline, "probe", side_effect=lambda path: sources[Path(path).name]):
                report = setup_check.source_report(root)
            self.assertEqual((report["found"], report["listed"]), (2, 2))
            phone, screen = report["files"]
            self.assertEqual(Path(phone["file"]).name, "Phone Clip.mov")
            self.assertEqual((phone["plays_in_a_browser"], phone["suggested_canvas_fps"], phone["hdr"], phone["rotation"]),
                             (False, 30, "hlg", 90))
            self.assertIn("Ask The Owner Once", phone["advice"])
            self.assertEqual((screen["plays_in_a_browser"], screen["suggested_canvas_fps"]), (True, 30))
            self.assertNotIn("reasons", screen)
            self.assertIn("1 Source Is Unlikely To Play In A Browser.", report["note"])
            self.assertEqual(report["canvas_rate_rule"], timeline.CANVAS_RATE_RULE)
            with patch.object(setup_check, "which", return_value=None):
                self.assertIsNone(setup_check.source_report(root))
            with patch.object(setup_check, "which", return_value="ffprobe"), \
                    patch.object(timeline, "probe", side_effect=EditError("Unreadable")):
                self.assertEqual([row["readable"] for row in setup_check.source_report(root)["files"]], [False, False])


class ConversionPlanTests(unittest.TestCase):
    def test_phone_clip_plan_scales_upright_then_converts_once(self):
        recipe = working_copy.conversion(meta(PHONE))
        self.assertEqual(recipe["size"], [1080, 1920])
        self.assertTrue(recipe["tone_mapped"])
        self.assertEqual(recipe["filter"], "scale=1080:1920,setsar=1," + tone_filters(PHONE) + "format=yuv420p")
        self.assertEqual(recipe["filter"].count("tonemap=tonemap="), 1)
        self.assertNotIn("transpose", recipe["filter"])
        self.assertNotIn("fps=", recipe["filter"])
        picture = recipe["picture"]
        self.assertEqual(picture[:6], ["-map", "0:0", "-filter:v", recipe["filter"], "-fps_mode", "passthrough"])
        for pair in (["-c:v", "libx264"], ["-pix_fmt", "yuv420p"], ["-color_trc", "bt709"], ["-color_primaries", "bt709"],
                     ["-colorspace", "bt709"], ["-color_range", "tv"], ["-g", "60"]):
            at = picture.index(pair[0])
            self.assertEqual(picture[at:at + 2], pair)
        notes = " ".join(recipe["notes"])
        self.assertIn("The Same One Check, Still, And Render Apply To The Original.", notes)
        self.assertIn("The Working Copy Is Stored Upright.", notes)

    def test_sound_is_copied_or_encoded_without_any_filter(self):
        copied = working_copy.conversion(meta(PHONE))
        self.assertEqual((copied["sound"], copied["sound_handling"]), (["-map", "0:1", "-c:a", "copy"], "copied"))
        encoded = working_copy.conversion(meta(PHONE, PCM))
        self.assertEqual((encoded["sound"], encoded["sound_handling"]), (["-map", "0:1", "-c:a", "aac", "-b:a", "256k"], "encoded"))
        self.assertIn("With No Filter And No Level Change.", " ".join(encoded["notes"]))
        silent = working_copy.conversion(meta(PHONE, None))
        self.assertEqual((silent["sound"], silent["sound_handling"]), (["-an"], "none"))
        with patch.object(working_copy, "binary", return_value="ffmpeg"):
            for recipe in (copied, encoded, silent):
                args = working_copy.command(Path("clip.mov"), "working.mp4", recipe)
                for banned in ("-af", "-filter:a", "-ar", "-ac", "-y", "-vf", "-r", "-vsync"):
                    self.assertNotIn(banned, args)
                self.assertFalse([part for part in args if "volume" in part or "loudnorm" in part or "dynaudnorm" in part])
                self.assertIn("-n", args)
                self.assertEqual(args[-1], "working.mp4")
                self.assertEqual(args[args.index("-i") + 1], "clip.mov")

    def test_standard_sources_are_only_scaled_and_never_enlarged(self):
        recipe = working_copy.conversion(meta(dict(PLAIN, codec_name="hevc", width=1280, height=720)))
        self.assertEqual((recipe["size"], recipe["tone_mapped"]), ([1280, 720], False))
        self.assertEqual(recipe["filter"], "scale=1280:720,setsar=1,format=yuv420p")
        self.assertNotIn("-color_trc", recipe["picture"])
        self.assertEqual(working_copy.conversion(meta(PLAIN), 960)["size"], [960, 540])
        self.assertEqual(working_copy.conversion(meta(PHONE), 1280)["size"], [720, 1280])
        self.assertEqual(working_copy.working_size([1001, 563], 1920), [1000, 562])
        anamorphic = dict(PLAIN, width=1440, height=1080, sample_aspect_ratio="4:3")
        self.assertEqual(working_copy.conversion(meta(anamorphic))["size"], [1920, 1080])
        wide = working_copy.conversion(meta(dict(PLAIN, color_primaries="bt2020")))
        self.assertIn("bt2020 Primaries Without A PQ Or HLG Transfer", " ".join(wide["notes"]))

    def test_sources_that_cannot_be_converted_are_refused(self):
        profile5 = dict(PHONE, color_transfer="unknown", color_primaries="unknown",
                        side_data_list=[{"side_data_type": "DOVI configuration record", "dv_profile": 5}])
        cases = (
            (meta(profile5), "Dolby Vision Profile 5"),
            (meta(dict(PLAIN, side_data_list=[{"rotation": -45}])), "45 Degree Display Rotation"),
            ({"duration": 3.0, "video": None, "audio": AAC, "format": "wav", "picture": None}, "Needs A Source With A Picture Stream"),
            ({"duration": None, "video": {"codec_name": "png", "width": 8, "height": 8, "index": 0}, "audio": None,
              "format": "png_pipe", "picture": picture_info({"width": 8, "height": 8})}, "A Still Image Needs No Working Copy"),
        )
        for source, expected in cases:
            with self.subTest(expected=expected), self.assertRaisesRegex(EditError, expected):
                working_copy.conversion(source)
        for bad in (100, 9000, 1920.0, "1920"):
            with self.assertRaisesRegex(EditError, "Long Side Between 320 And 8192"):
                working_copy.conversion(meta(PHONE), bad)

    def test_null_sink_command_reads_the_picture_only_and_names_no_output_file(self):
        recipe = working_copy.conversion(meta(PHONE))
        with patch.object(working_copy, "binary", return_value="ffmpeg"):
            args = working_copy.command(Path("clip.mov"), None, recipe, 5)
        self.assertEqual(args[-3:], ["-f", "null", "-"])
        self.assertIn("-an", args)
        self.assertEqual(args[args.index("-t") + 1], "5")
        self.assertNotIn("libx264", args)
        self.assertFalse([part for part in args if part.endswith(".mp4")])


class GateTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="working copy ")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.source = self.root / "Phone Clip.mov"
        self.source.write_bytes(b"Original Placeholder")
        self.output = self.root / "Phone Clip Working Copy.mp4"
        self.probed = {self.source.name: meta(PHONE), "working.mp4": meta(COPY), self.output.name: meta(COPY)}
        probe = patch.object(working_copy, "probe", side_effect=lambda path: self.probed[Path(path).name])
        probe.start()
        self.addCleanup(probe.stop)
        binary = patch.object(working_copy, "binary", return_value="ffmpeg")
        binary.start()
        self.addCleanup(binary.stop)

    def leftovers(self):
        return sorted(path.name for path in self.root.iterdir() if path != self.source)

    def test_conversion_is_refused_without_the_owner_agreement_flag(self):
        with patch.object(working_copy.subprocess, "run") as run, self.assertRaisesRegex(EditError, "Ask The Owner Before Making A Working Copy"):
            working_copy.make(self.source, self.output)
        run.assert_not_called()
        self.assertEqual(self.leftovers(), [])
        with self.assertRaises(EditError) as caught:
            edit_video.main(["working-copy", str(self.source), str(self.output)])
        self.assertIn("--owner-agreed-working-copy", str(caught.exception))
        self.assertEqual(self.source.read_bytes(), b"Original Placeholder")

    def test_export_approval_is_a_different_flag_and_is_not_accepted_here(self):
        script = str(SCRIPTS / "edit_video.py")
        for flags in (["--owner-approved"], []):
            done = subprocess.run([sys.executable, "-B", script, "working-copy", str(self.source), str(self.output), *flags],
                                  capture_output=True, text=True)
            self.assertNotEqual(done.returncode, 0)
            self.assertFalse(self.output.exists())
        self.assertIn("unrecognized arguments: --owner-approved",
                      subprocess.run([sys.executable, "-B", script, "working-copy", str(self.source), str(self.output),
                                      "--owner-approved"], capture_output=True, text=True).stderr)
        render = subprocess.run([sys.executable, "-B", script, "render", "timeline.json", "cut.mp4",
                                 "--owner-agreed-working-copy"], capture_output=True, text=True)
        self.assertIn("unrecognized arguments: --owner-agreed-working-copy", render.stderr)
        listing = " ".join(edit_video.parser().format_help().split())
        self.assertIn("Requires The Owner's Agreement.", listing)

    def test_plan_prints_the_command_and_writes_nothing(self):
        with patch.object(working_copy.subprocess, "run") as run:
            report = working_copy.make(self.source, self.output, plan=True)
        run.assert_not_called()
        self.assertEqual(self.leftovers(), [])
        self.assertEqual((report["command"], report["working_size"], report["displayed_size"], report["sound"]),
                         ("working-copy", [1080, 1920], [2160, 3840], "copied"))
        self.assertTrue(report["wrote"].startswith("Nothing."))
        self.assertEqual(report["ffmpeg"][-1], self.output.name)
        self.assertIn(str(self.source), report["ffmpeg"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            edit_video.main(["working-copy", str(self.source), str(self.output), "--plan"])
        self.assertEqual(json.loads(output.getvalue())["filter"], report["filter"])
        self.assertEqual(self.leftovers(), [])

    def test_targets_protect_the_original_and_existing_files(self):
        taken = self.root / "Taken.mp4"
        taken.write_bytes(b"Keep This")
        cases = ((self.root / "Missing.mov", self.output, "Missing Source"),
                 (self.source, self.root / "Copy.mov", "Choose An MP4 Output Filename"),
                 (self.source, taken, "Output Already Exists"),
                 (self.source, self.root / "Nowhere" / "Copy.mp4", "Output Folder Does Not Exist"))
        for source, output, expected in cases:
            with self.subTest(expected=expected), self.assertRaisesRegex(EditError, expected):
                working_copy.make(source, output, agreed=True)
        original = self.root / "Already.mp4"
        original.write_bytes(b"Original Placeholder")
        with self.assertRaisesRegex(EditError, "The Original Is Never Replaced"):
            working_copy.make(original, original, agreed=True)
        self.assertEqual(taken.read_bytes(), b"Keep This")
        with self.assertRaisesRegex(EditError, "--seconds Together With --check"):
            working_copy.make(self.source, self.output, agreed=True, seconds=5)

    def test_missing_hdr_filters_are_named_before_anything_runs(self):
        with patch.object(working_copy, "available_filters", return_value={"scale", "tonemap"}), \
                patch.object(working_copy.subprocess, "run") as run:
            with self.assertRaisesRegex(EditError, "Lacks The zscale Filter Needed To Convert HDR Footage"):
                working_copy.make(self.source, self.output, agreed=True)
            with self.assertRaisesRegex(EditError, "zscale"):
                working_copy.make(self.source, self.output, check=True)
        run.assert_not_called()
        self.assertEqual(self.leftovers(), [])

    def stand_in(self, code=0, error=""):
        """Stand In For FFmpeg. It Records The Command And Leaves Placeholder Bytes Where The Encoder Would Write."""
        calls = []

        def run(args, cwd=None, **options):
            calls.append((args, cwd))
            if code == 0 and args[-1] == "working.mp4":
                (Path(cwd) / "working.mp4").write_bytes(b"Placeholder Bytes, Not A Video")

            class Done:
                returncode, stdout, stderr = code, "frame=13187\n", error
            return Done()
        return calls, run

    def test_agreed_run_verifies_the_result_and_never_replaces_a_file(self):
        calls, run = self.stand_in()
        with patch.object(working_copy, "available_filters", return_value={"zscale", "tonemap"}), \
                patch.object(working_copy.subprocess, "run", side_effect=run):
            report = working_copy.make(self.source, self.output, agreed=True)
            self.assertEqual(self.output.read_bytes(), b"Placeholder Bytes, Not A Video")
            self.assertEqual(self.leftovers(), [self.output.name])
            self.assertEqual((report["frames"], report["duration_seconds"]), (13187, SECONDS))
            self.assertIn("It Is Not An Export Of The Edit.", report["wrote"])
            self.assertIn("working_copy", report["next_step"])
            args, cwd = calls[0]
            self.assertEqual(Path(cwd).parent, self.root)
            self.assertEqual(args[-1], "working.mp4")
            with self.assertRaisesRegex(EditError, "Output Already Exists"):
                working_copy.make(self.source, self.output, agreed=True)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.source.read_bytes(), b"Original Placeholder")

    def test_a_result_that_disagrees_with_its_original_is_not_published(self):
        cases = ((meta(COPY, seconds=SECONDS - 1), "Duration Does Not Match"),
                 (meta(dict(COPY, nb_frames="13000")), "Has 13000 Frames And Its Original Has 13187"),
                 (meta(dict(COPY, width=1920, height=1080)), "Picture Size Failed Verification"))
        for made, expected in cases:
            self.probed["working.mp4"] = made
            _, run = self.stand_in()
            with self.subTest(expected=expected), patch.object(working_copy, "available_filters", return_value={"zscale", "tonemap"}), \
                    patch.object(working_copy.subprocess, "run", side_effect=run):
                with self.assertRaisesRegex(EditError, expected):
                    working_copy.make(self.source, self.output, agreed=True)
            self.assertEqual(self.leftovers(), [])
        _, run = self.stand_in(1, "Encoder Stopped")
        with patch.object(working_copy, "available_filters", return_value={"zscale", "tonemap"}), \
                patch.object(working_copy.subprocess, "run", side_effect=run):
            with self.assertRaisesRegex(EditError, "Encoder Stopped"):
                working_copy.make(self.source, self.output, agreed=True)
        self.assertEqual(self.leftovers(), [])


@unittest.skipUnless(FFMPEG, "FFmpeg Required")
class NullSinkTests(unittest.TestCase):
    """Run The Planned Picture Chain On A Generated HLG Pattern. Frames Go To A Null Sink Or A Pipe, Never A File."""

    WIDTH, HEIGHT = 180, 320

    def setUp(self):
        if any(name not in media.available_filters() for name in media.TONE_FILTERS):
            self.skipTest("This FFmpeg Build Lacks zscale Or tonemap.")
        self.clip = dict(PHONE, width=self.HEIGHT, height=self.WIDTH)
        self.recipe = working_copy.conversion(meta(self.clip))

    def pattern(self, level):
        # The Generated Frames Are Already Upright, As FFmpeg Delivers A Rotated Phone Clip.
        return (f"color=black:s={self.WIDTH}x{self.HEIGHT}:r=24:d=0.25,format=yuv420p10le,"
                f"geq=lum={round(64 + level * 876)}:cb=512:cr=512,"
                "setparams=color_trc=arib-std-b67:color_primaries=bt2020:colorspace=bt2020nc:range=tv")

    def lavfi(self, args, source):
        at = args.index("-i")
        return args[:at] + ["-f", "lavfi", "-i", source] + args[at + 2:]

    def test_planned_chain_runs_into_the_null_sink_and_keeps_every_frame(self):
        self.assertEqual(self.recipe["size"], [self.WIDTH, self.HEIGHT])
        args = self.lavfi(working_copy.command("generated", None, self.recipe), self.pattern(0.5))
        done = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(working_copy.frames_done(done.stdout), 6)

    def test_encoder_and_sound_arguments_are_accepted_without_writing_a_file(self):
        # The Whole Planned Command Runs, With A Generated Source In Place Of The Clip And A Null Sink In Place Of The File.
        tone = "aevalsrc=0.1*sin(2*PI*220*t)|0.2*sin(2*PI*440*t):s=48000:d=0.25[out1]"
        for sound in (AAC, PCM):
            recipe = working_copy.conversion(meta(self.clip, sound))
            args = working_copy.command("generated", "working.mp4", recipe)
            self.assertEqual(args[-3:], ["-movflags", "+faststart", "working.mp4"])
            args = self.lavfi(args[:-3] + ["-f", "null", "-"], self.pattern(0.5) + "[out0];" + tone)
            with tempfile.TemporaryDirectory(prefix="null sink ") as folder, self.subTest(sound=sound["codec_name"]):
                done = subprocess.run(args, cwd=folder, capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(working_copy.frames_done(done.stdout), 6)
                self.assertEqual(list(Path(folder).iterdir()), [])

    def test_working_copy_pixels_match_the_composition_graph(self):
        w, h = self.WIDTH, self.HEIGHT
        for level in (0.25, 0.5, 0.75):
            source = self.pattern(level)
            base = [shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "lavfi", "-i", source]
            tail = ["-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "yuv420p", "pipe:1"]
            copy = subprocess.run(base + ["-filter:v", self.recipe["filter"]] + tail, capture_output=True, check=True).stdout
            shot = dict(asset="Phone", start=0, end=0.25, at=0, duration=0.25, speed=1, gain=0, fit="cover",
                        geometry=framing(self.clip, w, h, "cover", 1, 0, 0), brightness=1, contrast=1, saturation=1,
                        hdr="hlg", tone_map=True)
            model = {"width": w, "height": h, "fps": 24, "duration": 0.25, "overlays": [], "captions": [], "audio": [],
                     "assets": {"Phone": {"kind": "video", "path": "generated", "video": self.clip, "audio": None}},
                     "shots": [shot]}
            _, expression = graph(model)
            composed = subprocess.run(base + ["-filter_complex_threads", "1", "-filter_complex", expression + ";[sound]anullsink",
                                              "-map", "[picture]"] + tail, capture_output=True, check=True).stdout
            self.assertEqual(len(copy), w * h * 3 // 2)
            center = w * (h // 2) + w // 2
            with self.subTest(level=level):
                self.assertLessEqual(abs(copy[center] - composed[center]), 1)
                self.assertGreater(copy[center], 40)


class TimelineTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="copy timeline ")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.sources = {"phone.source": meta(PHONE), "phone.copy": meta(COPY), "old.source": meta(PLAIN, seconds=12.0),
                        "tone.source": {"duration": 9.0, "video": None, "audio": AAC, "format": "wav", "picture": None}}
        for name in self.sources:
            (self.root / name).write_bytes(name.encode())
        self.doc = {
            "version": 1, "title": "Working Copy", "canvas": {"width": 1080, "height": 1920, "fps": 30, "fit": "cover"},
            "assets": {"Phone": {"path": "phone.source", "kind": "video", "working_copy": "phone.copy"},
                       "Old": {"path": "old.source", "kind": "video"}, "Tone": {"path": "tone.source", "kind": "audio"}},
            "shots": [{"asset": "Phone", "in": 0, "out": 2}, {"asset": "Old", "in": 1, "out": 3}],
            "audio": [{"asset": "Phone", "at": 2, "end": 3, "in": 10}],
        }
        probe = patch.object(timeline, "probe", side_effect=lambda path: self.sources[Path(path).name])
        probe.start()
        self.addCleanup(probe.stop)

    def model(self):
        return prepare(json.loads(json.dumps(self.doc)), self.root)

    def test_model_keeps_the_original_path_and_names_the_copy(self):
        model = self.model()
        phone = model["assets"]["Phone"]
        self.assertEqual(Path(phone["path"]).name, "phone.source")
        self.assertEqual(Path(phone["working_copy"]).name, "phone.copy")
        self.assertEqual(phone["picture"]["displayed_size"], [2160, 3840])
        self.assertNotIn("working_copy", model["assets"]["Old"])
        self.assertEqual(model["shots"][0]["geometry"]["crop"], [2160, 3840, 0, 0])
        notes = model["warnings"]
        self.assertTrue(any(note.startswith("Asset Phone Plays From Its Working Copy In The Browser Editor And In Remotion.")
                            and note.endswith("Render Read The Original.") for note in notes))
        self.assertTrue(any("Tone Mapping Converts Shot 1 To Standard Dynamic Range Once" in note
                            and "Play The Working Copy, Which Already Carries That Conversion." in note for note in notes))
        self.assertFalse([note for note in notes if "Browser Player Shows Its Own Conversion" in note])
        self.assertFalse([note for note in notes if "Make A Fresh Working Copy" in note or "Shapes Differ" in note])
        self.assertFalse([note for note in notes if "Is Unlikely To Play" in note])

    def test_validation_points_to_a_working_copy_when_a_source_in_use_has_none(self):
        del self.doc["assets"]["Phone"]["working_copy"]
        self.doc["assets"]["Spare"] = {"path": "phone.source", "kind": "video"}
        notes = [note for note in self.model()["warnings"] if "Is Unlikely To Play In The Browser Editor Or In Remotion Studio." in note]
        self.assertEqual(len(notes), 1)
        self.assertTrue(notes[0].startswith("Asset Phone Is Unlikely To Play"))
        for part in ("HEVC Video Plays In A Browser Only", "The Picture Is HLG HDR.", "Ask The Owner Once", "working_copy Field"):
            self.assertIn(part, notes[0])

    def test_composition_graph_and_inputs_never_touch_the_working_copy(self):
        inputs, expression = graph(self.model())
        files = [inputs[i + 1] for i, part in enumerate(inputs) if part == "-i"]
        self.assertEqual([Path(name).name for name in files], ["phone.source", "old.source", "phone.source"])
        self.assertNotIn("phone.copy", " ".join(inputs) + expression)
        self.assertEqual(expression.count("tonemap=tonemap="), 1)
        del self.doc["assets"]["Phone"]["working_copy"]
        self.assertEqual(graph(self.model()), (inputs, expression))

    def test_validation_warns_when_the_copy_disagrees_with_its_original(self):
        cases = ((meta(COPY, seconds=SECONDS - 0.5), "Working Copy Lasts 219.520 Seconds And Its Original Lasts 220.020 Seconds."),
                 (meta(dict(COPY, nb_frames="13100")), "Working Copy Has 13100 Frames And Its Original Has 13187."),
                 (meta(dict(COPY, width=1920, height=1080)), "Working Copy Is 1920 By 1080 And Its Original Displays At 2160 By 3840."),
                 (meta(dict(COPY, side_data_list=[{"rotation": -90}], width=1920, height=1080)), "Carries A 90 Degree Display Rotation."),
                 (meta(dict(COPY, codec_name="hevc")), "Working Copy May Not Play In A Browser. HEVC Video"))
        for twin, expected in cases:
            self.sources["phone.copy"] = twin
            with self.subTest(expected=expected):
                self.assertIn(expected, " ".join(self.model()["warnings"]))
        self.sources["phone.copy"] = meta(dict(COPY, nb_frames="13188"), seconds=SECONDS + 0.01)
        self.assertFalse([note for note in self.model()["warnings"] if "Fresh Working Copy" in note])
        self.sources["phone.copy"] = meta(dict(PHONE, side_data_list=[], width=2160, height=3840))
        notes = " ".join(self.model()["warnings"])
        self.assertIn("Working Copy Is Itself HLG HDR.", notes)
        self.assertIn("The Browser Player Shows Its Own Conversion.", notes)

    def test_validate_command_reports_the_copy_and_invalid_copies_are_refused(self):
        project = self.root / "edit.json"
        project.write_text(json.dumps(self.doc), encoding="utf-8")
        self.sources["phone.copy"] = meta(COPY, seconds=100.0)
        output = io.StringIO()
        with patch.object(edit_video, "missing_tone_filters", return_value=[]), contextlib.redirect_stdout(output):
            edit_video.main(["validate", str(project)])
        notes = " ".join(json.loads(output.getvalue())["warnings"])
        self.assertIn("Plays From Its Working Copy", notes)
        self.assertIn("Working Copy Lasts 100.000 Seconds", notes)
        cases = (({"path": "phone.source", "kind": "video", "working_copy": "missing.copy"}, "Missing Working Copy"),
                 ({"path": "phone.source", "kind": "video", "working_copy": "phone.source"}, "Must Be A Different File From Its Original"),
                 ({"path": "phone.source", "kind": "video", "working_copy": "tone.source"}, "Missing Video Stream In"),
                 ({"path": "phone.source", "kind": "video", "working_copy": ""}, "Working Copy Path Requires Text"),
                 ({"path": "tone.source", "kind": "audio", "working_copy": "phone.copy"}, "Only A Video Asset Can Name A Working Copy"))
        for asset, expected in cases:
            self.doc["assets"]["Phone"] = asset
            self.doc["shots"][0]["asset"] = "Old" if asset["kind"] == "audio" else "Phone"
            self.doc["audio"] = []
            with self.subTest(expected=expected), self.assertRaisesRegex(EditError, expected):
                self.model()

    def test_caption_mapper_carries_both_paths_into_a_timeline_in_another_folder(self):
        project = self.root / "edit.json"
        project.write_text(json.dumps(self.doc), encoding="utf-8")
        words = self.root / "words.json"
        words.write_text(json.dumps([{"start": 0.2, "end": 0.6, "text": "Hello"}, {"start": 0.7, "end": 1.2, "text": "there."}]),
                         encoding="utf-8")
        (self.root / "Captioned").mkdir()
        target = self.root / "Captioned" / "edit.json"
        done = subprocess.run([sys.executable, "-B", str(SCRIPTS / "speech.py"), "captions", str(words), str(project), "--asset", "Phone",
                               "--phrases", "--with-timeline", "--output", str(target)], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        phone = json.loads(target.read_text(encoding="utf-8"))["assets"]["Phone"]
        self.assertEqual((target.parent / phone["path"]).resolve(), (self.root / "phone.source").resolve())
        self.assertEqual((target.parent / phone["working_copy"]).resolve(), (self.root / "phone.copy").resolve())
        self.assertNotIn("working_copy", json.loads(target.read_text(encoding="utf-8"))["assets"]["Old"])

    def test_review_serves_the_working_copy_and_the_original_where_there_is_none(self):
        project = self.root / "edit.json"
        project.write_text(json.dumps(self.doc), encoding="utf-8")
        with make_server(project) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                self.assertEqual(urlopen(server.url + "media/Phone").read(), b"phone.copy")
                self.assertEqual(urlopen(server.url + "media/Old").read(), b"old.source")
                state = json.load(urlopen(server.url + "state"))
                self.assertEqual(Path(state["model"]["assets"]["Phone"]["working_copy"]).name, "phone.copy")
                self.assertEqual(state["project"]["assets"]["Phone"]["path"], "phone.source")
            finally:
                server.shutdown()
                thread.join()
        self.assertEqual((self.root / "phone.source").read_bytes(), b"phone.source")


if __name__ == "__main__":
    unittest.main()
