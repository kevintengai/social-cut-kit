"""Opt-In Sound Fades On Shots And Cues. Without The Fields The Sound Stays As Recorded."""

import array
import math
import shutil
import struct
import sys
import tempfile
import unittest
import wave
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from example import example
from handoff import otio
from media import fade_filters, graph, mix
from timeline import EditError, load, prepare

FFMPEG = shutil.which("ffmpeg") and shutil.which("ffprobe")


@unittest.skipUnless(FFMPEG, "FFmpeg Required")
class FadeFieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="fade fixtures ")
        cls.path = example(Path(cls.temp.name) / "Cut")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def model(self, **cue):
        doc = load(self.path)
        doc["audio"][0].update(cue)
        return prepare(doc, self.path.parent)

    def test_rows_without_fades_are_unchanged_and_carry_no_fade_filters(self):
        model = self.model()
        self.assertEqual(set(model["audio"][0]), {"asset", "at", "end", "start", "gain"})
        self.assertNotIn("afade", graph(model)[1])
        self.assertEqual(fade_filters(model["audio"][0], 4), "")

    def test_cue_and_shot_fades_enter_the_model_the_graph_and_the_handoff(self):
        model = self.model(fade_in=0.5, fade_out=1.25)
        self.assertEqual((model["audio"][0]["fade_in"], model["audio"][0]["fade_out"]), (0.5, 1.25))
        _, expression = graph(model)
        self.assertIn("volume=0.7,afade=t=in:st=0:d=0.5,afade=t=out:st=2.75:d=1.25,adelay=0S:all=1[m0]", expression)
        self.assertEqual(expression.count("afade="), 2)
        cue = otio(model)["tracks"]["children"][-1]["children"][0]
        self.assertEqual(cue["metadata"]["social_cut_kit"]["fade_out"], 1.25)
        only_out = self.model(fade_out=0.01)
        self.assertEqual(fade_filters(only_out["audio"][0], 4), ",afade=t=out:st=3.99:d=0.01")
        shot = {"asset": "AV", "start": 0, "end": 2, "duration": 2, "speed": 1, "gain": 1, "fit": "cover",
                "fade_in": 0.005, "fade_out": 0.005}
        hand = {"width": 96, "height": 64, "fps": 24, "duration": 2, "overlays": [], "captions": [], "audio": [],
                "assets": {"AV": {"kind": "video", "path": "source", "video": {"index": 0, "width": 96, "height": 64},
                                  "audio": {"index": 1}}}, "shots": [shot]}
        self.assertIn("apad,atrim=duration=2,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.005,"
                      "afade=t=out:st=1.995:d=0.005[a0]", graph(hand)[1])

    def test_fades_must_be_numbers_that_fit_inside_the_row(self):
        for cue in ({"fade_in": 3, "fade_out": 1.5}, {"fade_in": -0.1}, {"fade_out": "short"}, {"fade_in": 61}):
            with self.subTest(cue=cue), self.assertRaises(EditError):
                self.model(**cue)
        doc = load(self.path)
        doc["shots"][0].update(fade_in=1.5, fade_out=1.0)
        with self.assertRaisesRegex(EditError, "Shot Fades Must Fit Inside Its 2 Second Length"):
            prepare(doc, self.path.parent)
        doc["shots"][0].update(fade_in=1.0, fade_out=1.0)
        self.assertEqual(prepare(doc, self.path.parent)["shots"][0]["fade_out"], 1.0)


@unittest.skipUnless(FFMPEG, "FFmpeg Required")
class FadeSoundTests(unittest.TestCase):
    def test_fades_ramp_the_decoded_sound_and_the_default_is_a_hard_join(self):
        with tempfile.TemporaryDirectory(prefix="fade sound ") as folder:
            root = Path(folder)
            frames = b"".join(struct.pack("<hh", value, value) for value in
                              (round(32767 * 0.2 * math.sin(2 * math.pi * 500 * i / 48000)) for i in range(48000 * 4)))
            with wave.open(str(root / "talk.wav"), "wb") as wav:
                wav.setparams((2, 2, 48000, 0, "NONE", ""))
                wav.writeframes(frames)
            stream = {"index": 0, "channels": 2, "sample_rate": "48000"}

            def model(**fades):
                return {"title": "Fades", "width": 1080, "height": 1920, "fps": 30, "duration": 4.0,
                        "overlays": [], "captions": [], "warnings": [], "audio": [],
                        "assets": {"Talk": {"kind": "video", "path": str(root / "talk.wav"), "duration": 4.0,
                                            "video": {"index": 0, "width": 1080, "height": 1920}, "audio": stream}},
                        "shots": [dict(asset="Talk", start=0, end=2, at=0, duration=2, speed=1, gain=1, fit="cover", **fades),
                                  dict(asset="Talk", start=2, end=4, at=2, duration=2, speed=1, gain=1, fit="cover")]}

            def peaks(name, scene):
                mix(scene, root / name, "voice")
                with wave.open(str(root / name), "rb") as wav:
                    pcm = array.array("h")
                    pcm.frombytes(wav.readframes(wav.getnframes()))
                if sys.byteorder != "little":
                    pcm.byteswap()
                # Peak Of A 10 Millisecond Window Starting At Each Listed Time.
                return [max(abs(v) for v in pcm[round(t * 48000) * 2: round((t + 0.01) * 48000) * 2]) / 32767
                        for t in (0.0, 0.25, 0.75, 1.5, 1.99, 2.0, 3.0)]

            plain = peaks("plain.wav", model())
            for level in plain:
                self.assertAlmostEqual(level, 0.2, delta=0.004)
            faded = peaks("faded.wav", model(fade_in=0.5, fade_out=1.0))
            expected = [0.004, 0.102, 0.2, 0.1, 0.002, 0.2, 0.2]
            for level, target in zip(faded, expected):
                self.assertAlmostEqual(level, target, delta=0.006)
            self.assertEqual({path.suffix for path in root.iterdir()}, {".wav"})


if __name__ == "__main__":
    unittest.main()
