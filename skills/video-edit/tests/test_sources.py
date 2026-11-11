"""HDR And Rotated Sources: Probing, Validation Warnings, One Tone Map Per Shot, And Review Stills.

The Checks Use Mocked Probe Data, Graph Inspection, Generated Test Patterns, And PNG Stills.
No Video File Is Written.
"""

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import edit_video
import media
import timeline
from example import example
from media import graph, process, still, tone_filters
from timeline import EditError, framing, load, picture_info, prepare

FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")
PHONE = {
    "index": 0, "codec_name": "hevc", "codec_type": "video", "width": 3840, "height": 2160,
    "pix_fmt": "yuv420p10le", "sample_aspect_ratio": "1:1", "color_range": "tv", "color_space": "bt2020nc",
    "color_transfer": "arib-std-b67", "color_primaries": "bt2020", "bits_per_raw_sample": "10",
    "avg_frame_rate": "30000/1001", "r_frame_rate": "30000/1001",
    "side_data_list": [
        {"side_data_type": "DOVI configuration record", "dv_profile": 8, "dv_level": 4,
         "rpu_present_flag": 1, "el_present_flag": 0, "bl_present_flag": 1, "dv_bl_signal_compatibility_id": 4},
        {"side_data_type": "Display Matrix", "rotation": -90},
    ],
}
MASTERED = {
    "index": 0, "codec_name": "hevc", "codec_type": "video", "width": 1920, "height": 1080,
    "pix_fmt": "yuv420p10le", "color_range": "tv", "color_space": "bt2020nc", "color_transfer": "smpte2084",
    "color_primaries": "bt2020", "avg_frame_rate": "24/1",
    "side_data_list": [
        {"side_data_type": "Mastering display metadata", "min_luminance": "50/10000", "max_luminance": "40000000/10000"},
        {"side_data_type": "Content light level metadata", "max_content": 600, "max_average": 180},
    ],
}
PLAIN = {"index": 0, "codec_name": "h264", "codec_type": "video", "width": 1920, "height": 1080,
         "pix_fmt": "yuv420p", "color_range": "tv", "color_space": "bt709", "color_transfer": "bt709",
         "color_primaries": "bt709", "bits_per_raw_sample": "8", "avg_frame_rate": "30/1"}
SOUND = {"index": 1, "codec_type": "audio", "channels": 2, "sample_rate": "48000"}
# The Composition Graph Of The Bundled Example Before HDR Handling Existed.
LEGACY_GRAPH = (
    "[0:0]settb=AVTB,setpts=PTS/1,fps=fps=24:start_time=0,crop=56:100:52:0:exact=1,scale=360:640,setsar=1,"
    "pad=360:640:0:0,setsar=1,format=yuv420p,tpad=stop_mode=clone:stop_duration=2,trim=duration=2,"
    "setpts=PTS-STARTPTS[v0];\n"
    "anullsrc=r=48000:cl=stereo,atrim=duration=2,asetpts=PTS-STARTPTS[a0];\n"
    "[1:0]settb=AVTB,setpts=PTS/1,fps=fps=24:start_time=0,crop=47:83:65:8:exact=1,scale=360:640,setsar=1,"
    "format=gbrp,lutrgb=r='clip((clip(val*1.05,0,255)-127.5)*1.04+127.5,0,255)':"
    "g='clip((clip(val*1.05,0,255)-127.5)*1.04+127.5,0,255)':"
    "b='clip((clip(val*1.05,0,255)-127.5)*1.04+127.5,0,255)',"
    "colorchannelmixer=rr=1.09444:rg=-0.0858:rb=-0.00864:gr=-0.02556:gg=1.0342:gb=-0.00864:"
    "br=-0.02556:bg=-0.0858:bb=1.11136,pad=360:640:0:0,setsar=1,format=yuv420p,"
    "tpad=stop_mode=clone:stop_duration=2,trim=duration=2,setpts=PTS-STARTPTS[v1];\n"
    "anullsrc=r=48000:cl=stereo,atrim=duration=2,asetpts=PTS-STARTPTS[a1];\n"
    "[v0][a0][v1][a1]concat=n=2:v=1:a=1[base][voice];\n"
    "[2:0]fps=24,scale=120:-2,setsar=1,format=rgba,setpts=PTS-STARTPTS+1/TB[o0];\n"
    "[base][o0]overlay=x=18:y=54:eof_action=pass:repeatlast=0:enable='gte(t,1)*lt(t,1.75)'[ov0];\n"
    "[ov0]subtitles=filename=captions.ass,format=yuv420p[picture];\n"
    "[3:0]aresample=48000:async=1:first_pts=0,aformat=sample_fmts=fltp:sample_rates=48000:"
    "channel_layouts=stereo,atrim=duration=4,asetpts=PTS-STARTPTS,volume=0.7,adelay=0S:all=1[m0];\n"
    "[voice][m0]amix=inputs=2:duration=first:normalize=0,aformat=channel_layouts=stereo[sound]"
)


def meta(video, audio=SOUND, seconds=12.0):
    return {"duration": seconds, "video": video, "audio": audio, "format": "mov,mp4,m4a,3gp,3g2,mj2",
            "picture": picture_info(video)}


class ProbeTests(unittest.TestCase):
    def test_phone_clip_reports_displayed_geometry_depth_color_and_dolby_vision(self):
        info = picture_info(PHONE)
        self.assertEqual(info["hdr"], "hlg")
        self.assertEqual((info["color_transfer"], info["color_primaries"], info["color_space"]),
                         ("arib-std-b67", "bt2020", "bt2020nc"))
        self.assertEqual(info["bit_depth"], 10)
        self.assertEqual(info["rotation"], 90)
        self.assertEqual((info["coded_size"], info["displayed_size"]), ([3840, 2160], [2160, 3840]))
        self.assertEqual(info["dolby_vision"], {"profile": 8, "level": 4, "compatibility": 4})
        self.assertAlmostEqual(info["frame_rate"], 29.97, places=2)

    def test_pq_peak_prefers_content_light_level_and_sdr_is_not_flagged(self):
        info = picture_info(MASTERED)
        self.assertEqual((info["hdr"], info["peak_nits"], info["rotation"]), ("pq", 600, 0))
        self.assertEqual(picture_info(dict(MASTERED, side_data_list=MASTERED["side_data_list"][:1]))["peak_nits"], 4000)
        plain = picture_info(PLAIN)
        self.assertIsNone(plain["hdr"])
        self.assertEqual((plain["bit_depth"], plain["displayed_size"]), (8, [1920, 1080]))
        self.assertIsNone(picture_info(None))

    def test_rotation_tag_sample_aspect_and_bit_depth_fallbacks(self):
        legacy = {"width": 1440, "height": 1080, "sample_aspect_ratio": "4:3", "tags": {"rotate": "270"}}
        info = picture_info(legacy)
        self.assertEqual((info["rotation"], info["displayed_size"]), (270, [1080, 1920]))
        self.assertEqual(picture_info({"width": 8, "height": 8, "side_data_list": [{"rotation": 180}]})["displayed_size"], [8, 8])
        depths = {"yuv420p": 8, "yuvj420p": 8, "nv12": 8, "rgb24": 8, "yuv422p10le": 10, "p010le": 10,
                  "gbrp12le": 12, "gray16le": 16, "rgb48le": 16, "rgba64be": 16, "gbrpf32le": 32, "yuv420p9le": 9}
        for name, depth in depths.items():
            with self.subTest(pix_fmt=name):
                self.assertEqual(timeline.bit_depth({"pix_fmt": name}), depth)
        self.assertEqual(timeline.bit_depth({"pix_fmt": "yuv420p", "bits_per_raw_sample": "10"}), 10)

    def test_probe_adds_a_picture_summary_beside_the_raw_streams(self):
        listing = {"format": {"duration": "3.5", "format_name": "mov"},
                   "streams": [{"codec_type": "video", "disposition": {"attached_pic": 1}, "index": 0},
                               dict(PHONE, index=1), dict(SOUND, index=2)]}

        class Done:
            stdout = json.dumps(listing)

        with patch.object(timeline, "run", return_value=Done()), patch.object(timeline, "binary", return_value="ffprobe"):
            result = timeline.probe(Path("clip"))
        self.assertEqual(result["video"]["index"], 1)
        self.assertEqual(result["picture"]["hdr"], "hlg")
        self.assertEqual(result["picture"]["displayed_size"], [2160, 3840])
        self.assertEqual(set(result), {"duration", "video", "audio", "format", "picture"})

    def test_framing_uses_the_displayed_picture(self):
        geometry = framing(PHONE, 1080, 1920, "cover", 1, 0, 0)
        self.assertEqual(geometry["crop"], [2160, 3840, 0, 0])
        self.assertEqual(geometry["scale"], [1080, 1920])
        sideways = framing(dict(PHONE, side_data_list=[]), 1080, 1920, "cover", 1, 0, 0)
        self.assertEqual(sideways["crop"][:2], [1215, 2160])
        tagged = framing({"width": 3840, "height": 2160, "tags": {"rotate": "90"}}, 1080, 1920, "cover", 1, 0, 0)
        self.assertEqual(tagged["crop"], [2160, 3840, 0, 0])


class ProjectTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="source fixtures ")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        # Placeholder Sources. Their Stream Data Comes From The Mocked Probe Below.
        self.sources = {"phone.source": meta(PHONE), "master.source": meta(MASTERED), "old.source": meta(PLAIN)}
        for name in self.sources:
            (self.root / name).write_bytes(b"Placeholder")
        self.doc = {
            "version": 1, "title": "Mixed Sources", "canvas": {"width": 1080, "height": 1920, "fps": 30, "fit": "cover"},
            "assets": {"Phone": {"path": "phone.source", "kind": "video"},
                       "Master": {"path": "master.source", "kind": "video"},
                       "Old": {"path": "old.source", "kind": "video"}},
            "shots": [{"asset": "Phone", "in": 0, "out": 2}, {"asset": "Old", "in": 1, "out": 3},
                      {"asset": "Phone", "in": 4, "out": 5, "brightness": 1.1}],
        }
        probe = patch.object(timeline, "probe", side_effect=lambda path: self.sources[Path(path).name])
        probe.start()
        self.addCleanup(probe.stop)

    def model(self):
        return prepare(json.loads(json.dumps(self.doc)), self.root)

    def test_hdr_shots_are_tone_mapped_by_default_and_warned_about(self):
        model = self.model()
        self.assertEqual([shot.get("tone_map") for shot in model["shots"]], [True, None, True])
        self.assertEqual([shot.get("hdr") for shot in model["shots"]], ["hlg", None, "hlg"])
        self.assertNotIn("hdr", model["shots"][1])
        notes = " ".join(model["warnings"])
        self.assertIn("Asset Phone Is HLG HDR With Dolby Vision Profile 8", notes)
        self.assertIn("Tone Mapping Converts Shot 1, Shot 3 To Standard Dynamic Range Once", notes)
        self.assertIn("Stored 3840 By 2160 With A 90 Degree Display Rotation", notes)
        self.assertIn("Displayed 2160 By 3840 Picture", notes)
        self.assertFalse([note for note in model["warnings"] if "Asset Old" in note])
        self.assertEqual(model["shots"][0]["geometry"]["crop"], [2160, 3840, 0, 0])

    def test_tone_map_turns_off_per_shot_and_per_project(self):
        self.doc["shots"][2]["tone_map"] = False
        model = self.model()
        self.assertEqual([shot.get("tone_map") for shot in model["shots"]], [True, None, False])
        self.assertTrue(any("Tone Mapping Is Off For Shot 3" in note for note in model["warnings"]))
        self.doc["canvas"]["tone_map"] = False
        self.doc["shots"][0]["tone_map"] = True
        model = self.model()
        self.assertEqual([shot.get("tone_map") for shot in model["shots"]], [True, None, False])
        del self.doc["shots"][0]["tone_map"], self.doc["shots"][2]["tone_map"]
        self.assertEqual([shot.get("tone_map") for shot in self.model()["shots"]], [False, None, False])
        for place in (self.doc["canvas"], self.doc["shots"][1]):
            place["tone_map"] = "off"
            with self.assertRaisesRegex(EditError, "Requires true Or false"):
                self.model()
            place["tone_map"] = True

    def test_graph_converts_each_hdr_shot_exactly_once_before_color_changes(self):
        self.doc["overlays"] = [{"asset": "Master", "at": 0.5, "end": 1.5, "width": 400}]
        model = self.model()
        _, expression = graph(model)
        lines = expression.split(";\n")
        shots = [line for line in lines if "settb=AVTB" in line]
        self.assertEqual([line.count("tonemap=tonemap=") for line in shots], [1, 0, 1])
        self.assertEqual([line.count("zscale=") for line in shots], [2, 0, 2])
        hlg = ("zscale=transferin=arib-std-b67:primariesin=bt2020:matrixin=bt2020nc:rangein=limited:"
               "transfer=linear:primaries=bt709:npl=203,format=gbrpf32le,"
               "tonemap=tonemap=mobius:param=0.3:desat=0:peak=4.926108374,"
               "zscale=transferin=linear:primariesin=bt709:transfer=bt709:primaries=bt709:matrix=bt709:"
               "range=limited:dither=error_diffusion,format=yuv420p,")
        self.assertEqual(tone_filters(PHONE), hlg)
        self.assertIn("crop=2160:3840:0:0:exact=1,scale=1080:1920,setsar=1," + hlg + "pad=1080:1920:0:0", shots[0])
        self.assertLess(shots[2].index("tonemap="), shots[2].index("lutrgb="))
        overlay = next(line for line in lines if line.endswith("[o0]"))
        self.assertEqual(overlay.count("tonemap=tonemap="), 1)
        self.assertIn("transferin=smpte2084", overlay)
        self.assertIn("peak=2.955665025", overlay)
        self.assertLess(overlay.index("tonemap="), overlay.index("format=rgba"))
        self.assertEqual(expression.count("tonemap=tonemap="), 3)
        self.assertEqual(tone_filters(PLAIN), "")

    def test_turning_tone_mapping_off_restores_the_plain_chain(self):
        self.doc["canvas"]["tone_map"] = False
        _, expression = graph(self.model())
        self.assertNotIn("tonemap", expression)
        self.assertNotIn("zscale", expression)

    def test_missing_filter_is_named_and_only_matters_when_tone_mapping_is_on(self):
        model = self.model()
        with patch.object(media, "available_filters", return_value={"scale", "tonemap"}):
            self.assertEqual(media.missing_tone_filters(model), ["zscale"])
            with self.assertRaisesRegex(EditError, "Lacks The zscale Filter Needed To Convert HDR Shots"):
                process(model)
            with self.assertRaisesRegex(EditError, "zscale"):
                still(model, 0.5, self.root / "frame.png")
        with patch.object(media, "available_filters", return_value=set()):
            with self.assertRaisesRegex(EditError, "zscale And tonemap Filters"):
                media.require_tone_filters(model)
            self.doc["canvas"]["tone_map"] = False
            self.assertEqual(media.missing_tone_filters(self.model()), [])
        self.assertFalse(list(self.root.glob("*.png")))

    def test_validate_prints_warnings_for_hdr_rotation_and_a_limited_build(self):
        project = self.root / "edit.json"
        project.write_text(json.dumps(self.doc), encoding="utf-8")
        for missing, expected in (([], False), (["zscale"], True)):
            output = io.StringIO()
            with patch.object(edit_video, "missing_tone_filters", return_value=missing), contextlib.redirect_stdout(output):
                edit_video.main(["validate", str(project)])
            report = json.loads(output.getvalue())
            self.assertEqual(report["command"], "validate")
            self.assertTrue(any("HLG HDR" in note for note in report["warnings"]))
            self.assertTrue(any("Display Rotation" in note for note in report["warnings"]))
            self.assertEqual(any("This FFmpeg Build Lacks zscale" in note for note in report["warnings"]), expected)

    def test_unusual_sources_get_plain_warnings(self):
        profile5 = dict(PHONE, color_transfer="unknown", color_primaries="unknown", color_space="unknown",
                        side_data_list=[{"side_data_type": "DOVI configuration record", "dv_profile": 5,
                                         "dv_bl_signal_compatibility_id": 0}])
        self.sources["phone.source"] = meta(profile5)
        self.sources["old.source"] = meta(dict(PLAIN, color_primaries="bt2020", color_transfer="unknown",
                                               side_data_list=[{"rotation": 45}]))
        notes = " ".join(self.model()["warnings"])
        self.assertIn("Asset Phone Is Dolby Vision Profile 5 Without A Standard Base Layer", notes)
        self.assertIn("Asset Old Has bt2020 Primaries Without A PQ Or HLG Transfer (unspecified)", notes)
        self.assertIn("Only Right-Angle Rotations Are Framed Correctly", notes)


@unittest.skipUnless(FFMPEG, "FFmpeg Required")
class StandardProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="still fixtures ")
        cls.base = Path(cls.temp.name)
        cls.path = example(cls.base / "Plain Cut")
        cls.model = prepare(load(cls.path), cls.path.parent)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_standard_project_graph_and_model_are_unchanged(self):
        inputs, expression = graph(self.model)
        self.assertEqual(expression, LEGACY_GRAPH)
        self.assertEqual(inputs[:6], ["-loop", "1", "-framerate", "24", "-t", "2"])
        self.assertEqual(self.model["warnings"], [])
        self.assertEqual(set(self.model["shots"][0]), {
            "asset", "at", "brightness", "contrast", "duration", "end", "fit", "gain", "geometry", "pan_x",
            "pan_y", "saturation", "speed", "start", "zoom"})
        self.assertEqual(set(self.model["overlays"][0]), {"asset", "at", "end", "start", "width", "x", "y"})

    def test_validate_output_has_no_warning_key_for_a_standard_project(self):
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "edit_video.py"), "validate", str(self.path)],
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), {"command": "validate", "title": "Colour And Rhythm",
                                                     "duration_seconds": 4.0, "fps": 24, "shots": 2})

    def test_blank_segments_hold_time_without_opening_sources(self):
        scene = media.focus(self.model, 2.5, 2.6)
        self.assertEqual([bool(shot.get("blank")) for shot in scene["shots"]], [True, False])
        # The Overlay Ends Before The Window. The Four-Second Sound Cue Still Plays Through It.
        self.assertEqual((scene["overlays"], len(scene["audio"])), ([], 1))
        inputs, expression = graph(dict(scene, audio=[]))
        self.assertEqual(inputs.count("-i"), 1)
        self.assertEqual(graph(scene)[0].count("-i"), 2)
        self.assertIn("color=c=black:s=360x640:r=24,format=yuv420p,setsar=1,trim=duration=2,setpts=PTS-STARTPTS[v0]", expression)

    @unittest.skipUnless(FFMPEG, "FFmpeg Required")
    def test_still_matches_the_same_frame_of_the_complete_composition(self):
        for seconds, frame, shot in ((1.25, 30, 1), (2.5, 60, 2), (3.96, 95, 2)):
            with self.subTest(seconds=seconds):
                target = self.base / f"frame {frame}.png"
                report = still(self.model, seconds, target)
                self.assertEqual((report["frame"], report["shot"]), (frame, shot))
                inputs, expression = graph(self.model)
                expression += f";\n[picture]select='eq(n,{frame})'[frame];\n[sound]anullsink"
                with tempfile.TemporaryDirectory() as work:
                    (Path(work) / "captions.ass").write_text(media.ass(self.model), encoding="utf-8")
                    args = [shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", *inputs,
                            "-filter_complex_threads", "1", "-filter_complex", expression, "-map", "[frame]",
                            "-frames:v", "1", "-c:v", "png", "-f", "image2pipe", "pipe:1"]
                    whole = subprocess.run(args, cwd=work, capture_output=True, check=True).stdout
                self.assertEqual(target.read_bytes(), whole)
                self.assertEqual(target.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
        with self.assertRaisesRegex(EditError, "Already Exists"):
            still(self.model, 1.25, self.base / "frame 30.png")
        for bad, message in (((4.0, self.base / "late.png"), "Choose A Time"), ((1.0, self.base / "frame.jpg"), "PNG")):
            with self.assertRaisesRegex(EditError, message):
                still(self.model, *bad)
        self.assertEqual({path.suffix for path in self.base.rglob("*") if path.is_file()}, {".png", ".wav", ".json"})

    @unittest.skipUnless(FFMPEG, "FFmpeg Required")
    def test_still_command_reports_the_frame_and_protects_existing_files(self):
        target = self.base / "From Command.png"
        command = [sys.executable, "-B", str(SCRIPTS / "edit_video.py"), "still", str(self.path), str(target), "--at", "0.5"]
        first = subprocess.run(command + ["--no-burn"], capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        report = json.loads(first.stdout)
        self.assertEqual((report["command"], report["frame"], report["seconds"], report["shot"]), ("still", 12, 0.5, 1))
        again = subprocess.run(command, capture_output=True, text=True)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn("Output Already Exists", again.stderr)


@unittest.skipUnless(FFMPEG and {"zscale", "tonemap"} <= media.available_filters(), "Tone Mapping Needs zscale And tonemap.")
class ToneMapPixelTests(unittest.TestCase):
    """Run The Real Graph On Generated HLG And PQ Patterns And Read Pixels Back Through A Pipe."""

    WIDTH, HEIGHT = 180, 320

    def render(self, video, source, tone):
        w, h = self.WIDTH, self.HEIGHT
        shot = dict(asset="Phone", start=0, end=0.25, at=0, duration=0.25, speed=1, gain=0, fit="cover",
                    geometry=framing(video, w, h, "cover", 1, 0, 0), brightness=1, contrast=1, saturation=1,
                    hdr=picture_info(video)["hdr"], tone_map=tone)
        model = {"width": w, "height": h, "fps": 24, "duration": 0.25, "overlays": [], "captions": [], "audio": [],
                 "assets": {"Phone": {"kind": "video", "path": "generated", "video": video, "audio": None}},
                 "shots": [shot]}
        _, expression = graph(model)
        args = [shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "lavfi", "-i", source,
                "-filter_complex_threads", "1", "-filter_complex", expression + ";[sound]anullsink",
                "-map", "[picture]", "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "yuv420p", "pipe:1"]
        data = subprocess.run(args, capture_output=True, check=True).stdout
        self.assertEqual(len(data), w * h * 3 // 2)
        luma = data[w * (h // 2) + w // 2]
        blue = data[w * h + (w // 2) * (h // 4) + w // 4]
        red = data[w * h + (w // 2) * (h // 2) + (w // 2) * (h // 4) + w // 4]
        return luma, blue, red

    def gray(self, level, transfer):
        # The Generated Frames Are Already Upright, As FFmpeg Delivers A Rotated Phone Clip.
        return (f"color=black:s={self.WIDTH}x{self.HEIGHT}:r=24:d=0.25,format=yuv420p10le,"
                f"geq=lum={round(64 + level * 876)}:cb=512:cr=512,"
                f"setparams=color_trc={transfer}:color_primaries=bt2020:colorspace=bt2020nc:range=tv")

    def test_hlg_midtones_hold_and_highlights_roll_off_on_a_rotated_clip(self):
        clip = dict(PHONE, width=self.HEIGHT, height=self.WIDTH)
        expected = {0.25: 77, 0.5: 138, 0.75: 203, 1.0: 235}
        for level, target in expected.items():
            with self.subTest(level=level):
                luma, blue, red = self.render(clip, self.gray(level, "arib-std-b67"), True)
                self.assertAlmostEqual(luma, target, delta=3)
                self.assertAlmostEqual(blue, 128, delta=1)
                self.assertAlmostEqual(red, 128, delta=1)
        untouched, _, _ = self.render(clip, self.gray(0.5, "arib-std-b67"), False)
        self.assertAlmostEqual(untouched, 125, delta=2)

    def test_pq_uses_reference_white_and_the_metadata_peak(self):
        clip = dict(MASTERED, width=self.WIDTH, height=self.HEIGHT)
        # PQ Code 0.5807 Is 203 Nits. With A 600 Nit Peak The Roll-Off Places It Near 86 Percent.
        white, _, _ = self.render(clip, self.gray(0.5807, "smpte2084"), True)
        self.assertAlmostEqual(white, 205, delta=3)
        dim, _, _ = self.render(clip, self.gray(0.38, "smpte2084"), True)
        self.assertAlmostEqual(dim, 109, delta=3)
        flat, _, _ = self.render(clip, self.gray(0.5807, "smpte2084"), False)
        self.assertAlmostEqual(flat, 16 + round(219 * 0.5807), delta=2)

    def test_chain_accepts_rgb_full_range_and_untagged_layouts(self):
        layouts = [
            ({"pix_fmt": "gbrp10le", "color_transfer": "smpte2084", "color_primaries": "bt2020"}, "rangein=full", "matrixin"),
            ({"pix_fmt": "yuv444p12le", "color_transfer": "arib-std-b67", "color_primaries": "bt2020",
              "color_space": "bt2020nc", "color_range": "pc"}, "matrixin=bt2020nc:rangein=full", None),
            ({"pix_fmt": "yuv420p10le", "color_transfer": "smpte2084"}, "primariesin=bt2020:matrixin=bt2020nc:rangein=limited", None),
            ({"pix_fmt": "p010le", "color_transfer": "arib-std-b67", "color_primaries": "bt2020",
              "color_space": "bt2020nc", "color_range": "tv"}, "rangein=limited", None),
        ]
        for video, present, absent in layouts:
            with self.subTest(layout=video["pix_fmt"]):
                chain = tone_filters(video)
                self.assertIn(present, chain)
                if absent:
                    self.assertNotIn(absent, chain)
                source = f"testsrc2=size=128x72:rate=24:duration=0.2,format={video['pix_fmt']}"
                done = subprocess.run([shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "lavfi",
                                       "-i", source, "-vf", chain.rstrip(","), "-f", "null", "-"], capture_output=True, text=True)
                self.assertEqual(done.returncode, 0, done.stderr)

    def test_wide_gamut_color_regains_its_saturation(self):
        clip = dict(PHONE, width=self.HEIGHT, height=self.WIDTH)
        source = (f"color=0xC00000:s={self.WIDTH}x{self.HEIGHT}:r=24:d=0.25,format=gbrp,"
                  "zscale=transferin=bt709:primariesin=bt709:rangein=full:transfer=arib-std-b67:"
                  "primaries=bt2020:matrix=bt2020nc:range=limited:npl=203,format=yuv420p10le")
        luma, blue, red = self.render(clip, source, True)
        flat_luma, flat_blue, flat_red = self.render(clip, source, False)
        # The Original Standard Red Reads About 51, 109, 212 In BT.709.
        self.assertAlmostEqual(luma, 51, delta=6)
        self.assertAlmostEqual(red, 212, delta=10)
        self.assertGreater(red - 128, 1.6 * (flat_red - 128))
        self.assertLess(flat_red, 180)


if __name__ == "__main__":
    unittest.main()
