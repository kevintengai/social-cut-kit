"""Loudness Measurement, The Single Linear Gain, Cue Windows, And Check Mixes.

Fixtures Are Generated WAV Files. Everything Is Metered Through FFmpeg's Null Sink. No Video File Is Written.
"""

import array
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import loudness
from example import example
from media import graph, mix, process, sound_graph
from timeline import EditError, binary, load, prepare

FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")
SUMMARY = """
[Parsed_ebur128_0 @ 000001] Summary:

  Integrated loudness:
    I:         -19.3 LUFS
    Threshold: -29.8 LUFS

  Loudness range:
    LRA:         4.2 LU
    Threshold: -39.6 LUFS
    LRA low:   -22.5 LUFS
    LRA high:  -18.3 LUFS

  True peak:
    Peak:       -3.1 dBFS
[Parsed_volumedetect_1 @ 000002] n_samples: 480000
[Parsed_volumedetect_1 @ 000002] mean_volume: -22.4 dB
[Parsed_volumedetect_1 @ 000002] max_volume: -3.4 dB
"""


def tone(path, seconds, level, hz=1000, spike=None):
    """Write A 48 kHz Stereo Sine. An Optional Spike Sets A Few Samples To A Higher Level."""
    rate = 48000
    frames = bytearray()
    for i in range(round(seconds * rate)):
        value = level * math.sin(2 * math.pi * hz * i / rate)
        if spike and spike[0] <= i / rate < spike[0] + 0.01:
            value = spike[1] * math.sin(2 * math.pi * 3000 * i / rate)
        frames += struct.pack("<hh", round(32767 * value), round(32767 * value))
    with wave.open(str(path), "wb") as wav:
        wav.setparams((2, 2, rate, 0, "NONE", ""))
        wav.writeframes(bytes(frames))


def sound_model(folder, voice_level=0.1, spike=None, cue_gain=0.5):
    tone(folder / "talk.wav", 5, voice_level, spike=spike)
    tone(folder / "tap.wav", 0.5, 0.05, hz=2000)
    stream = {"index": 0, "channels": 2, "sample_rate": "48000"}
    return {
        "title": "Sound Only", "width": 1080, "height": 1920, "fps": 30, "duration": 5.0,
        "overlays": [], "captions": [], "warnings": [],
        # A WAV Stands In For Camera Sound. The Sound-Only Graph Never Opens A Picture Stream.
        "assets": {"Talk": {"kind": "video", "path": str(folder / "talk.wav"), "duration": 5.0,
                            "video": {"index": 0, "width": 1080, "height": 1920}, "audio": stream},
                   "Tap": {"kind": "audio", "path": str(folder / "tap.wav"), "duration": 0.5,
                           "video": None, "audio": stream}},
        "shots": [dict(asset="Talk", start=0, end=2.5, at=0, duration=2.5, speed=1, gain=1, fit="cover"),
                  dict(asset="Talk", start=2.5, end=5, at=2.5, duration=2.5, speed=1, gain=1, fit="cover")],
        "audio": [dict(asset="Tap", at=1.0, end=1.5, start=0, gain=cue_gain)],
    }


class PlanTests(unittest.TestCase):
    def test_summary_is_read_and_silence_or_short_windows_have_no_loudness(self):
        self.assertEqual(loudness.read_meter(SUMMARY), {
            "integrated_lufs": -19.3, "loudness_range_lu": 4.2, "true_peak_dbtp": -3.1,
            "rms_dbfs": -22.4, "sample_peak_dbfs": -3.4})
        quiet = SUMMARY.replace("-19.3 LUFS", "-70.0 LUFS").replace("-3.1 dBFS", "-inf dBFS")
        quiet = quiet.replace("-22.4 dB", "-91.0 dB").replace("-3.4 dB", "-91.0 dB")
        self.assertEqual(loudness.read_meter(quiet), {
            "integrated_lufs": None, "loudness_range_lu": None, "true_peak_dbtp": None,
            "rms_dbfs": None, "sample_peak_dbfs": None})
        with self.assertRaisesRegex(EditError, "ebur128"):
            loudness.read_meter("No Meter Output")

    def test_one_gain_reaches_the_target_and_the_ceiling_is_checked(self):
        measured = {"integrated_lufs": -19.3, "true_peak_dbtp": -3.1}
        plan = loudness.gain_plan(measured)
        self.assertEqual((plan["target_lufs"], plan["true_peak_ceiling_dbtp"]), (-14.0, -1.5))
        self.assertEqual((plan["gain_db"], plan["true_peak_after_gain_dbtp"]), (5.3, 2.2))
        self.assertAlmostEqual(plan["linear_gain"], 10 ** (5.3 / 20), places=5)
        self.assertTrue(plan["breaches_ceiling"])
        self.assertEqual((plan["largest_gain_within_ceiling_db"], plan["loudness_at_largest_gain_lufs"]), (1.6, -17.7))
        self.assertIn("Above The -1.5 dBTP Ceiling", plan["note"])
        self.assertIn("+1.6 dB", plan["note"])
        gentle = loudness.gain_plan(measured, -20, -1)
        self.assertEqual((gentle["gain_db"], gentle["breaches_ceiling"]), (-0.7, False))
        self.assertIn("Inside The -1 dBTP Ceiling", gentle["note"])
        exact = loudness.gain_plan({"integrated_lufs": -15.5, "true_peak_dbtp": -3.0})
        self.assertEqual((exact["gain_db"], exact["true_peak_after_gain_dbtp"], exact["breaches_ceiling"]), (1.5, -1.5, False))
        silent = loudness.gain_plan({"integrated_lufs": None, "true_peak_dbtp": None})
        self.assertIsNone(silent["gain_db"])
        self.assertIn("No Gain Can Be Planned", silent["note"])
        for target, ceiling in ((-2, -1.5), (-14, 1), (float("nan"), -1.5)):
            with self.assertRaises(EditError):
                loudness.gain_plan(measured, target, ceiling)

    def test_master_gain_is_one_volume_filter_on_the_finished_mix(self):
        model = {"width": 96, "height": 64, "fps": 24, "duration": 1, "overlays": [], "captions": [], "audio": [],
                 "assets": {"AV": {"kind": "video", "path": "source", "video": {"index": 0, "width": 96, "height": 64},
                                   "audio": {"index": 1}}},
                 "shots": [{"asset": "AV", "start": 0, "end": 1, "duration": 1, "speed": 1, "gain": 1, "fit": "cover"}]}
        _, plain = graph(model)
        _, gained = graph(model, master_gain=1.995262)
        self.assertTrue(plain.endswith("[voice]anull[sound]"))
        self.assertTrue(gained.endswith("[voice]anull[blend];\n[blend]volume=1.995262[sound]"))
        self.assertEqual(gained.count("volume=1.995262"), 1)
        for word in ("acompressor", "alimiter", "loudnorm", "dynaudnorm"):
            self.assertNotIn(word, gained)
        inputs, quiet = graph(model, picture=False)
        self.assertNotIn("[v0]", quiet)
        self.assertIn("concat=n=1:v=0:a=1[voice]", quiet)
        self.assertEqual(inputs, ["-t", "1", "-i", "source"])


@unittest.skipUnless(FFMPEG, "FFmpeg Required")
class MeterTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="loud fixtures ")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def test_a_reference_tone_meters_at_its_known_level_and_the_gain_lands_on_target(self):
        model = sound_model(self.root)
        voice = loudness.measure(model, "voice")
        self.assertAlmostEqual(voice["integrated_lufs"], -20.0, delta=0.15)
        self.assertAlmostEqual(voice["true_peak_dbtp"], -20.0, delta=0.15)
        self.assertAlmostEqual(voice["rms_dbfs"], -23.0, delta=0.15)
        self.assertAlmostEqual(voice["loudness_range_lu"], 0.0, delta=0.3)
        report = loudness.report(model)
        self.assertEqual(report["layer"], "mix")
        self.assertAlmostEqual(report["gain_db"], report["target_lufs"] - report["integrated_lufs"], places=6)
        self.assertFalse(report["breaches_ceiling"])
        after = loudness.measure(model, master_gain=report["linear_gain"])
        self.assertAlmostEqual(after["integrated_lufs"], -14.0, delta=0.15)
        self.assertAlmostEqual(after["true_peak_dbtp"], report["true_peak_after_gain_dbtp"], delta=0.15)
        tight = loudness.report(model, ceiling=-15.0)
        self.assertTrue(tight["breaches_ceiling"])
        self.assertAlmostEqual(tight["largest_gain_within_ceiling_db"], -15.0 - tight["true_peak_dbtp"], places=6)
        self.assertEqual({path.suffix for path in self.root.iterdir()}, {".wav"})

    def test_cue_is_compared_with_speech_in_a_short_window_at_the_cue(self):
        model = sound_model(self.root)
        row, = loudness.cue_levels(model, aim=-18)
        self.assertEqual((row["cue"], row["asset"], row["window_seconds"]), (1, "Tap", [1.0, 1.5]))
        # A 0.05 Sine At Gain 0.5 Is 12 dB Under A 0.1 Sine.
        self.assertAlmostEqual(row["cue_rms_dbfs"], -35.1, delta=0.2)
        self.assertAlmostEqual(row["speech_rms_dbfs"], -23.0, delta=0.2)
        self.assertAlmostEqual(row["cue_minus_speech_db"], -12.0, delta=0.3)
        self.assertEqual(row["reading"], "Under Speech. Audible As Support.")
        self.assertAlmostEqual(row["gain_for_aim"], 0.5 * 10 ** (-6 / 20), delta=0.012)
        whole = loudness.measure(model, "cues")
        # Averaged Over The Whole Edit, The Same Cue Reads 10 dB Lower Than It Does At The Cue.
        self.assertAlmostEqual(whole["rms_dbfs"], row["cue_rms_dbfs"] - 10, delta=0.3)
        self.assertIsNone(loudness.measure(model, "cues", 3.0, 0.5)["rms_dbfs"])
        hot = sound_model(self.root, cue_gain=2)
        self.assertEqual(loudness.cue_levels(hot)[0]["reading"], "Close To Speech Level. Prominent.")
        alone = dict(model, shots=[dict(shot, gain=0) for shot in model["shots"]])
        self.assertEqual(loudness.cue_levels(alone)[0]["reading"], "No Speech In This Window. The Cue Plays In The Clear.")
        self.assertEqual([loudness.reading(v) for v in (4, -30, -20)], [
            "Louder Than Speech. Expect It To Cover Words.", "Likely Masked By Speech.",
            "Well Under Speech. Subtle, And It May Vanish On A Phone Speaker."])
        for window, aim in ((0, None), (3, 40)):
            with self.assertRaises(EditError):
                loudness.cue_levels(model, window, aim)

    def test_windows_and_layers_are_validated(self):
        model = sound_model(self.root)
        for arguments in (("chorus", None, None), ("mix", 1.0, None), ("mix", 4.8, 0.5), ("mix", -1.0, 0.5)):
            with self.assertRaises(EditError):
                sound_graph(model, *arguments)
        window = loudness.report(model, layer="voice", start=2.4, seconds=0.2)
        self.assertEqual(window["window_seconds"], [2.4, 2.6])
        self.assertNotIn("gain_db", window)
        self.assertIsNone(window["integrated_lufs"])
        self.assertAlmostEqual(window["rms_dbfs"], -23.0, delta=0.3)

    def test_check_mix_is_a_stereo_wav_and_existing_files_are_kept(self):
        model = sound_model(self.root)
        target = self.root / "check mix.wav"
        report = mix(model, target)
        self.assertEqual((report["layer"], report["seconds"], report["sample_rate"]), ("mix", 5.0, 48000))
        with wave.open(str(target), "rb") as wav:
            self.assertEqual((wav.getnchannels(), wav.getframerate(), wav.getsampwidth(), wav.getnframes()), (2, 48000, 2, 240000))
            samples = array.array("h")
            samples.frombytes(wav.readframes(48000))
        if sys.byteorder != "little":
            samples.byteswap()
        self.assertAlmostEqual(max(samples) / 32767, 0.1, delta=0.003)
        with self.assertRaisesRegex(EditError, "Already Exists"):
            mix(model, target)
        with self.assertRaisesRegex(EditError, "WAV"):
            mix(model, self.root / "check.mp3")
        part = mix(model, self.root / "cue only.wav", "cues", 0.9, 0.7)
        self.assertEqual(part["seconds"], 0.7)
        with wave.open(str(self.root / "cue only.wav"), "rb") as wav:
            self.assertEqual(wav.getnframes(), round(0.7 * 48000))
            samples = array.array("h")
            samples.frombytes(wav.readframes(wav.getnframes()))
        self.assertEqual(max(samples[:9000]), 0)
        self.assertAlmostEqual(max(samples) / 32767, 0.025, delta=0.002)
        self.assertEqual({path.suffix for path in self.root.iterdir()}, {".wav"})

    def test_finished_file_meter_reads_the_first_audio_stream(self):
        tone(self.root / "finished.wav", 4, 0.2)
        result = loudness.measure_file(self.root / "finished.wav")
        self.assertAlmostEqual(result["integrated_lufs"], -14.0, delta=0.15)
        self.assertAlmostEqual(result["true_peak_dbtp"], -14.0, delta=0.15)
        with self.assertRaises(EditError):
            loudness.measure_file(self.root / "missing.wav")

    def test_sound_only_graph_matches_the_sound_of_the_complete_graph(self):
        model = {"width": 96, "height": 64, "fps": 24, "duration": 1.5, "overlays": [], "captions": [], "audio": [],
                 "assets": {"AV": {"kind": "video", "path": "In Memory", "video": {"index": 0, "width": 80, "height": 80},
                                   "audio": {"index": 1}}},
                 "shots": [{"asset": "AV", "start": 0, "end": 1, "duration": .5, "speed": 2, "gain": 1, "fit": "cover"},
                           {"asset": "AV", "start": 0, "end": 1, "duration": 1, "speed": 1, "gain": .5, "fit": "contain"}]}
        source = "testsrc2=size=80x80:rate=24:duration=1[out0];aevalsrc=0.1*sin(2*PI*220*t)|0.2*sin(2*PI*440*t):s=48000:d=1[out1]"
        base = [binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin",
                "-f", "lavfi", "-i", source, "-f", "lavfi", "-i", source, "-filter_complex_threads", "1"]
        pcm = ["-map", "[sound]", "-c:a", "pcm_s16le", "-f", "s16le", "pipe:1"]
        _, whole = graph(model)
        _, sound = graph(model, picture=False)
        full = subprocess.run(base + ["-filter_complex", whole, "-map", "[picture]", "-f", "null", "-"] + pcm,
                              capture_output=True, check=True).stdout
        only = subprocess.run(base + ["-filter_complex", sound] + pcm, capture_output=True, check=True).stdout
        self.assertEqual(len(full), 48000 * 2 * 2 * 1.5)
        self.assertEqual(full, only)


class RenderGainTests(unittest.TestCase):
    """The Encode Itself Is Mocked. These Checks Cover The Decision And The Report."""

    def setUp(self):
        self.model = {"duration": 5.0}
        self.output = Path("Approved Cut.mp4")
        self.finished = {"integrated_lufs": -14.1, "loudness_range_lu": 3.0, "true_peak_dbtp": -2.0,
                         "rms_dbfs": -17.0, "sample_peak_dbfs": -2.4}

    def run_render(self, measured, **options):
        with patch.object(loudness, "measure", return_value=measured), \
                patch.object(loudness, "process") as encode, \
                patch.object(loudness, "measure_file", return_value=self.finished) as meter:
            try:
                return loudness.render(self.model, self.output, **options), encode, meter
            except EditError as error:
                return error, encode, meter

    def test_gain_is_applied_once_and_the_finished_file_is_reported(self):
        measured = {"integrated_lufs": -20.0, "loudness_range_lu": 3.1, "true_peak_dbtp": -9.0}
        result, encode, meter = self.run_render(measured)
        encode.assert_called_once_with(self.model, self.output, True, master_gain=round(10 ** (6 / 20), 6))
        meter.assert_called_once()
        self.assertEqual((result["applied_gain_db"], result["capped_at_ceiling"]), (6.0, False))
        self.assertEqual(result["measured_mix"], measured)
        self.assertEqual(result["finished_file"], {"integrated_lufs": -14.1, "loudness_range_lu": 3.0, "true_peak_dbtp": -2.0})
        self.assertTrue(result["finished_within_ceiling"])
        self.assertIn("No Compression, Limiting, Or Equalization", result["what_changed"])
        self.assertNotIn("note", result)

    def test_refusal_writes_nothing_and_cap_applies_the_largest_safe_gain(self):
        measured = {"integrated_lufs": -24.0, "loudness_range_lu": 6.0, "true_peak_dbtp": -4.0}
        error, encode, meter = self.run_render(measured)
        self.assertIsInstance(error, EditError)
        self.assertIn("Nothing Was Rendered", str(error))
        self.assertIn("--if-over-ceiling cap", str(error))
        encode.assert_not_called()
        meter.assert_not_called()
        result, encode, _ = self.run_render(measured, over="cap")
        encode.assert_called_once_with(self.model, self.output, True, master_gain=round(10 ** (2.5 / 20), 6))
        self.assertEqual((result["applied_gain_db"], result["capped_at_ceiling"]), (2.5, True))
        self.assertIn("The Gain Was Capped At +2.5 dB", result["note"])

    def test_encoder_overshoot_silence_and_bad_choices_are_reported(self):
        self.finished["true_peak_dbtp"] = -1.1
        result, _, _ = self.run_render({"integrated_lufs": -16.0, "loudness_range_lu": 2.0, "true_peak_dbtp": -4.0})
        self.assertFalse(result["finished_within_ceiling"])
        self.assertIn("The Encoded True Peak Is -1.1 dBTP, Above The Ceiling", result["note"])
        error, encode, _ = self.run_render({"integrated_lufs": None, "loudness_range_lu": None, "true_peak_dbtp": None})
        self.assertIn("Render Without --loudness-target", str(error))
        encode.assert_not_called()
        error, encode, _ = self.run_render({"integrated_lufs": -16.0, "true_peak_dbtp": -4.0}, over="squash")
        self.assertIn("Unsupported Ceiling Choice", str(error))
        encode.assert_not_called()
        self.output = Path("Approved Cut.mov")
        error, encode, meter = self.run_render({"integrated_lufs": -16.0, "true_peak_dbtp": -4.0})
        self.assertIn("Choose An MP4 Output Filename", str(error))
        encode.assert_not_called()
        # An Existing Export Is Simulated, So The Check Itself Never Creates A Video File.
        with patch.object(loudness, "measure") as measured, patch.object(Path, "exists", return_value=True):
            with self.assertRaisesRegex(EditError, "Output Already Exists"):
                loudness.render(self.model, Path("Taken.mp4"))
        measured.assert_not_called()


@unittest.skipUnless(FFMPEG, "FFmpeg Required")
class CommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="loud command ")
        cls.base = Path(cls.temp.name)
        cls.path = example(cls.base / "Cut")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def cli(self, *arguments):
        return subprocess.run([sys.executable, "-B", str(SCRIPTS / "edit_video.py"), *map(str, arguments)],
                              capture_output=True, text=True)

    def test_loudness_command_reports_the_mix_the_plan_and_each_cue(self):
        done = self.cli("loudness", self.path, "--cues")
        self.assertEqual(done.returncode, 0, done.stderr)
        report = json.loads(done.stdout)
        self.assertEqual((report["command"], report["layer"], report["target_lufs"], report["true_peak_ceiling_dbtp"]),
                         ("loudness", "mix", -14.0, -1.5))
        for key in ("integrated_lufs", "loudness_range_lu", "true_peak_dbtp", "gain_db", "linear_gain", "breaches_ceiling"):
            self.assertIn(key, report)
        self.assertAlmostEqual(report["gain_db"], -14.0 - report["integrated_lufs"], places=6)
        self.assertEqual(report["cues"][0]["reading"], "No Speech In This Window. The Cue Plays In The Clear.")
        other = json.loads(self.cli("loudness", self.path, "--loudness-target", "-16", "--true-peak-ceiling", "-30").stdout)
        self.assertEqual((other["target_lufs"], other["breaches_ceiling"]), (-16.0, True))
        window = json.loads(self.cli("loudness", self.path, "--layer", "cues", "--start", "1", "--seconds", "0.5").stdout)
        self.assertEqual((window["layer"], window["window_seconds"]), ("cues", [1.0, 1.5]))
        self.assertNotIn("gain_db", window)
        for bad in (("--start", "1"), ("--seconds", "9", "--start", "0"), ("--loudness-target", "3")):
            failed = self.cli("loudness", self.path, *bad)
            self.assertNotEqual(failed.returncode, 0)
            self.assertTrue(failed.stderr.strip())

    def test_complete_graph_with_the_gain_decodes_into_the_null_sink(self):
        model = prepare(load(self.path), self.path.parent)
        before = loudness.measure(model)
        process(model, master_gain=2.0)
        after = loudness.measure(model, master_gain=2.0)
        self.assertAlmostEqual(after["integrated_lufs"] - before["integrated_lufs"], 6.0, delta=0.2)
        self.assertAlmostEqual(after["true_peak_dbtp"] - before["true_peak_dbtp"], 6.0, delta=0.2)
        self.assertAlmostEqual(after["loudness_range_lu"], before["loudness_range_lu"], delta=0.2)
        self.assertFalse(list(self.base.rglob("*.mp4")))

    def test_mix_command_writes_only_a_wav(self):
        target = self.base / "Cut" / "Check Mix.wav"
        done = self.cli("mix", self.path, target, "--layer", "cues")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["output"], str(target.resolve()))
        with wave.open(str(target), "rb") as wav:
            self.assertEqual(wav.getnframes(), 4 * 48000)
        self.assertNotEqual(self.cli("mix", self.path, target).returncode, 0)

    def test_render_gain_options_never_bypass_owner_approval(self):
        target = self.base / "Cut" / "Never.mp4"
        unapproved = self.cli("render", self.path, target, "--loudness-target", "-14")
        self.assertNotEqual(unapproved.returncode, 0)
        self.assertIn("Owner Review", unapproved.stderr)
        orphan = self.cli("render", self.path, target, "--owner-approved", "--true-peak-ceiling", "-1")
        self.assertNotEqual(orphan.returncode, 0)
        self.assertIn("Add --loudness-target", orphan.stderr)
        # The Example Mix Peaks Near Minus 26 dBTP, So A Minus 30 Ceiling Refuses Before Any Encode.
        refused = self.cli("render", self.path, target, "--owner-approved", "--loudness-target", "-14",
                           "--true-peak-ceiling", "-30")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("Nothing Was Rendered", refused.stderr)
        self.assertFalse(list(self.base.rglob("*.mp4")))


if __name__ == "__main__":
    unittest.main()
