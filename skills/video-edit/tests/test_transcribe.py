"""Transcription With A Stand-In Recognizer: The Normal Path And The FFmpeg Decode Fallback."""

import importlib.util
import json
import math
import os
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
NUMPY = importlib.util.find_spec("numpy") is not None
# A Stand-In For The Optional Package. It Reports Whether It Was Given A Path Or Decoded Samples.
STAND_IN = '''
import os


class Word:
    def __init__(self, start, end, word):
        self.start, self.end, self.word = start, end, word


class Segment:
    def __init__(self, words):
        self.words = words


class WhisperModel:
    def __init__(self, name, device="cpu", compute_type="int8"):
        self.name = name

    def transcribe(self, audio, language=None, word_timestamps=False):
        if isinstance(audio, str) and os.environ.get("STAND_IN_READER_FAILS"):
            raise TypeError("open() got an unexpected keyword argument")
        given = "path" if isinstance(audio, str) else "samples:%d:%s" % (len(audio), audio.dtype)
        return [Segment([Word(0.5, 0.9, " Hello"), Word(1.0, 1.4, " " + given), Word(2.0, 2.0, " dropped")])], None
'''


class TranscribeTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="transcribe fixtures ")
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        (self.root / "package").mkdir()
        (self.root / "package" / "faster_whisper.py").write_text(STAND_IN, encoding="utf-8")
        frames = b"".join(struct.pack("<h", round(9000 * math.sin(2 * math.pi * 300 * i / 8000))) for i in range(16000))
        with wave.open(str(self.root / "voice.wav"), "wb") as wav:
            wav.setparams((1, 2, 8000, 0, "NONE", ""))
            wav.writeframes(frames)

    def transcribe(self, output, **extra):
        env = dict(os.environ, PYTHONPATH=str(self.root / "package"), **extra)
        done = subprocess.run([sys.executable, "-B", str(SCRIPT), "transcribe", str(self.root / "voice.wav"),
                               str(self.root / output), "--backend", "faster-whisper", "--model", "stand-in"],
                              capture_output=True, text=True, env=env)
        return done

    def test_recognizer_reads_the_file_when_it_can(self):
        done = self.transcribe("words.json")
        self.assertEqual(done.returncode, 0, done.stderr)
        words = json.loads((self.root / "words.json").read_text(encoding="utf-8"))["words"]
        self.assertEqual(words, [{"start": 0.5, "end": 0.9, "text": "Hello"}, {"start": 1.0, "end": 1.4, "text": "path"}])
        again = self.transcribe("words.json")
        self.assertNotEqual(again.returncode, 0)

    @unittest.skipUnless(FFMPEG and NUMPY, "The Decode Fallback Needs FFmpeg And NumPy.")
    def test_ffmpeg_decodes_samples_when_the_recognizer_cannot_open_the_file(self):
        done = self.transcribe("fallback.json", STAND_IN_READER_FAILS="1")
        self.assertEqual(done.returncode, 0, done.stderr)
        words = json.loads((self.root / "fallback.json").read_text(encoding="utf-8"))["words"]
        # Two Seconds Of Sound Arrive As 32000 Mono Samples At 16 kHz.
        self.assertEqual([word["text"] for word in words], ["Hello", "samples:32000:float32"])


if __name__ == "__main__":
    unittest.main()
