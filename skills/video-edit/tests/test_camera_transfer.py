import contextlib
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import camera_transfer as camera

cv2, np = camera.cv2, camera.np
VISION = cv2 is not None
FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


def sample(t=0., x=0., y=0., zoom=1., angle=0.):
    return dict(t=t, x=x, y=y, zoom=zoom, angle=angle, confidence=1., status="tracked")


def plan(samples, width=320, height=240, duration=1., **settings):
    defaults = dict(strength=1., anchor_x=.5, anchor_y=.5, fps=24., timing="hold", edge_mode="reflect")
    return {"schema": "camera-transfer/v1", "source": dict(width=width, height=height, duration=duration),
            "reference": {"duration": duration}, "settings": defaults | settings, "samples": samples}


def texture(width, height):
    rng = np.random.default_rng(309)
    result = cv2.GaussianBlur(rng.integers(0, 256, (height, width), dtype=np.uint8), (5, 5), .85)
    for _ in range(75):
        center = tuple(map(int, rng.integers([0, 0], [width, height])))
        cv2.circle(result, center, int(rng.integers(2, 7)), int(rng.integers(20, 240)), -1)
    return result


def reference_frames():
    width, height = 320, 240
    base = texture(width, height)
    frames = []
    for i in range(9):
        forward = cv2.getRotationMatrix2D(((width - 1) / 2, (height - 1) / 2), -i * .8, 1.008 ** i)
        forward[:, 2] += [1.4 * i, -.7 * i]
        frame = cv2.warpAffine(base, forward, (width, height), borderMode=cv2.BORDER_REFLECT)
        # An Independently Moving Subject Covers Part Of The Background.
        frame[60:105, 35 + i * 4:105 + i * 4] = base[60:105, 35:105]
        frames.append(frame)
    return frames


@unittest.skipUnless(VISION, "Camera Test Requires OpenCV And NumPy.")
class MotionTests(unittest.TestCase):
    def test_accumulated_global_motion_against_independent_moving_subject(self):
        frames = reference_frames()
        result = camera.track(frames, [i / 30 for i in range(len(frames))])
        last = result[-1]
        self.assertTrue(all(s["status"] == "tracked" for s in result[1:]))
        self.assertGreater(last["confidence"], .5)
        self.assertAlmostEqual(last["x"] * 319, 11.2, delta=.65)
        self.assertAlmostEqual(last["y"] * 239, -5.6, delta=.65)
        self.assertAlmostEqual(last["angle"], 6.4, delta=.32)
        self.assertAlmostEqual(last["zoom"], 1.008 ** 8, delta=.006)

    def test_translation_fallback_and_no_texture_hold(self):
        frame = texture(240, 160)
        shifted = np.roll(np.roll(frame, 4, axis=1), -3, axis=0)
        blank = np.zeros_like(frame)
        with patch.object(camera, "feature_motion", return_value=None):
            result = camera.track([frame, shifted, blank, blank], [0., .03, .08, .11])
        self.assertEqual([p["status"] for p in result], ["origin", "translation", "held", "held"])
        self.assertAlmostEqual(result[1]["x"] * 239, 4, delta=.22)
        self.assertAlmostEqual(result[1]["y"] * 159, -3, delta=.22)
        self.assertEqual(result[1]["x"], result[-1]["x"])
        self.assertEqual(result[-1]["confidence"], 0)

    def test_hard_cut_is_held_then_new_scene_tracks_without_a_jump(self):
        old = texture(320, 240)
        fresh = cv2.GaussianBlur(np.random.default_rng(782).integers(0, 256, old.shape, dtype=np.uint8), (5, 5), .85)
        frames = [old, np.roll(old, 2, axis=0), fresh, np.roll(fresh, 4, axis=1)]
        result = camera.track(frames, [0, .1, .2, .3])
        self.assertEqual([p["status"] for p in result], ["origin", "tracked", "held", "tracked"])
        self.assertEqual(result[2]["angle"], result[1]["angle"])
        self.assertAlmostEqual(result[-1]["x"] * 319, 4, delta=.2)
        self.assertAlmostEqual(result[-1]["y"] * 239, 2, delta=.2)

    def test_cover_contains_every_output_corner_with_asymmetric_anchor(self):
        w, h = 321, 180
        p = plan([sample(0., -.13, .085, .8, 12.5)], w, h,
                 edge_mode="cover", anchor_x=.1, anchor_y=.9, strength=1.4)
        matrix = camera.MotionPath(p).matrix(0.)
        inverse = cv2.invertAffineTransform(matrix)
        coords = np.float64([[0, 0], [w - 1, 0], [0, h - 1], [w - 1, h - 1]])
        inside = coords @ inverse[:, :2].T + inverse[:, 2]
        self.assertTrue(np.all(inside >= -1e-7))
        self.assertTrue(np.all(inside <= [w - 1 + 1e-7, h - 1 + 1e-7]))

    def test_zero_strength_is_identity_and_fractional_translation_resamples(self):
        w, h = 101, 81
        frame = np.zeros((h, w), np.uint8)
        frame[40, 45] = 200
        p = plan([sample(x=.5 / (w - 1))], w, h)
        warped = camera.MotionPath(p).warp(frame, 0.)
        self.assertEqual(tuple(warped[40, 45:47]), (100, 100))
        p["samples"] = [sample(0, .2, .1, 2., 125.)]
        p["settings"].update(strength=0, edge_mode="cover", anchor_x=.9)
        np.testing.assert_array_equal(camera.MotionPath(p).warp(frame, 0), frame)

    def test_reflected_edges_match_browser_reflect_101_without_duplicate_end_pixels(self):
        frame = np.tile(np.uint8([10, 20, 30, 40, 50]), (3, 1))
        p = plan([sample(x=2 / 4)], 5, 3)
        shifted = camera.MotionPath(p).warp(frame, 0)
        np.testing.assert_array_equal(shifted[1], [30, 20, 10, 20, 30])
        p["samples"] = [sample(x=-2 / 4)]
        np.testing.assert_array_equal(camera.MotionPath(p).warp(frame, 0)[1], [30, 40, 50, 40, 30])

    def test_interpolation_uses_reference_timestamps_and_log_zoom(self):
        p = plan([sample(), sample(.3, .07, -.04, 2., 35.), sample(.9, .24, .23, 4., 55.)],
                 duration=2., timing="stretch")
        p["reference"]["duration"] = 1.
        matrix = camera.MotionPath(p).matrix(.3)
        self.assertAlmostEqual(math.hypot(*matrix[:, 0]), math.sqrt(2), places=9)
        self.assertAlmostEqual(math.degrees(math.atan2(matrix[1, 0], matrix[0, 0])), 17.5)
        q = matrix @ [159.5, 119.5, 1]
        np.testing.assert_allclose(q, [159.5 + .035 * 319, 119.5 - .02 * 239])
        p["settings"]["timing"] = "hold"
        motion = camera.MotionPath(p)
        np.testing.assert_allclose(motion.matrix(1.8), motion.matrix(.9))

    def test_invalid_timestamp_and_nonfinite_samples_rejected(self):
        for points in ([sample(.1)], [sample(0), sample(0)], [sample(x=float("nan"))], [sample(zoom=0)]):
            with self.assertRaises(ValueError):
                camera.MotionPath(plan(points))


class GateTests(unittest.TestCase):
    def test_concurrent_save_and_interrupted_write_leave_one_complete_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "motion.json"
            with self.assertRaises(RuntimeError):
                with camera.new_destination(path) as staged:
                    staged.write_text("Partial")
                    raise RuntimeError("Interrupted")
            self.assertEqual(list(Path(tmp).iterdir()), [])
            with self.assertRaises(FileExistsError):
                with camera.new_destination(path) as staged:
                    staged.write_text("First Writer")
                    path.write_text("Existing Plan")
            self.assertEqual(path.read_text(), "Existing Plan")
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_an_unapproved_export_performs_no_io(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "never.mp4"
            with self.assertRaisesRegex(ValueError, "Approval"):
                camera.main(["render", "missing.json", str(path)])
            with self.assertRaisesRegex(ValueError, "Approval"):
                camera.process({}, {}, path)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_probe_applies_display_rotation_sar_and_skips_cover_art(self):
        media = {"format": {"duration": "1.125"}, "streams": [
            {"index": 0, "codec_type": "video", "disposition": {"attached_pic": 1}},
            {"index": 1, "codec_type": "video", "width": 200, "height": 100, "sample_aspect_ratio": "3:2",
             "side_data_list": [{"rotation": -90}], "avg_frame_rate": "24000/1001"},
            {"index": 2, "codec_type": "audio", "codec_name": "aac"}]}
        with tempfile.TemporaryDirectory() as tmp, patch("subprocess.check_output", return_value=json.dumps(media)):
            path = Path(tmp) / "metadata.txt"
            path.write_text("Data")
            result = camera.probe(path)
        self.assertEqual((result["width"], result["height"], result["stream"]), (100, 300, 1))
        self.assertAlmostEqual(result["fps"], 24000 / 1001)
        self.assertEqual(result["audio_codecs"], ["aac"])


@unittest.skipUnless(VISION and FFMPEG, "Camera Integration Requires FFmpeg, FFprobe, NumPy And OpenCV.")
class MediaTests(unittest.TestCase):
    def test_original_timed_still_sequence_through_cli_and_null_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            lines = ["ffconcat version 1.0"]
            for index, frame in enumerate(reference_frames()[:5]):
                path = folder / f"still{index}.pgm"
                with path.open("wb") as f:
                    f.write(f"P5\n320 240\n255\n".encode() + frame.tobytes())
                lines += [f"file '{path.name}'", "duration 0.12" if index % 2 else "duration 0.08"]
            source = folder / "stills.ffconcat"
            source.write_text("\n".join(lines) + "\n", encoding="ascii")
            target_plan = folder / "motion.json"
            review = folder / "review.html"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                camera.main(["analyze", str(source), str(source), str(target_plan)])
                camera.main(["review", str(target_plan), "--output", str(review)])
                camera.main(["check", str(target_plan)])
            recorded = json.loads(target_plan.read_text(encoding="utf-8"))
            self.assertEqual([round(s["t"], 2) for s in recorded["samples"]], [0, .08, .2, .28, .4])
            self.assertEqual(recorded["samples"][-1]["status"], "tracked")
            self.assertIn('id="embeddedPlan"', review.read_text(encoding="utf-8"))
            self.assertIn("SHA256=", stdout.getvalue())
            self.assertEqual({p.suffix for p in folder.iterdir()}, {".pgm", ".ffconcat", ".json", ".html"})

    def test_cfr_null_pipeline_preserves_stereo_samples_and_transformed_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sound.wav"
            rate, fps, w, h = 24000, 24, 80, 64
            signal = np.random.default_rng(306).integers(-10000, 10000, (rate, 2), dtype=np.int16)
            with wave.open(str(path), "wb") as output:
                output.setparams((2, 2, rate, 0, "NONE", ""))
                output.writeframes(signal.astype("<i2").tobytes())
            info = dict(path=str(path), width=w, height=h, duration=1., audio_codecs=["pcm_s16le"])
            p = plan([sample(), sample(.5, .1, -.09, 1.05, 7)], w, h, fps=fps, edge_mode="cover")
            original = cv2.cvtColor(texture(w, h), cv2.COLOR_GRAY2BGR)
            motion = camera.MotionPath(p)
            expected = [motion.warp(original, i / fps) for i in range(fps)]
            with patch.object(camera, "decode", side_effect=lambda *args, **kwargs: (original for _ in range(fps))):
                result = camera.process(p, info)
            video_hash = hashlib.sha256(b"".join(f.tobytes() for f in expected)).hexdigest()
            audio_hash = hashlib.sha256((signal.astype("<i4") * 65536).astype("<i4").tobytes()).hexdigest()
            self.assertIn(f"0,v,SHA256={video_hash}", result)
            self.assertIn(f"1,a,SHA256={audio_hash}", result)
            self.assertEqual(list(Path(tmp).iterdir()), [path])

    def test_variable_frame_rate_resampling_keeps_picture_active_at_each_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            lines = ["ffconcat version 1.0"]
            for i, value in enumerate([30, 80, 130, 180]):
                name = f"gray{i}.pgm"
                (folder / name).write_bytes(b"P5\n24 24\n255\n" + bytes([value] * 576))
                lines += [f"file '{name}'", "duration " + ["0.08", "0.12", "0.08", "0.12"][i]]
            source = folder / "sequence.ffconcat"
            source.write_text("\n".join(lines) + "\n", encoding="ascii")
            info = camera.probe(source)
            p = plan([sample()], 24, 24, info["duration"], fps=10)
            frames = list(camera.output_frames(info, camera.MotionPath(p)))
            self.assertEqual([int(f[12, 12, 0]) for f in frames], [30, 80, 130, 180])
            p["settings"]["fps"] = 1.
            frames = list(camera.output_frames(info, camera.MotionPath(p)))
            self.assertEqual([int(f[12, 12, 0]) for f in frames], [30])

    def test_prores_and_h264_packet_timestamps_end_exactly_at_fractional_clip_duration(self):
        # The Frame CRC Muxer Emits Text Packet Diagnostics For Both Codec Paths.
        info = dict(width=80, height=64, duration=.6, path="unused", audio_codecs=[])
        frame = cv2.cvtColor(texture(80, 64), cv2.COLOR_GRAY2BGR)
        for filename in ("choice.mp4", "choice.mov"):
            args = camera.encoder_args(info, 4, Path(filename))
            del args[args.index("-i", args.index("pipe:0")):args.index("-fps_mode:v")]
            args[-2:] = ["-map", "0:v:0", "-f", "framecrc", "-"]
            result = camera.feed_encoder(args, iter([frame] * 3))
            packets = [list(map(int, line.split(",")[:4])) for line in result.splitlines() if not line.startswith("#")]
            self.assertIn("#tb 0: 1/1000000", result)
            self.assertEqual([(p[2], p[3]) for p in packets], [(0, 250000), (250000, 250000), (500000, 100000)])
            self.assertFalse(Path(filename).exists())


if __name__ == "__main__":
    unittest.main()
