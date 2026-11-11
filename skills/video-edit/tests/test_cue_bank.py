"""The Sound Bank: Original Files Stay Byte-Identical, New Cues Rebuild, And The Index Describes Every File."""

import array
import contextlib
import hashlib
import importlib.util
import io
import json
import math
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

BANK = Path(__file__).resolve().parents[1] / "assets" / "cue-bank"
SOUNDS = BANK / "sounds"
SPEC = importlib.util.spec_from_file_location("cue_bank_build", BANK / "build.py")
build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build)

# SHA-256 Of The 33 Sounds Shipped Before The Bank Grew. They Must Never Change.
ORIGINAL = {
    "button-down": "0c0ab1b0d6a696d21a0fc35e86b6ba65f63c3cc69d40d8812382cd16c3208382",
    "button-up": "39db0de6c2d534898afc58ac8ad693a9f1e8686440c78cb4b2a51835109737d0",
    "small-switch": "3ab8fd874f16144c514c55c804f54f85e4c0f4d6eea4f18191498dc9dc963ba6",
    "glass-point": "49311228e99056671c51cca8c801ee96ea87e44c84ac4b3a378b8f13bdf359bb",
    "menu-open": "bfdd80c5246c86c7303bbf4ecd7e81ab05ba10e6595970c04ad57cc7d768c99c",
    "menu-close": "a7c85e0b19fcd72a64668053aad7b7b648940ae4ce986cbefb6caab566c4aa2b",
    "success-pair": "427a847a5de4afd6ef55c387932903506492b64920689067dc1c46adac3f293d",
    "gentle-alert": "3a0925b20fa4e4a6781f49fe128290d78f447bf8f4f113a6e78f0781a0e88820",
    "enter-confirm": "22b2d82e05975a1efb97c5750f24ce2a8c6791c2ac44597fed97dcf4327cdbee",
    "counter-step": "b11962f81e09ea0ed72007e66efe72caac110ca9845b6ac9c5efcc203933a58f",
    "page-flick": "a0a21ff596d3a6f9c393e6ce951ae2721fd5d25b82bb374ab9a77c6674406a0e",
    "soft-swipe": "4a008ecf9483185e4dab8c63a0e0cd058e331d8eb81dba71dd7ac05533c2ed32",
    "quick-pass": "37b38f1e4c84c1623f91f76f87e229dadeb2f6a82fcfc8da1a8e9b0642465425",
    "long-sweep": "47dbc50ca13e20ec98f37464b4cabc141db8fdb6fb6c16da7f8cd05c58a4665a",
    "low-drop": "164805093a80b092b70b86ec3179279060822d23d76007a0a8df2d0cbdd1625a",
    "transition-hit": "1edfe04780d52f2d5344bc2b9198b4bb9acf88648180034a5adfae1ae2aafd90",
    "marker-knock": "e08df8b8342e7b5eeaef0c22daf71fd06a6b57a2792756ae88c167deca532306",
    "paper-touch": "ed3b93f0b7519db55a4d097d0d93179015f224c14635d4a984d31b5c935c899e",
    "countdown-tick": "31c1425d30fca6b88c42923ed24f454c5de57cc04cad5e9d68b80127e9d8c5b5",
    "countdown-finish": "389a5f320104ffc1b41ebb74d652ff4d7b0acafdf1610ac781e985df02399354",
    "soft-key": "76c3ed38fbd6d14501dab4e09488c826f7d1eb6a1e0b17e25c0a40ebd6801c5b",
    "three-keys": "a6536ca19ebefbb6e4a9923b2b936113eaae88ddaf2ec7946232b7fc9970e058",
    "receipt-feed": "e95ecf7df2041ec64a54bad92126b2f82e3b6888b1c02346fe4d28e7f33815b3",
    "shutter-snap": "c5f79ed3cefd703b0012c00431548132e2ef6f02598796bd2769b412f900f76b",
    "low-pulse": "0cc5f3d44d475203768398b84ed7e8904346fde962bb1d4dba523975518f7a26",
    "dial-turn": "d81bc8a1bee9120bfc22cc86154adacde06bdbe72e06374e1fe92f2ed3a3e56d",
    "spring-reveal": "921c659c9b9d83973ce9a780a75a18a4288f6bf23bbb04697ad9c8c72dbb7cb6",
    "rubber-stop": "53b4e1b3bb47da109481b23e3f4c1b1dd35e6e2d0f79c1eb867e4a49233a3a10",
    "notification-bloom": "72adf80b4c1e1ce224593c7169ab3131d9479c9275ec87335ff3066df5b62474",
    "focus-shift": "0681909e1888cd1f285860cd15cbb6e8536f3c5690df1a2fbb16b97ac845f87d",
    "desk-air": "6fc6571995658d79042e7c8139474e994b3c927b7743b7e8ffd8c24f86db6ad9",
    "machine-idle": "d0c518a174992864556ef897b62a728da45477c3009920d3ea88ed07838f651d",
    "soft-room": "ce7fbea9fa1ef831464ecb72219c1e670c144a712a94ba59f05c9f61719d651f",
}
PALETTE = {"whoosh": 4, "riser": 1, "stinger": 1, "impact": 1, "roll": 1, "ticks": 1, "keys": 1, "chime": 2,
           "shutter": 1, "glitch": 1, "buzz": 1, "notify": 1, "pop": 1, "bed": 9}


def samples(path):
    with wave.open(str(path), "rb") as wav:
        layout = (wav.getnchannels(), wav.getsampwidth(), wav.getframerate())
        pcm = array.array("h")
        pcm.frombytes(wav.readframes(wav.getnframes()))
    if sys.byteorder != "little":
        pcm.byteswap()
    return layout, pcm


class CueBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((SOUNDS / "index.json").read_text(encoding="utf-8"))
        cls.by_name = {record["file"][:-4]: record for record in cls.index}

    def test_original_sounds_are_byte_identical(self):
        self.assertEqual([record["file"][:-4] for record in self.index[:33]], list(ORIGINAL))
        self.assertEqual([spec[0] for spec in build.PROGRAMS], list(ORIGINAL))
        for name, digest in ORIGINAL.items():
            with self.subTest(sound=name):
                self.assertEqual(hashlib.sha256((SOUNDS / f"{name}.wav").read_bytes()).hexdigest(), digest)
                self.assertEqual(self.by_name[name]["sha256"], digest)

    def test_index_describes_every_file_and_nothing_else(self):
        self.assertEqual(len(self.index), 56)
        self.assertEqual(len(self.index) - len(ORIGINAL), 23)
        self.assertEqual(sorted(path.name for path in SOUNDS.iterdir()),
                         sorted([record["file"] for record in self.index] + ["index.json"]))
        self.assertEqual([record["file"][:-4] for record in self.index], [name for name, _, _ in build.catalog()])
        for record in self.index:
            with self.subTest(sound=record["file"]):
                path = SOUNDS / record["file"]
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["sha256"])
                layout, pcm = samples(path)
                self.assertEqual(layout, (1, 2, 24000))
                self.assertAlmostEqual(len(pcm) / 24000, record["seconds"], delta=1 / 24000)
                peak = max(abs(value) for value in pcm)
                rms = math.sqrt(sum(value * value for value in pcm) / len(pcm))
                self.assertAlmostEqual(record["peak_dbfs"], 20 * math.log10(peak / 32768), delta=0.051)
                self.assertAlmostEqual(record["rms_dbfs"], 20 * math.log10(rms / 32768), delta=0.051)
                self.assertLessEqual(record["peak_dbfs"], -3.0)
                self.assertGreaterEqual(len(record["tags"]), 3)
                self.assertTrue(all(tag == tag.lower() and tag.isalnum() for tag in record["tags"]))
                self.assertEqual(len(set(record["tags"])), len(record["tags"]))
                use = record["use"]
                self.assertTrue(use.endswith(".") and "\n" not in use and len(use) <= 110, use)
                for word in use.replace("-", " ").split():
                    self.assertFalse(word[0].islower(), f"{word} In {use}")
                self.assertEqual(set(record) - {"overlap_seconds"},
                                 {"file", "family", "seconds", "sha256", "tags", "use", "peak_dbfs", "rms_dbfs"})

    def test_palette_covers_what_an_editor_reaches_for(self):
        families = [record["family"] for record in self.index[33:]] + ["bed"] * 3
        for family, count in PALETTE.items():
            with self.subTest(family=family):
                self.assertEqual(families.count(family), count)
        tags = {tag for record in self.index for tag in record["tags"]}
        for tag in ("whoosh", "riser", "stinger", "impact", "roll", "clock", "typing", "register", "coin", "shutter",
                    "glitch", "error", "notification", "pop", "room", "hum", "night", "water", "static"):
            self.assertIn(tag, tags)
        weights = {name: self.by_name[name]["seconds"] for name in ("whoosh-light", "whoosh-medium", "whoosh-heavy")}
        self.assertLess(weights["whoosh-light"], weights["whoosh-medium"])
        self.assertLess(weights["whoosh-medium"], weights["whoosh-heavy"])
        beds = [record for record in self.index[33:] if record["family"] == "bed"]
        self.assertEqual(len(beds), 6)
        for bed in beds:
            self.assertGreaterEqual(bed["seconds"], 6)
            self.assertEqual(bed["overlap_seconds"], 0.25)
            self.assertAlmostEqual(bed["rms_dbfs"], -27.0, delta=0.6)
            _, pcm = samples(SOUNDS / bed["file"])
            self.assertLess(max(abs(pcm[0]), abs(pcm[-1])), 40)
        self.assertNotIn("overlap_seconds", self.by_name["soft-room"])

    def test_generator_rebuilds_the_shipped_bank(self):
        with tempfile.TemporaryDirectory() as folder:
            fresh = Path(folder) / "fresh cues"
            log = io.StringIO()
            with contextlib.redirect_stdout(log):
                build.build(fresh)
            self.assertEqual(log.getvalue().strip(), "Built 56 Original Cue Files.")
            rebuilt = json.loads((fresh / "index.json").read_text(encoding="utf-8"))
            self.assertEqual([record["file"] for record in rebuilt], [record["file"] for record in self.index])
            for old, new in zip(self.index, rebuilt):
                with self.subTest(sound=old["file"]):
                    for key in ("family", "seconds", "tags", "use"):
                        self.assertEqual(new[key], old[key])
                    self.assertEqual(new.get("overlap_seconds"), old.get("overlap_seconds"))
                    (_, shipped), (_, made) = samples(SOUNDS / old["file"]), samples(fresh / new["file"])
                    self.assertEqual(len(shipped), len(made))
                    # The Shipped Files Are Fixed By Their Digests. A Rebuild May Differ By One Step
                    # Where A Platform's Math Library Rounds The Last Bit Differently.
                    self.assertLessEqual(max(abs(a - b) for a, b in zip(shipped, made)), 1)
            self.assertEqual(build.render("pop-bubble"), build.render("pop-bubble"))
            with self.assertRaises(KeyError):
                build.render("missing-cue")

    def test_command_builds_into_a_new_folder_only(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "rebuilt"
            done = subprocess.run([sys.executable, "-B", str(BANK / "build.py"), str(target)], capture_output=True, text=True)
            self.assertEqual((done.returncode, done.stdout.strip()), (0, "Built 56 Original Cue Files."))
            self.assertEqual(len(list(target.glob("*.wav"))), 56)
            again = subprocess.run([sys.executable, "-B", str(BANK / "build.py"), str(target)], capture_output=True, text=True)
            self.assertEqual(again.returncode, 2)
            self.assertIn("Choose A New Or Empty Output Folder", again.stderr)


if __name__ == "__main__":
    unittest.main()
