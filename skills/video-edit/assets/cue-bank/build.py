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
import zlib


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


# The Second Set Is Layered From Filtered Noise, Tuned Partials, And Scheduled Events.
# Each Design Seeds Its Own Generator From Its Name, So Adding A Design Never Changes Another.
TAU = math.tau


def source(name):
    return random.Random(zlib.crc32(name.encode("ascii")) + 20261)


def hiss(rng, count):
    return [rng.uniform(-1, 1) for _ in range(count)]


def biquad(kind, hz, q):
    w = TAU * min(max(hz, 5.0), RATE * 0.45) / RATE
    cosine, alpha = math.cos(w), math.sin(w) / (2 * q)
    if kind == "band":
        b0, b1, b2 = alpha, 0.0, -alpha
    elif kind == "low":
        b0 = b2 = (1 - cosine) / 2
        b1 = 1 - cosine
    else:
        b0 = b2 = (1 + cosine) / 2
        b1 = -(1 + cosine)
    a0 = 1 + alpha
    return b0 / a0, b1 / a0, b2 / a0, -2 * cosine / a0, (1 - alpha) / a0


def shape(samples, kind, hz, q=0.707, step=24):
    """Filter With A Fixed Frequency, Or With One That Follows A Function Of Position From 0 To 1."""
    moving = callable(hz)
    b0, b1, b2, a1, a2 = biquad(kind, hz(0.0) if moving else hz, q)
    x1 = x2 = y1 = y2 = 0.0
    count = len(samples)
    out = []
    for i, x in enumerate(samples):
        if moving and i % step == 0:
            b0, b1, b2, a1, a2 = biquad(kind, hz(i / count), q)
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, x, y1, y
        out.append(y)
    return out


def slow(rng, count, hz):
    """A Smooth Random Curve Between 0 And 1 For Drift, Flutter, And Swell.

    Random Levels Are Placed Half A Cycle Apart And Joined With Cosine Easing, So The Curve
    Moves At About The Named Rate Whether That Is A Fraction Of A Hertz Or A Dozen.
    """
    spacing = max(2, round(RATE / (2 * hz)))
    knots = [rng.random() for _ in range(count // spacing + 2)]
    curve = []
    for i in range(count):
        index, offset = divmod(i, spacing)
        ease = 0.5 - 0.5 * math.cos(math.pi * offset / spacing)
        curve.append(knots[index] + (knots[index + 1] - knots[index]) * ease)
    return curve


def place(buffer, at, samples, gain=1.0):
    start = round(at * RATE)
    for i, value in enumerate(samples):
        if 0 <= start + i < len(buffer):
            buffer[start + i] += gain * value


def burst(rng, seconds, kind, hz, q, tau):
    """A Short Filtered Noise Hit With An Exponential Tail."""
    count = round(seconds * RATE)
    grains = shape(hiss(rng, count), kind, hz, q)
    return [grains[i] * math.exp(-i / (tau * RATE)) for i in range(count)]


def ring(seconds, partials, attack=0.0008):
    """Decaying Sine Partials Given As Frequency, Level, And Decay Time."""
    count = round(seconds * RATE)
    out = [0.0] * count
    for hz, level, tau in partials:
        if hz > RATE * 0.44:
            continue
        step = TAU * hz / RATE
        for i in range(count):
            out[i] += level * math.sin(step * i) * math.exp(-i / (tau * RATE))
    rise = max(1, round(attack * RATE))
    return [out[i] * min(1.0, i / rise) for i in range(count)]


def whoosh(rng, seconds, start_hz, top_hz, end_hz, q, peak_at, weight=0.0):
    count = round(seconds * RATE)

    def centre(u):
        if u < peak_at:
            return start_hz * (top_hz / start_hz) ** (u / peak_at)
        return top_hz * (end_hz / top_hz) ** ((u - peak_at) / (1 - peak_at))

    air = shape(hiss(rng, count), "band", centre, q)
    body = shape(hiss(rng, count), "band", lambda u: centre(u) * 0.5, q * 0.8)
    rumble = shape(hiss(rng, count), "low", 170, 0.7) if weight else None
    skew = math.log(0.5) / math.log(peak_at)
    out, phase = [], 0.0
    for i in range(count):
        u = i / (count - 1)
        swell = max(0.0, math.sin(math.pi * u ** skew)) ** 2.2
        value = (air[i] + 0.55 * body[i]) * swell
        if weight:
            phase += TAU * (64 - 26 * u) / RATE
            value += weight * swell ** 1.4 * (2.2 * rumble[i] + 0.5 * math.sin(phase))
        out.append(value)
    return out


def pull(rng, seconds):
    """A Reverse Whoosh That Swells And Stops Dead For A Cut."""
    count = round(seconds * RATE)
    air = shape(hiss(rng, count), "band", lambda u: 320 * 17 ** u, 1.1)
    edge = shape(hiss(rng, count), "high", 2600, 0.7)
    return [(air[i] + 0.25 * edge[i] * (i / count) ** 2) * (i / count) ** 3.2 for i in range(count)]


def riser(rng, seconds):
    count = round(seconds * RATE)
    air = shape(hiss(rng, count), "band", lambda u: 240 * 27 ** u, 1.4)
    out, phases, wobble = [], [0.0, 0.0, 0.0], 0.0
    for i in range(count):
        u = i / (count - 1)
        hz = 98 * 2 ** (3.2 * u)
        tone = 0.0
        for voice, (detune, level) in enumerate(((1.0, 1.0), (1.007, 0.8), (0.5, 0.6))):
            phases[voice] += TAU * hz * detune / RATE
            for k in range(1, 7):
                tone += level * math.sin(k * phases[voice]) / k
        wobble += TAU * (5 + 13 * u) / RATE
        pulse = 1 - 0.35 * (0.5 + 0.5 * math.sin(wobble))
        out.append(1.6 * air[i] * u ** 1.8 + 0.3 * tone * u ** 1.4 * pulse)
    return out


def impact(rng, seconds):
    count = round(seconds * RATE)
    thump = shape(hiss(rng, count), "low", 200, 0.7)
    body = shape(hiss(rng, count), "band", 420, 1.2)
    snap = shape(hiss(rng, count), "band", 2600, 0.9)
    tail = shape(hiss(rng, count), "low", 90, 0.7)
    # A Knock In The Low Mids Carries The Hit On Speakers That Cannot Reproduce The Sub.
    knock = ring(seconds, [(118, 0.9, 0.11), (236, 0.8, 0.075), (354, 0.55, 0.05), (590, 0.3, 0.03)])
    out, phase = [], 0.0
    for i in range(count):
        t = i / RATE
        phase += TAU * (34 + 46 * math.exp(-t / 0.06)) / RATE
        sub = 0.7 * math.tanh(3.0 * math.sin(phase) * math.exp(-t / 0.42))
        value = (sub + knock[i] + 5.0 * thump[i] * math.exp(-t / 0.09) + 6.5 * body[i] * math.exp(-t / 0.07)
                 + 1.6 * snap[i] * math.exp(-t / 0.008) + 1.2 * tail[i] * math.exp(-t / 0.5))
        out.append(value * min(1.0, t / 0.0015))
    return out


def stinger(rng, seconds):
    count = round(seconds * RATE)
    out = [0.0] * count
    # An Open Fifth Stacked Over Three Octaves Reads As An Accent Without Implying Major Or Minor.
    for hz, level in ((146.83, 0.55), (293.66, 1.0), (440.0, 0.85), (587.33, 0.9), (880.0, 0.6), (1174.66, 0.5),
                      (2349.3, 0.16), (3520.0, 0.08)):
        for detune in (0.997, 1.003):
            step = TAU * hz * detune / RATE
            for k in range(1, 9):
                if hz * k > RATE * 0.42:
                    break
                weight, fade = level / k ** 0.9, 2.6 + 0.5 * k
                for i in range(count):
                    out[i] += weight * math.sin(k * step * i) * math.exp(-fade * i / RATE)
    place(out, 0, burst(rng, 0.08, "band", 3400, 0.8, 0.014), 9.0)
    return [out[i] * min(1.0, i / (0.004 * RATE)) for i in range(count)]


def drum_roll(rng, seconds):
    out = [0.0] * round(seconds * RATE)
    at, gap, hand = 0.03, 0.105, 0
    while at < 1.75:
        level = (0.22 + 0.6 * (at / 1.75) ** 1.6) * (1.0 if hand % 2 == 0 else 0.86)
        place(out, at, burst(rng, 0.07, "band", 2400, 0.7, 0.022), 2.0 * level)
        place(out, at, burst(rng, 0.07, "high", 5200, 0.7, 0.012), 0.6 * level)
        place(out, at, ring(0.07, [(185, 1.0, 0.03)]), 0.5 * level)
        at += gap
        gap = max(0.034, gap * 0.955)
        hand += 1
    place(out, 1.8, burst(rng, 0.62, "band", 2100, 0.6, 0.09), 2.6)
    place(out, 1.8, burst(rng, 0.62, "high", 4800, 0.7, 0.05), 0.8)
    place(out, 1.8, ring(0.62, [(110, 1.0, 0.12), (196, 0.5, 0.06)]), 1.0)
    return out


def clock_ticks(rng, seconds):
    out = [0.0] * round(seconds * RATE)
    for beat in range(round(seconds / 0.5)):
        tick = beat % 2 == 0
        tones = [(3100, 1.0, 0.005), (5200, 0.5, 0.003), (1450, 0.6, 0.009)] if tick else \
                [(2300, 1.0, 0.006), (4100, 0.4, 0.003), (1050, 0.7, 0.011)]
        place(out, 0.02 + 0.5 * beat, ring(0.06, tones, 0.0003), 1.0 if tick else 0.8)
        place(out, 0.02 + 0.5 * beat, burst(rng, 0.004, "high", 6000, 0.7, 0.0006), 0.5)
    return out


def typing(rng, seconds):
    out = [0.0] * round(seconds * RATE)
    # Draw The Rhythm First And Fit It To The Length, So The Last Key Always Has Room To Ring Out.
    gaps = [rng.uniform(0.075, 0.15) for _ in range(9)]
    span = 0.11
    for gap in gaps:
        span += gap
    pace = min(1.0, (seconds - 0.2) / span)
    at = 0.02
    for key in range(10):
        last = key == 9
        if last:
            at += 0.09 * pace
        level = 1.0 if last else rng.uniform(0.5, 0.9)
        pitch = 205 if last else rng.uniform(260, 420)
        place(out, at, burst(rng, 0.02, "high", 2000, 0.7, 0.003), 1.4 * level)
        place(out, at, burst(rng, 0.03, "band", rng.uniform(1700, 2600), 1.1, 0.005), 3.0 * level)
        place(out, at, ring(0.06, [(pitch, 1.0, 0.022 if last else 0.014), (pitch * 2.7, 0.3, 0.006)]), 0.4 * level)
        place(out, at + rng.uniform(0.045, 0.07), burst(rng, 0.012, "high", 3200, 0.7, 0.002), 0.5 * level)
        if not last:
            at += gaps[key] * pace
    return out


def register(rng, seconds):
    out = [0.0] * round(seconds * RATE)
    for at, level in ((0.01, 0.5), (0.085, 0.6)):
        place(out, at, burst(rng, 0.06, "band", 1400, 0.8, 0.012), 5.0 * level)
        place(out, at, ring(0.08, [(170, 1.0, 0.025)]), 1.4 * level)
    for at, hz, level in ((0.16, 1760.0, 1.0), (0.27, 2093.0, 0.8)):
        place(out, at, ring(seconds - at, [(hz, 1.0, 0.32), (hz * 2.756, 0.55, 0.18), (hz * 5.404, 0.25, 0.08)]), level)
    return out


def coin(rng, seconds):
    out = [0.0] * round(seconds * RATE)
    modes = ((1.0, 1.0, 0.085), (1.59, 0.7, 0.07), (2.14, 0.5, 0.06), (2.30, 0.4, 0.05), (2.65, 0.3, 0.04), (2.92, 0.2, 0.03))
    for at, level in ((0.004, 1.0), (0.17, 0.55), (0.28, 0.3), (0.35, 0.16)):
        base = 2900 * rng.uniform(0.985, 1.015)
        strike = ring(seconds - at, [(base * ratio, weight, tau) for ratio, weight, tau in modes], 0.0004)
        flutter = [strike[i] * (1 - 0.3 * math.sin(TAU * 31 * i / RATE) * math.exp(-i / (0.05 * RATE))) for i in range(len(strike))]
        place(out, at, flutter, level)
    return out


def shutter(rng, seconds):
    out = [0.0] * round(seconds * RATE)
    place(out, 0.012, burst(rng, 0.03, "band", 3200, 1.0, 0.004), 1.4)
    place(out, 0.012, ring(0.04, [(900, 1.0, 0.006)]), 0.3)
    whirr = shape(hiss(rng, round(0.058 * RATE)), "band", 1100, 3.0)
    place(out, 0.02, [whirr[i] * math.sin(math.pi * i / len(whirr)) for i in range(len(whirr))], 0.5)
    place(out, 0.078, burst(rng, 0.05, "band", 2100, 0.8, 0.007), 2.0)
    place(out, 0.078, ring(0.09, [(210, 1.0, 0.018)]), 0.6)
    place(out, 0.15, burst(rng, 0.04, "band", 2800, 0.9, 0.005), 0.9)
    return out


def glitch(rng, seconds):
    count = round(seconds * RATE)
    out, previous = [], []
    while len(out) < count:
        kind = rng.choice(("tone", "tone", "crush", "crush", "gap", "stutter"))
        length = round(rng.uniform(0.018, 0.07) * RATE)
        if kind == "gap":
            piece = [0.0] * round(rng.uniform(0.01, 0.035) * RATE)
        elif kind == "stutter" and previous:
            grain = previous[: round(rng.uniform(0.006, 0.009) * RATE)]
            piece = grain * rng.randint(3, 6)
        elif kind == "tone":
            hz, hold = rng.choice((220, 330, 440, 660, 880, 1320, 1760)), rng.choice((3, 5, 8))
            piece, held = [], 0.0
            for i in range(length):
                if i % hold == 0:
                    held = round(15 * (0.6 if math.sin(TAU * hz * i / RATE) >= 0 else -0.6)) / 15
                piece.append(held)
        else:
            hold, held, piece = rng.randint(4, 18), 0.0, []
            for i in range(length):
                if i % hold == 0:
                    held = rng.uniform(-0.7, 0.7)
                piece.append(held)
        ramp = min(12, len(piece) // 2)
        for i in range(ramp):
            piece[i] *= i / ramp
            piece[-1 - i] *= i / ramp
        if kind != "gap":
            previous = piece
        out.extend(piece)
    return out[:count]


def buzzer(rng, seconds):
    count = round(seconds * RATE)
    out = [0.0] * count
    for start, end, bend in ((0.0, 0.19, 1.0), (0.25, seconds, 0.94)):
        first, last = round(start * RATE), round(end * RATE)
        # Two Notes A Semitone Apart Beat Against Each Other For The Rough Edge Of A Buzzer.
        for hz, level in ((138.59, 1.0), (146.83, 0.8)):
            step = TAU * hz * bend / RATE
            for k in range(1, 21):
                weight = level / k ** 0.75
                for i in range(first, last):
                    out[i] += weight * math.sin(k * step * (i - first))
        edge = round(0.006 * RATE)
        for i in range(first, last):
            out[i] *= min(1.0, (i - first) / edge, (last - 1 - i) / edge)
    return shape(out, "low", 3200, 0.8)


def triad(rng, seconds):
    out = [0.0] * round(seconds * RATE)
    for at, hz, tau in ((0.004, 880.0, 0.16), (0.089, 1108.73, 0.16), (0.174, 1318.51, 0.18)):
        place(out, at, ring(seconds - at, [(hz, 1.0, tau), (hz * 4, 0.35, 0.03)], 0.002))
    return out


def pop(rng, seconds):
    count = round(seconds * RATE)
    click = burst(rng, 0.01, "high", 3500, 0.7, 0.0012)
    out, phase = [], 0.0
    for i in range(count):
        t = i / RATE
        phase += TAU * (260 + 760 * (1 - math.exp(-t / 0.018))) / RATE
        value = math.sin(phase) * min(1.0, t / 0.0015) * math.exp(-t / 0.024)
        out.append(value + (0.25 * click[i] if i < len(click) else 0.0))
    return out


def room_warm(rng, seconds):
    count = round(seconds * RATE)
    low, mid, high = (shape(hiss(rng, count), "low", hz, 0.7) for hz in (180, 900, 3500))
    drift = slow(rng, count, 0.15)
    return [(low[i] + 0.35 * mid[i] + 0.08 * high[i]) * (0.88 + 0.24 * drift[i]) for i in range(count)]


def room_bright(rng, seconds):
    count = round(seconds * RATE)
    mid = shape(hiss(rng, count), "low", 2500, 0.7)
    air = shape(hiss(rng, count), "band", 4500, 0.6)
    low = shape(hiss(rng, count), "low", 250, 0.7)
    drift = slow(rng, count, 0.2)
    return [(0.6 * mid[i] + 0.25 * air[i] + 0.5 * low[i] + 0.02 * math.sin(TAU * 120 * i / RATE))
            * (0.9 + 0.2 * drift[i]) for i in range(count)]


def machine_hum(rng, seconds):
    count = round(seconds * RATE)
    fan = shape(hiss(rng, count), "band", 700, 0.8)
    low = shape(hiss(rng, count), "low", 150, 0.7)
    drift = slow(rng, count, 0.25)
    # Mains Harmonics With One Slightly Detuned Partner For A Slow Beat. The Upper Ones Reach Small Speakers.
    parts = [(60, 0.4), (120, 1.0), (120.37, 0.25), (180, 0.5), (240, 0.4), (300, 0.22), (360, 0.3), (480, 0.16),
             (600, 0.14), (720, 0.09), (840, 0.06)]
    steps = [(TAU * hz / RATE, level, rng.uniform(0, TAU)) for hz, level in parts]
    out = []
    for i in range(count):
        tone = 0.0
        for step, level, offset in steps:
            tone += level * math.sin(step * i + offset)
        out.append((tone + 2.4 * fan[i] + 1.2 * low[i]) * (0.92 + 0.16 * drift[i]))
    return out


def night_air(rng, seconds):
    count = round(seconds * RATE)
    wind = shape(hiss(rng, count), "low", 420, 0.7)
    swell = slow(rng, count, 0.2)
    out = [1.6 * wind[i] * (0.6 + 0.4 * swell[i]) for i in range(count)]
    for hz, period, pulses, rate, level in ((4300, 0.52, 3, 29, 0.34), (4720, 0.71, 4, 33, 0.2), (3890, 0.93, 2, 25, 0.15)):
        at = rng.uniform(0.05, period)
        window = round(0.014 * RATE)
        chirp = [math.sin(TAU * hz * i / RATE) * math.sin(math.pi * i / window) ** 2 for i in range(window)]
        while at < seconds - 0.3:
            for pulse in range(pulses):
                place(out, at + pulse / rate, chirp, level * rng.uniform(0.8, 1.0))
            at += period * rng.uniform(0.94, 1.06)
    return out


def water(rng, seconds):
    count = round(seconds * RATE)
    wide = shape(hiss(rng, count), "band", 1500, 0.5)
    high = shape(hiss(rng, count), "band", 3200, 0.8)
    ripple, shimmer = slow(rng, count, 12), slow(rng, count, 9)
    out = [wide[i] * (0.35 + 0.65 * ripple[i]) + 0.3 * high[i] * (0.3 + 0.7 * shimmer[i]) for i in range(count)]
    at = 0.0
    while at < seconds - 0.1:
        length = round(rng.uniform(0.025, 0.07) * RATE)
        base, level, phase, drop = rng.uniform(450, 1300), rng.uniform(0.03, 0.12), 0.0, []
        for i in range(length):
            phase += TAU * base * (1 + 0.5 * i / length) / RATE
            drop.append(math.sin(phase) * math.sin(math.pi * i / length))
        place(out, at, drop, level)
        at += rng.uniform(0.03, 0.11)
    return out


def static(rng, seconds):
    count = round(seconds * RATE)
    grain = shape(shape(hiss(rng, count), "high", 500, 0.7), "low", 4800, 0.7)
    flutter, wander = slow(rng, count, 6), slow(rng, count, 0.4)
    out, phase, spark = [], 0.0, 0.0
    for i in range(count):
        t = i / RATE
        if rng.random() < 25 / RATE:
            spark = rng.uniform(0.3, 1.0) * rng.choice((-1, 1))
        spark *= 0.95
        phase += TAU * (2100 + 500 * (wander[i] - 0.5)) / RATE
        dip = 0.3 if 1.9 < t < 1.96 or 4.2 < t < 4.26 else 1.0
        whistle = 0.05 * math.sin(phase) * math.sin(math.pi * t / seconds) ** 2
        out.append((grain[i] * (0.75 + 0.25 * flutter[i]) + 0.6 * spark + whistle) * dip)
    return out


# Name, Family, Seconds, Generator, Level In dBFS, And Whether The Level Is Peak Or RMS.
DESIGNS = [
    ("whoosh-light", "whoosh", 0.32, lambda r, s: whoosh(r, s, 1800, 7000, 3000, 1.2, 0.55), -6.0, "peak"),
    ("whoosh-medium", "whoosh", 0.55, lambda r, s: whoosh(r, s, 700, 4200, 1500, 1.0, 0.6), -6.0, "peak"),
    ("whoosh-heavy", "whoosh", 0.95, lambda r, s: whoosh(r, s, 180, 1800, 500, 0.9, 0.62, 0.42), -5.0, "peak"),
    ("whoosh-reverse", "whoosh", 0.7, pull, -6.0, "peak"),
    ("riser-tension", "riser", 2.4, riser, -6.0, "peak"),
    ("drum-roll-build", "roll", 2.45, drum_roll, -4.0, "peak"),
    ("stinger-bright", "stinger", 1.4, stinger, -4.0, "peak"),
    ("impact-deep", "impact", 1.6, impact, -4.0, "peak"),
    ("pop-bubble", "pop", 0.13, pop, -6.0, "peak"),
    ("clock-ticks", "ticks", 3.0, clock_ticks, -9.0, "peak"),
    ("typing-burst", "keys", 1.3, typing, -8.0, "peak"),
    ("register-chime", "chime", 1.6, register, -6.0, "peak"),
    ("coin-ping", "chime", 0.6, coin, -6.0, "peak"),
    ("shutter-mechanical", "shutter", 0.22, shutter, -6.0, "peak"),
    ("glitch-stutter", "glitch", 0.5, glitch, -12.0, "peak"),
    ("error-buzz", "buzz", 0.52, buzzer, -7.0, "peak"),
    ("notify-triad", "notify", 0.9, triad, -6.0, "peak"),
    ("room-tone-warm", "bed", 8.0, room_warm, -27.0, "rms"),
    ("room-tone-bright", "bed", 8.0, room_bright, -27.0, "rms"),
    ("machine-hum", "bed", 8.0, machine_hum, -27.0, "rms"),
    ("night-air", "bed", 10.0, night_air, -27.0, "rms"),
    ("water-stream", "bed", 8.0, water, -27.0, "rms"),
    ("radio-static", "bed", 6.0, static, -27.0, "rms"),
]
BED_FADE = 0.25


def design(name, family, seconds, generator, level, measure):
    """Render One Second-Set Cue As Little-Endian 16-Bit Mono Samples."""
    samples = generator(source(name), seconds)
    count = len(samples)
    total = 0.0
    for value in samples:
        total += value
    mean = total / count
    samples = [value - mean for value in samples]
    if family == "bed":
        # Equal-Power Ends Let Two Overlapped Copies Cross Without A Dip.
        ramp = round(BED_FADE * RATE)
        for i in range(ramp):
            gain = math.sin(0.5 * math.pi * i / ramp)
            samples[i] *= gain
            samples[count - 1 - i] *= gain
    else:
        lead, tail = round(0.002 * RATE), round(0.012 * RATE)
        for i in range(lead):
            samples[i] *= i / lead
        for i in range(tail):
            samples[count - 1 - i] *= i / tail
    peak = 0.0
    power = 0.0
    for value in samples:
        peak = max(peak, abs(value))
        power += value * value
    reference = peak if measure == "peak" else math.sqrt(power / count)
    gain = 10 ** (level / 20) / reference
    # Beds Are Set By Average Level. A Stray Peak Is Held Under Minus 9 dBFS.
    gain = min(gain, 10 ** (-9 / 20) / peak) if measure == "rms" else gain
    pcm = array("h", (max(-32767, min(32767, round(32767 * gain * value))) for value in samples))
    if sys.byteorder != "little":
        pcm.byteswap()
    return pcm.tobytes()


# Tags And One Suggested Use For Every Cue. Tags Are Lowercase Search Words.
NOTES = {
    "button-down": ("tap click ui button press low", "Mark A Button Press Or A Tap On Screen."),
    "button-up": ("tap click ui button release", "Mark A Release, A Toggle, Or A Small Confirmation."),
    "small-switch": ("tap click ui switch toggle", "Mark A Toggle Or A Setting Change."),
    "glass-point": ("bell ping highlight bright callout", "Point At One Detail Or Land A Highlighted Word."),
    "menu-open": ("rise ui open reveal tone", "Open A Menu, A Panel, Or A New Section."),
    "menu-close": ("fall ui close dismiss tone", "Close A Panel Or Dismiss An Element."),
    "success-pair": ("pair success confirm positive notification", "Confirm A Result Or A Completed Step."),
    "gentle-alert": ("pair alert caution soft notification", "Flag A Caution Without Alarm."),
    "enter-confirm": ("bell confirm enter submit ui", "Confirm A Submitted Form Or A Sent Message."),
    "counter-step": ("tap count step list tick", "Count List Items Or Steps As They Appear."),
    "page-flick": ("brush swipe page paper transition short", "Flip A Page Or Swap A Still."),
    "soft-swipe": ("brush swipe transition soft whoosh", "Carry A Gentle Slide Or A Screen Swipe."),
    "quick-pass": ("brush whoosh fast short transition", "Accent A Fast Cut Or A Quick Punch-In."),
    "long-sweep": ("brush sweep whoosh long transition build", "Bridge Two Scenes Or Lead Into A Reveal."),
    "low-drop": ("bump drop low impact bass", "Land A Reveal Or Underline A Heavy Statement."),
    "transition-hit": ("bump hit impact cut short", "Punctuate A Hard Cut."),
    "marker-knock": ("tap knock wood marker low", "Mark A Chapter Point Or A Knock On A Surface."),
    "paper-touch": ("grain paper texture rustle soft", "Add Texture To A Document Or A Card Appearing."),
    "countdown-tick": ("tap tick countdown clock count", "Tick Each Number Of A Countdown."),
    "countdown-finish": ("bell finish countdown end chime", "Close A Countdown Or Mark Time Up."),
    "soft-key": ("tap key typing keyboard short", "Place One Key Press Under On-Screen Typing."),
    "three-keys": ("steps keys typing keyboard sequence", "Suggest A Short Run Of Typing."),
    "receipt-feed": ("steps printer receipt mechanical feed", "Suggest A Printer, A Receipt, Or A Mechanical Feed."),
    "shutter-snap": ("grain camera shutter photo snap", "Mark A Photo, A Screenshot, Or A Freeze Frame."),
    "low-pulse": ("bump pulse low bass tension", "Add A Low Heartbeat Under A Tense Moment."),
    "dial-turn": ("steps dial knob ratchet adjust", "Suggest A Dial Or A Value Being Adjusted."),
    "spring-reveal": ("rise reveal spring playful pop", "Lift A Playful Reveal Or An Element Popping In."),
    "rubber-stop": ("fall stop bounce playful decline", "Mark A Playful Stop Or A Number Going Down."),
    "notification-bloom": ("bell notification message bloom long", "Announce A Message With A Long Tail."),
    "focus-shift": ("brush whoosh focus settle transition", "Follow A Rack Focus Or A Slow Reframe."),
    "desk-air": ("bed ambience room air quiet texture", "Fill A Short Gap Between Cuts With Quiet Air."),
    "machine-idle": ("bed ambience machine hum low", "Sit Under A Device Or A Workshop Shot."),
    "soft-room": ("bed ambience room tone quiet", "Hold Room Presence Under A Pause In Speech."),
    "whoosh-light": ("whoosh transition fast light airy swipe", "Carry A Quick Swipe, A Text Fly-In, Or A Light Punch-In."),
    "whoosh-medium": ("whoosh transition pass medium cut", "Bridge A Standard Cut Or A Slide Between Two Shots."),
    "whoosh-heavy": ("whoosh transition heavy low long weight", "Give Weight To A Big Scene Change Or A Slow Push."),
    "whoosh-reverse": ("whoosh reverse pull swell cut build", "Pull Into A Hard Cut. End It On The Cut Frame."),
    "riser-tension": ("riser build tension rise long reveal", "Build Toward A Reveal. End It Where The Impact Or The Answer Lands."),
    "drum-roll-build": ("drum roll build snare reveal anticipation", "Hold Anticipation Before A Result. The Final Hit Lands At 1.8 Seconds."),
    "stinger-bright": ("stinger hit chord accent bright title", "Accent A Title Card, A Logo, Or A Punchline."),
    "impact-deep": ("impact hit deep low boom sub", "Land A Big Reveal. Its Mid Layer Keeps It Audible On A Phone."),
    "pop-bubble": ("pop bubble ui short playful appear", "Pop In A Sticker, An Emoji, Or A Caption Word."),
    "clock-ticks": ("clock tick tock time loop countdown", "Show Time Passing. Six Ticks Half A Second Apart Repeat Cleanly Every 3 Seconds."),
    "typing-burst": ("typing keys keyboard burst computer", "Play Under On-Screen Typing Or A Search Being Entered."),
    "register-chime": ("register cash money sale chime bell", "Mark A Sale, A Price, Or A Money Moment."),
    "coin-ping": ("coin money ping metal bounce reward", "Mark A Small Win, A Saving, Or A Point Scored."),
    "shutter-mechanical": ("camera shutter photo mechanical click", "Mark A Photo With A Fuller Two-Stage Shutter."),
    "glitch-stutter": ("glitch digital stutter error transition", "Cover A Jump Cut Or Signal A Digital Fault."),
    "error-buzz": ("error buzz wrong negative alert", "Mark A Wrong Answer, A Mistake, Or A Thing To Avoid."),
    "notify-triad": ("notification message chime rising ui", "Announce A Message, A Reply, Or A New Follower."),
    "room-tone-warm": ("bed ambience room tone warm low loop", "Fill Silence Between Cuts In An Indoor Take."),
    "room-tone-bright": ("bed ambience room tone bright air loop", "Fill Silence In A Bright Or Hard-Walled Room."),
    "machine-hum": ("bed ambience machine hum electric loop", "Sit Under Equipment, A Server, Or An Appliance."),
    "night-air": ("bed ambience night outdoor crickets wind loop", "Set A Quiet Outdoor Night."),
    "water-stream": ("bed ambience water stream brook nature loop", "Set A Stream, A Fountain, Or A Calm Outdoor Scene."),
    "radio-static": ("bed ambience radio static noise retro loop", "Suggest A Radio, An Old Recording, Or A Lost Signal."),
}


def levels(raw):
    """Measured Sample Peak And RMS In dBFS. A Full-Scale Sine Reads Minus 3 RMS."""
    pcm = array("h")
    pcm.frombytes(raw)
    if sys.byteorder != "little":
        pcm.byteswap()
    peak, power = 0, 0
    for value in pcm:
        peak = max(peak, abs(value))
        power += value * value
    rms = math.sqrt(power / len(pcm))

    def decibels(value):
        return round(20 * math.log10(value / 32768), 1) if value else None

    return decibels(peak), decibels(rms)


def render(name):
    """The Complete Sample Data For One Cue By Name."""
    for index, spec in enumerate(PROGRAMS):
        if spec[0] == name:
            return synth(index, *spec)
    for spec in DESIGNS:
        if spec[0] == name:
            return design(*spec)
    raise KeyError(name)


def catalog():
    return [(spec[0], spec[1], spec[2]) for spec in PROGRAMS] + [(spec[0], spec[1], spec[2]) for spec in DESIGNS]


def build(directory):
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for name, family, duration in catalog():
        raw = render(name)
        path = directory / (name + ".wav")
        with wave.open(str(path), "wb") as wav:
            wav.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
            wav.writeframes(raw)
        tags, use = NOTES[name]
        peak, rms = levels(raw)
        record = {
            "file": path.name,
            "family": family,
            "seconds": duration,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "tags": tags.split(),
            "use": use,
            "peak_dbfs": peak,
            "rms_dbfs": rms,
        }
        if family == "bed" and any(name == spec[0] for spec in DESIGNS):
            record["overlap_seconds"] = BED_FADE
        records.append(record)
    with (directory / "index.json").open("w", encoding="utf-8", newline="\n") as index:
        index.write(json.dumps(records, indent=2) + "\n")
    print(f"Built {len(records)} Original Cue Files.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="New Or Empty Output Folder")
    target = parser.parse_args().directory
    if target.exists() and any(target.iterdir()):
        parser.error("Choose A New Or Empty Output Folder.")
    build(target)
