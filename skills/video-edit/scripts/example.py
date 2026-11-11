"""Handmade Editable Sample With Generated Stills And Stereo Sound."""

import json
import math
import struct
import wave
import zlib
from pathlib import Path

from timeline import write_new


def image(path, palette, variant):
    width, height = 160, 100
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            ring = abs(math.hypot(x - 80 + variant * 12, y - 50) - 27) < 5
            stripe = (x + 2 * y + variant * 24) % 57 < 6
            raw.extend(palette[2 if ring else int(stripe)])

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    with path.open("xb") as output:
        output.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def example(folder):
    folder.mkdir(parents=True, exist_ok=False)
    image(folder / "First Frame.png", [(23, 43, 62), (39, 85, 102), (122, 229, 196)], 0)
    image(folder / "Second Frame.png", [(49, 34, 75), (88, 52, 101), (245, 182, 121)], 1)
    rate = 16000
    with (folder / "Stereo Cue.wav").open("xb") as sound:
        with wave.open(sound, "wb") as wav:
            wav.setparams((2, 2, rate, 0, "NONE", ""))
            samples = bytearray()
            for i in range(rate * 4):
                t = i / rate
                envelope = min(1, t * 40, (4-t) * 40) if .5 < t < 3.5 else 0
                phase = 2 * math.pi * t
                samples.extend(struct.pack("<hh", int(2400*envelope*math.sin(220*phase)),
                                          int(2000*envelope*math.sin(330*phase))))
            wav.writeframes(samples)
    doc = {
        "version": 1, "title": "Colour And Rhythm",
        "canvas": {"width": 360, "height": 640, "fps": 24, "fit": "cover"},
        "assets": {"First": {"kind": "image", "path": "First Frame.png"},
                   "Second": {"kind": "image", "path": "Second Frame.png"},
                   "Sound": {"kind": "audio", "path": "Stereo Cue.wav"}},
        "shots": [{"asset": "First", "in": 0, "out": 2}, {"asset": "Second", "in": 0, "out": 2,
                  "zoom": 1.2, "pan_x": .15, "brightness": 1.05, "contrast": 1.04, "saturation": 1.12}],
        "overlays": [{"asset": "Second", "at": 1, "end": 1.75, "in": 0, "x": 18, "y": 54, "width": 120}],
        "captions": [{"at": .25, "end": 1.5, "text": "Follow The Circle", "position": "bottom"},
                     {"at": 2.25, "end": 3.5, "text": "Now Change The Rhythm", "position": "top"}],
        "caption_style": {"font": "Arial", "color": "#FFFFFF", "outline": "#101010", "margin": 7},
        "audio": [{"asset": "Sound", "at": 0, "end": 4, "in": 0, "gain": .7}],
    }
    path = folder / "timeline.json"
    write_new(path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    return path
