"""Synthesize An Original Collection Of Editorial Sounds With Python's Standard Library."""

from array import array
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import wave


# Frequency, pitch travel in octaves, attack, release contour and noise define each gesture.
PROGRAMS = [
    ("button-down", "tap", 0.11, 225, -1.5),
    ("button-up", "tap", 0.12, 310, 1),
    ("small-switch", "tap", 0.13, 640, -2),
    ("glass-point", "bell", 0.48, 1240, 0.03),
    ("menu-open", "rise", 0.33, 330, 1.35),
    ("menu-close", "fall", 0.3, 720, -1.55),
    ("success-pair", "pair", 0.57, 540, 0.6),
    ("gentle-alert", "pair", 0.48, 310, -0.30),
    ("enter-confirm", "bell", 0.52, 780, -0.05),
    ("counter-step", "tap", 0.12, 470, -0.9),
    ("page-flick", "brush", 0.24, 280, 2.2),
    ("soft-swipe", "brush", 0.42, 400, 1.8),
    ("quick-pass", "brush", 0.18, 940, -1.8),
    ("long-sweep", "brush", 0.85, 210, 2.4),
    ("low-drop", "bump", 0.62, 135, -2.5),
    ("transition-hit", "bump", 0.28, 230, -1.8),
    ("marker-knock", "tap", 0.2, 250, -0.5),
    ("paper-touch", "grain", 0.30, 940, 0.45),
    ("countdown-tick", "tap", 0.16, 1200, -0.8),
    ("countdown-finish", "bell", 0.75, 660, 0.12),
    ("soft-key", "tap", 0.085, 540, -1.1),
    ("three-keys", "steps", 0.49, 610, -0.6),
    ("receipt-feed", "steps", 0.78, 260, 0.28),
    ("shutter-snap", "grain", 0.14, 1450, -1.6),
    ("low-pulse", "bump", 0.55, 80, -0.65),
    ("dial-turn", "steps", 0.60, 760, 0.35),
    ("spring-reveal", "rise", 0.47, 310, 1.65),
    ("rubber-stop", "fall", 0.39, 550, -2.2),
    ("notification-bloom", "bell", 0.88, 965, 0.03),
    ("focus-shift", "brush", 0.61, 750, -1.25),
    ("desk-air", "bed", 4.0, 130, 0.1),
    ("machine-idle", "bed", 4.0, 64, 0),
    ("soft-room", "bed", 5.0, 180, -0.04),
]
RATE = 24000


def synth(index, label, family, duration, hz, travel):
    rng = random.Random(910701 + index)
    count = round(RATE * duration)
    pcm = array("h")
    phase = 0
    memory = 0
    prev = 0
    for i in range(count):
        t = i / RATE
        u = i / max(1, count - 1)
        f = hz * 2 ** (travel * u)
        if family == "pair" and u > 0.46:
            f = hz * 2**travel
        phase += 2 * math.pi * f / RATE
        noise = rng.uniform(-1, 1)
        memory += 0.10 * (noise - memory)
        sine = math.sin(phase)
        if family == "brush":
            signal = (noise - prev) * 0.18 + memory * 1.5
            signal *= math.sin(math.pi * u) ** 1.7 * (0.6 + 0.4 * math.sin(phase) ** 2)
        elif family == "bed":
            signal = (0.55 * memory + 0.11 * sine + 0.035 * math.sin(phase * 2)) * (
                0.65 + 0.15 * math.cos(math.tau * u)
            )
        elif family == "bell":
            signal = (
                sine + 0.23 * math.sin(phase * 2.67) + 0.11 * math.sin(phase * 3.94)
            ) * math.exp(-5 * u)
        elif family in ("pair", "steps"):
            beat = (u * (2 if family == "pair" else 4)) % 1
            signal = (sine + 0.3 * memory) * math.exp(-7 * beat) * min(1, beat * 45)
        elif family in ("grain", "tap"):
            weight = 0.80 if family == "grain" else 0.25
            signal = (weight * noise + (1 - weight) * sine) * math.exp(-6.5 * u)
        elif family == "bump":
            signal = (0.84 * sine + 0.16 * memory) * math.exp(-5.2 * u)
        else:
            signal = (
                sine * 0.64 + math.sin(2 * phase) * 0.17 + 0.09 * memory
            ) * math.sin(math.pi * u) ** 0.8
        edge = min(1, i / 90, (count - 1 - i) / 120)
        pcm.append(round(23100 * math.tanh(signal) * edge))
        prev = noise
    if sys.byteorder != "little":
        pcm.byteswap()
    return pcm.tobytes()


def build(directory):
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for idx, spec in enumerate(PROGRAMS):
        name, family, duration, _, _ = spec
        raw = synth(idx, *spec)
        path = directory / (name + ".wav")
        with wave.open(str(path), "wb") as wav:
            wav.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
            wav.writeframes(raw)
        records.append(
            {
                "file": path.name,
                "family": family,
                "seconds": duration,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    (directory / "index.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Built {len(records)} Original Cue Files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="New Or Empty Output Folder")
    target = parser.parse_args().directory
    if target.exists() and any(target.iterdir()):
        parser.error("Choose A New Or Empty Output Folder.")
    build(target)
