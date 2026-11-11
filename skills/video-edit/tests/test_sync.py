"""Recorder Sync: The Offset At The Start Of A Take And A Second Reading Later In The Take For Drift."""

import json
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "speech.py"
FFMPEG = shutil.which("ffmpeg")
RATE = 16000


def bursts(seconds, seed=41):
    """Irregular Short Noise Bursts, Like Consonants In Speech."""
    rng = random.Random(seed)
    samples = [0] * round(seconds * RATE)
    at = 0.2
    while at < seconds - 0.2:
        for i in range(round(0.03 * RATE)):
            samples[round(at * RATE) + i] = round(rng.uniform(-9000, 9000))
        at += rng.uniform(0.18, 0.9)
    return samples


def save(path, samples):
    with wave.open(str(path), "wb") as wav:
        wav.setparams((1, 2, RATE, 0, "NONE", ""))
        wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))


@unittest.skipUnless(FFMPEG, "FFmpeg Required")
class SyncTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="sync fixtures ")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        camera = bursts(24)
        # The Recorder Starts A Quarter Second Late And Has Slipped A Further Tenth By The Halfway Point.
        recorder = [0] * round(0.25 * RATE) + camera[: 10 * RATE] + [0] * round(0.10 * RATE) + camera[10 * RATE:]
        save(self.root / "camera.wav", camera)
        save(self.root / "recorder.wav", recorder)

    def sync(self, *options):
        done = subprocess.run([sys.executable, "-B", str(SCRIPT), "sync", str(self.root / "camera.wav"),
                               str(self.root / "recorder.wav"), *options], capture_output=True, text=True)
        return done, (json.loads(done.stdout) if done.returncode == 0 else None)

    def test_offset_at_the_start_and_later_in_the_take_reveals_drift(self):
        done, early = self.sync("--seconds", "8", "--lag", "1")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(list(early), ["secondary_event_later_by_seconds", "correlation", "next_distinct_correlation", "resolution_seconds"])
        self.assertAlmostEqual(early["secondary_event_later_by_seconds"], 0.25, delta=0.011)
        self.assertGreater(early["correlation"], 0.9)
        done, late = self.sync("--seconds", "8", "--lag", "1", "--start", "12")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(late["sample_start_seconds"], 12.0)
        self.assertAlmostEqual(late["secondary_event_later_by_seconds"], 0.35, delta=0.011)
        drift = late["secondary_event_later_by_seconds"] - early["secondary_event_later_by_seconds"]
        self.assertAlmostEqual(drift, 0.10, delta=0.021)

    def test_start_must_be_a_reasonable_time(self):
        done, _ = self.sync("--start", "-3")
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("Use A Start From 0 To 86400 Seconds", done.stderr)


if __name__ == "__main__":
    unittest.main()
