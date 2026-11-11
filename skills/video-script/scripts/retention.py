"""Measure Audience Retention From A CSV Or A Chart Image."""

import argparse
import bisect
import csv
import io
import math
import shutil
import statistics
import struct
import subprocess
import sys
import tempfile
import zlib
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from desk_support import (  # noqa: E402
    DeskParser,
    clock,
    guard_streams,
    number_text,
    read_text,
    tidy_json,
    write_new,
)


FIXED_SECONDS = (1, 2, 3, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180)
AVERAGE_TOLERANCE = 3.0
LIST_LENGTH = 3
CURVE_POINTS = 240
SELFTEST_POINTS = 1.5
SELFTEST_SECONDS = 0.5
BY_HAND = (
    "Supply The Plot Rectangle And Line Color By Hand With "
    "--plot LEFT TOP RIGHT BOTTOM And --color RED GREEN BLUE."
)
PRACTICE_CURVE = (
    (0.0, 100.0),
    (0.06, 74.0),
    (0.10, 66.0),
    (0.33, 52.0),
    (0.40, 50.0),
    (0.62, 48.5),
    (0.68, 39.0),
    (0.95, 31.0),
    (1.0, 27.0),
)


class Unsure(ValueError):
    """Automatic Calibration Could Not Reach A Confident Reading."""


# Curve Measurements


def reading(samples, times, at, slack=0.0):
    """Interpolate The Curve At One Second, Or Return None Outside The Measured Span."""
    if at < times[0] - slack or at > times[-1] + slack:
        return None
    if at <= times[0]:
        return samples[0][1]
    if at >= times[-1]:
        return samples[-1][1]
    index = bisect.bisect_right(times, at)
    (t0, p0), (t1, p1) = samples[index - 1], samples[index]
    return p0 + (p1 - p0) * (at - t0) / (t1 - t0)


def edge_slack(times):
    spacing = statistics.median(b - a for a, b in zip(times, times[1:]))
    return max(0.5 * spacing, 0.005 * (times[-1] - times[0]))


def area_average(samples):
    """Return Seconds Watched Per Viewer Implied By The Area Under The Curve."""
    total = samples[0][0] * samples[0][1]
    for (t0, p0), (t1, p1) in zip(samples, samples[1:]):
        total += (t1 - t0) * (p0 + p1) / 2
    return total / 100


def stretches(samples, times, count, grain=None):
    """List The Steepest Drops And The Flattest Stretches With Their Time Ranges.

    Rates Are Compared With The Curve's Typical Loss Per Second, The Larger Of Its Median
    Local Rate And A Quarter Of Its Overall Rate. A Drop Grows Outward From A Peak Above
    One And A Half Times That Rate Until The Loss Falls To Half The Peak. A Flat Stretch
    Loses Under Half The Typical Rate For At Least One Second.
    """
    first, last = times[0], times[-1]
    span = last - first
    spacing = statistics.median(b - a for a, b in zip(times, times[1:]))
    window = min(span, max(0.5, span / 60, spacing))
    cells = min(1200, max(1, math.ceil(span / (window / 4))))
    size = span / cells

    def level(at):
        return reading(samples, times, min(max(at, first), last))

    def rates_over(width):
        found = []
        for cell in range(cells):
            middle = first + (cell + 0.5) * size
            start = max(first, middle - width / 2)
            end = min(last, middle + width / 2)
            found.append((level(end) - level(start)) / (end - start))
        return found

    losses = [-rate for rate in rates_over(window)]
    overall = (samples[0][1] - samples[-1][1]) / span
    base = max(statistics.median(losses), 0.25 * overall, 0.05)
    steep, flat, taken = [], [], [False] * cells
    # Grow a drop outward from each peak until the loss falls to half the peak rate.
    for peak in sorted(range(cells), key=lambda cell: -losses[cell]):
        if losses[peak] <= 1.5 * base:
            break
        if taken[peak]:
            continue
        floor = max(0.5 * losses[peak], base)
        begin = stop = peak
        while begin > 0 and not taken[begin - 1] and losses[begin - 1] > floor:
            begin -= 1
        while stop < cells - 1 and not taken[stop + 1] and losses[stop + 1] > floor:
            stop += 1
        for cell in range(begin, stop + 1):
            taken[cell] = True
        start = first + begin * size
        end = last if stop == cells - 1 else first + (stop + 1) * size
        change = level(end) - level(start)
        if change <= -1:
            steep.append(
                {
                    "from": round(start, 2),
                    "to": round(end, 2),
                    "delta_points": round(change, 2),
                    "points_per_second": round(change / (end - start), 2),
                }
            )
    # Values read from pixels or rounded in a CSV move in small steps. A wider window
    # keeps one step from breaking a plateau, then each end is walked back out.
    if grain is None:
        values = sorted({pct for _, pct in samples})
        grain = min((b - a for a, b in zip(values, values[1:])), default=0.0)
    wide = min(max(window, 6 * grain / base), max(window, span / 4))
    calm = [abs(rate) < 0.5 * base for rate in rates_over(wide)]
    reach = (wide - window) / 2
    cell = 0
    while cell < cells:
        begin = cell
        while cell < cells and calm[cell] and not taken[cell]:
            cell += 1
        if cell == begin:
            cell += 1
            continue
        start = first + begin * size
        end = last if cell == cells else first + cell * size
        for edge, way in ((start, -1), (end, 1)):
            moved = 0.0
            while moved + size <= reach + 1e-9:
                spot = edge + way * (moved + size)
                if not first <= spot <= last or taken[min(cells - 1, int((spot - first) / size))]:
                    break
                if abs(level(spot) - level(edge)) > 0.5 * base * (moved + size) + grain:
                    break
                moved += size
            if way < 0:
                start = edge - moved
            else:
                end = edge + moved
        if end - start >= max(1.0, 0.03 * span):
            flat.append(
                {
                    "from": round(start, 2),
                    "to": round(end, 2),
                    "seconds": round(end - start, 2),
                    "delta_points": round(level(end) - level(start), 2),
                }
            )
    steep.sort(key=lambda row: row["delta_points"])
    flat.sort(key=lambda row: -row["seconds"])
    return steep[:count], flat[:count]


def compact_curve(samples, times):
    """Return At Most CURVE_POINTS Intervals Of The Curve For Later Comparisons."""
    if len(samples) <= CURVE_POINTS + 1:
        return [[round(t, 3), round(p, 2)] for t, p in samples]
    first, span = times[0], times[-1] - times[0]
    return [
        [
            round(first + span * step / CURVE_POINTS, 3),
            round(reading(samples, times, first + span * step / CURVE_POINTS), 2),
        ]
        for step in range(CURVE_POINTS + 1)
    ]


def measure(samples, coverage, a, runtime, calibration, notes=()):
    """Build The Report. The First Six Fields Keep Their Original Meaning And Order."""
    if len(samples) < 2 or any(
        not math.isfinite(v) or v < 0 for pair in samples for v in pair
    ):
        raise ValueError("Supply At Least Two Finite Nonnegative Measurements.")
    if any(b[0] <= c[0] for c, b in zip(samples, samples[1:])):
        raise ValueError("Measurement Times Must Increase.")
    if a.interval <= 0 or not math.isfinite(a.interval):
        raise ValueError("Use A Positive Comparison Interval.")
    if a.count < 1:
        raise ValueError("List At Least One Drop And One Stretch.")
    if not math.isfinite(a.average_tolerance) or a.average_tolerance < 0:
        raise ValueError("Use A Nonnegative Average Tolerance In Seconds.")
    # Compare adjacent measured windows instead of reporting single-pixel fluctuations.
    changes = []
    end = 1
    for i, (at, pct) in enumerate(samples):
        end = max(i + 1, end)
        while end < len(samples) and samples[end][0] - at < a.interval:
            end += 1
        if end == len(samples):
            break
        changes.append(
            {
                "from": round(at, 3),
                "to": round(samples[end][0], 3),
                "delta_points": round(samples[end][1] - pct, 2),
            }
        )
    drop = min(changes, key=lambda row: row["delta_points"], default=None)
    lift = max(changes, key=lambda row: row["delta_points"], default=None)

    times = [t for t, _ in samples]
    slack = edge_slack(times)
    if runtime is None:
        runtime = times[-1]
    if not math.isfinite(runtime) or runtime <= 0:
        raise ValueError("Use A Positive Runtime In Seconds.")
    if runtime < times[-1] - slack:
        raise ValueError(
            f"The Curve Runs To {number_text(times[-1], 2)} Seconds, Past The "
            f"{number_text(runtime, 2)}-Second Runtime. Check The Runtime."
        )
    warnings = list(notes)
    if a.at is None:
        wanted = [s for s in FIXED_SECONDS if times[0] - slack <= s <= times[-1] + slack]
    else:
        if any(not math.isfinite(s) or s < 0 for s in a.at):
            raise ValueError("Readings Need Finite Nonnegative Seconds.")
        wanted = sorted(set(a.at))
    readings = []
    for second in wanted:
        value = reading(samples, times, second, slack)
        readings.append(
            {
                "seconds": int(second) if second == int(second) else second,
                "retention_pct": None if value is None else round(value, 2),
            }
        )
    third, tenth = reading(samples, times, 3, slack), reading(samples, times, 10, slack)
    average = area_average(samples)
    if times[0] > max(slack, 0.01 * runtime):
        warnings.append(
            f"The Curve Starts At {number_text(times[0], 2)} Seconds. "
            "The Area Before It Uses The First Reading."
        )
    if runtime - times[-1] > max(slack, 0.01 * runtime):
        warnings.append(
            f"The Curve Ends At {number_text(times[-1], 2)} Seconds Of A "
            f"{number_text(runtime, 2)}-Second Runtime. "
            "The Area-Based Average Is A Lower Bound."
        )
    if max(p for _, p in samples) > 100.5:
        warnings.append(
            "Some Readings Exceed 100 Percent. Platforms Count Replays This Way, "
            "Which Raises The Area-Based Average."
        )
    gap = None
    if a.reported_average is not None:
        gap = average - a.reported_average
        if abs(gap) > a.average_tolerance:
            warnings.append(
                f"The Area Under The Curve Implies {number_text(average, 2)} Seconds "
                f"Of Average Watch Time But The App Reports "
                f"{number_text(a.reported_average, 2)}. A Gap Above "
                f"{number_text(a.average_tolerance, 2)} Seconds Usually Means A "
                "Misread Chart. Check The Plot Rectangle, Axis Bounds, Line Color, "
                "And Duration. Replays Counted By The App Can Also Widen The Gap."
            )
    grain = None
    if calibration:
        box = calibration["plot"]
        grain = (calibration["axis_top"] - calibration["axis_bottom"]) / (box[3] - box[1])
    steep, flat = stretches(samples, times, a.count, grain)
    report = {
        "samples": len(samples),
        "chart_coverage": coverage,
        "first_pct": round(samples[0][1], 2),
        "last_pct": round(samples[-1][1], 2),
        "largest_drop": drop if drop and drop["delta_points"] < 0 else None,
        "largest_lift": lift if lift and lift["delta_points"] > 0 else None,
        "duration_seconds": round(runtime, 3),
        "readings": readings,
        "drop_3_to_10_points": (
            None if third is None or tenth is None else round(third - tenth, 2)
        ),
        "average_watch_seconds": round(average, 2),
        "average_watch_share_pct": round(100 * average / runtime, 1),
        "reported_average_seconds": a.reported_average,
        "average_gap_seconds": None if gap is None else round(gap, 2),
        "steepest_drops": steep,
        "flattest_stretches": flat,
        "calibration": calibration,
        "warnings": warnings,
    }
    return report, compact_curve(samples, times)


def table(path):
    try:
        text = read_text(path)
    except UnicodeError as exc:
        raise ValueError(f"{path} Is Not UTF-8 Text.") from exc
    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not {"seconds", "retention_pct"} <= set(reader.fieldnames or ()):
        raise ValueError("Expected CSV Columns Named seconds And retention_pct.")
    rows = []
    for number, row in enumerate(reader, 2):
        try:
            percent = float(str(row["retention_pct"]).strip().rstrip("%"))
            rows.append((float(row["seconds"]), percent))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Line {number} Needs A Number For seconds And For retention_pct."
            ) from exc
    return rows


# Image Decoding


def decoder(command, path):
    """Run FFmpeg Or FFprobe The Way The Original Reader Did And Return Its Output."""
    try:
        return subprocess.check_output(command, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise ValueError("Image Mode Needs FFmpeg And FFprobe On PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise ValueError(f"FFmpeg Could Not Read {path} As An Image.") from exc


def image_size(path):
    size = decoder(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(path),
        ],
        path,
    ).decode("ascii", "replace")
    try:
        wide, tall = map(int, size.strip().split(",")[:2])
    except ValueError as exc:
        raise ValueError(f"FFprobe Found No Picture In {path}.") from exc
    return wide, tall


def decode(path, crop=None):
    """Return RGB Bytes For The Whole Picture Or For One Width, Height, Left, Top Crop."""
    chain = "format=rgb24"
    if crop:
        chain += ",crop={}:{}:{}:{}".format(*crop)
    command = ["ffmpeg", "-v", "error", "-i", str(path), "-vf", chain]
    command += ["-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    return decoder(command, path)


# Whole-Image Arithmetic On Python Integers


def _table(test):
    return bytes(1 if test(value) else 0 for value in range(256))


def _both(*flags):
    value = int.from_bytes(flags[0], "big")
    for other in flags[1:]:
        value &= int.from_bytes(other, "big")
    return value.to_bytes(len(flags[0]), "big")


def _flags(plane, test):
    """Return One Integer Holding A One Byte Wherever A Plane Value Passes A Test."""
    return int.from_bytes(plane.translate(_table(test)), "big")


def _widen(plane):
    wide = bytearray(2 * len(plane))
    wide[1::2] = plane
    return int.from_bytes(wide, "big")


def _narrow(value, count):
    return value.to_bytes(2 * count, "big")[1::2]


def _ones(buffer, start=0):
    """Yield The Offsets Of Every Byte Set To One."""
    index = buffer.find(1, start)
    while index != -1:
        yield index
        index = buffer.find(1, index + 1)


class Planes:
    """Luma And Chroma For Every Pixel, Held In 16-Bit Lanes Of One Large Integer."""

    def __init__(self, pixels, width, height):
        self.pixels, self.width, self.height = pixels, width, height
        self.count = count = width * height
        if len(pixels) != 3 * count:
            raise ValueError("Incomplete Input Image.")
        self.ones = int.from_bytes(b"\x00\x01" * count, "big")
        self.guard = self.ones << 14
        self.low = (self.ones << 8) - self.ones
        self.full = (1 << (16 * count)) - 1
        red, green, blue = (_widen(pixels[c::3]) for c in range(3))
        self.luma = ((red + (green << 1) + blue) >> 2) & self.low
        gap = self.minus(red, green)
        high, low = green + gap, red - gap
        high = blue + self.minus(high, blue)
        low = low - self.minus(low, blue)
        self.chroma_lanes = high - low
        self.chroma = _narrow(self.chroma_lanes, count)

    def minus(self, a, b):
        """Subtract Lane By Lane And Stop At Zero. Lane Values Stay Below 16384."""
        raw = (a | self.guard) - b
        keep = (raw >> 14) & self.ones
        return raw & ((keep << 14) - keep)

    def thin_lines(self, reach=4, contrast=5, drift=12):
        """Flag Pixels Lighter Or Darker Than Both Vertical Neighbors Without Added Color.

        A Neighbor That Belongs To The Curve Cannot Be Compared, So One Such Neighbor Is
        Excused. This Keeps A Gridline Whole Where The Curve Runs Just Above Or Below It.
        """
        count, shift = self.count, 16 * self.width * reach
        luma, chroma = self.luma, self.chroma_lanes
        above, below = luma >> shift, (luma << shift) & self.full
        hue_above, hue_below = chroma >> shift, (chroma << shift) & self.full
        gain_above = self.minus(chroma, hue_above)
        gain_below = self.minus(chroma, hue_below)
        gain = gain_below + self.minus(gain_above, gain_below)
        plain = _flags(_narrow(gain, count), lambda v: v <= drift)
        vivid_above = _flags(_narrow(hue_above, count), lambda v: v >= 40)
        vivid_below = _flags(_narrow(hue_below, count), lambda v: v >= 40)
        found = []
        for upper, lower in (
            (self.minus(luma, above), self.minus(luma, below)),
            (self.minus(above, luma), self.minus(below, luma)),
        ):
            over = _flags(_narrow(upper, count), lambda v: v >= contrast)
            under = _flags(_narrow(lower, count), lambda v: v >= contrast)
            keep = ((over & under) | (over & vivid_below) | (vivid_above & under)) & plain
            found.append(keep.to_bytes(count, "big"))
        return tuple(found)


def match_columns(pixels, stride, x0, y0, wide, tall, color, tolerance):
    """Return, For Each Column Of A Region, The Row Offsets That Match The Line Color."""
    if x0 == 0 and wide == stride:
        block = pixels[3 * y0 * stride : 3 * (y0 + tall) * stride]
    else:
        block = b"".join(
            pixels[3 * (y * stride + x0) : 3 * (y * stride + x0 + wide)]
            for y in range(y0, y0 + tall)
        )
    flags = _both(
        *(
            block[c::3].translate(_table(lambda v, c=c: abs(v - color[c]) <= tolerance))
            for c in range(3)
        )
    )
    return [list(_ones(flags[x::wide])) for x in range(wide)]


# Manual Calibration


def chart(a):
    left, top, right, bottom = a.plot
    if min(left, top) < 0 or right <= left or bottom <= top:
        raise ValueError("Use A Positive Plot Rectangle In Image Coordinates.")
    iw, ih = image_size(a.file)
    if right >= iw or bottom >= ih:
        raise ValueError("The Plot Extends Outside The Image.")
    w, h = right - left + 1, bottom - top + 1
    return plot_samples(decode(a.file, (w, h, left, top)), w, h, a)


def plot_samples(buf, w, h, a):
    """Read The Curve From The Pixels Inside A Supplied Plot Rectangle."""
    if len(buf) != w * h * 3:
        raise ValueError("Incomplete Input Image.")
    if a.color is None:
        try:
            a.color = vivid_colors(Planes(buf, w, h), 0, 0, w - 1, h - 1)[0]
        except Unsure as exc:
            raise ValueError(
                f"Automatic Calibration Is Not Confident. {exc}. "
                "Supply The Line Color By Hand With --color RED GREEN BLUE."
            ) from exc
    samples = []
    for x, hits in enumerate(match_columns(buf, w, 0, 0, w, h, a.color, a.tolerance)):
        if hits:
            pct = a.top + (a.bottom - a.top) * statistics.median(hits) / (h - 1)
            samples.append((x * a.seconds / (w - 1), pct))
    if len(samples) < 2:
        raise ValueError("Too Few Line Pixels. Check The Plot And Line Color.")
    return samples, round(len(samples) / w, 3)


# Automatic Calibration


def gridline_candidates(planes, reach=4):
    """Find Thin Horizontal Lines With Their Row And Horizontal Extent."""
    w, h = planes.width, planes.height
    vivid = planes.chroma.translate(_table(lambda v: v >= 40))
    least, gap, shortest = max(16, w // 12), max(6, w // 80), max(60, w // 5)
    lines = []
    for tone, flags in zip(("light", "dark"), planes.thin_lines(reach)):
        counts = [
            flags.count(1, y * w, (y + 1) * w) if reach <= y < h - reach else 0
            for y in range(h)
        ]
        y = 0
        while y < h:
            if counts[y] < least:
                y += 1
                continue
            start = y
            while y < h and counts[y] >= least:
                y += 1
            if y - start > 8:
                continue
            best = max(range(start, y), key=counts.__getitem__)
            row = flags[best * w : (best + 1) * w]
            marks = (
                int.from_bytes(row, "big")
                | int.from_bytes(vivid[best * w : (best + 1) * w], "big")
            ).to_bytes(w, "big")
            spans, begin, last = [], None, None
            for x in _ones(marks):
                if begin is None:
                    begin = last = x
                elif x - last - 1 <= gap:
                    last = x
                else:
                    spans.append((begin, last))
                    begin = last = x
            if begin is not None:
                spans.append((begin, last))
            if not spans:
                continue
            begin, last = max(spans, key=lambda s: row.count(1, s[0], s[1] + 1))
            length = last - begin + 1
            if length >= shortest and row.count(1, begin, last + 1) >= 0.12 * length:
                lines.append(
                    {
                        "y": (start + y - 1) // 2,
                        "left": begin,
                        "right": last,
                        "tone": tone,
                    }
                )
    return sorted(lines, key=lambda line: line["y"])


def ladders(lines, width, height):
    """Group Lines Into Evenly Spaced Sets That Share One Horizontal Extent."""
    reach = max(6, width // 50)
    smallest = max(8, height // 100)

    def alike(a, b):
        return (
            a["tone"] == b["tone"]
            and abs(a["left"] - b["left"]) <= reach
            and abs(a["right"] - b["right"]) <= reach
        )

    found = []
    heights = [line["y"] for line in lines]
    for i, first in enumerate(lines):
        for j in range(i + 1, len(lines)):
            step = lines[j]["y"] - first["y"]
            if step < smallest or not alike(first, lines[j]):
                continue
            members = [i, j]
            give = max(2.0, 0.05 * step)
            while True:
                tail = lines[members[-1]]["y"]
                expected = tail + (tail - first["y"]) / (len(members) - 1)
                close = [
                    k
                    for k in range(
                        bisect.bisect_left(heights, expected - give),
                        bisect.bisect_right(heights, expected + give),
                    )
                    if k > members[-1] and alike(first, lines[k])
                ]
                if not close:
                    break
                members.append(min(close, key=lambda k: abs(lines[k]["y"] - expected)))
            if len(members) >= 3:
                found.append([lines[k] for k in members])
    found.sort(key=lambda group: (-len(group), group[0]["y"] - group[-1]["y"]))
    whole, seen = [], []
    for group in found:
        members = {id(line) for line in group}
        if not any(members <= other for other in seen):
            whole.append(group)
            seen.append(members)
    return whole


def vivid_colors(planes, x0, y0, x1, y1):
    """Rank The Saturated Colors In A Region, Most Colorful First."""
    w, wide = planes.width, x1 - x0 + 1
    spread = Counter()
    for y in range(y0, y1 + 1):
        spread.update(planes.chroma[y * w + x0 : y * w + x1 + 1])
    needed, seen, peak = max(8, wide // 2), 0, 0
    for value in range(255, -1, -1):
        seen += spread.get(value, 0)
        if seen >= needed:
            peak = value
            break
    if peak < 40:
        raise Unsure("No Saturated Curve Color Was Found In The Plot")
    floor = max(40, int(0.6 * peak))
    strong = _table(lambda v: v >= floor)
    exact, px = Counter(), planes.pixels
    for y in range(y0, y1 + 1):
        base = y * w + x0
        for x in _ones(planes.chroma[base : base + wide].translate(strong)):
            at = 3 * (base + x)
            exact[(px[at], px[at + 1], px[at + 2])] += 1
    bins = Counter()
    for shade, amount in exact.items():
        bins[tuple(v >> 4 for v in shade)] += amount
    ranked = []
    for key, amount in bins.items():
        if amount < max(8, wide // 4):
            continue
        inside = [(s, n) for s, n in exact.items() if tuple(v >> 4 for v in s) == key]
        center = [sum(s[c] * n for s, n in inside) / amount for c in range(3)]
        near = [
            (s, n)
            for s, n in exact.items()
            if all(abs(s[c] - center[c]) <= 20 for c in range(3))
        ]
        total = sum(n for _, n in near)
        shade, most = max(near, key=lambda item: item[1])
        if most * 2 < total:
            shade = tuple(round(sum(s[c] * n for s, n in near) / total) for c in range(3))
        if list(shade) not in [color for _, _, color in ranked]:
            ranked.append((max(center) - min(center), amount, list(shade)))
    if not ranked:
        raise Unsure("No Saturated Curve Color Was Found In The Plot")
    ranked.sort(key=lambda item: (-item[0], -item[1]))
    return [color for _, _, color in ranked[:3]]


def hue(shade):
    """Return The Hue Of A Color In Degrees, Or None For A Gray."""
    red, green, blue = shade
    high, low = max(shade), min(shade)
    if high == low:
        return None
    if high == red:
        turn = ((green - blue) / (high - low)) % 6
    elif high == green:
        turn = (blue - red) / (high - low) + 2
    else:
        turn = (red - green) / (high - low) + 4
    return 60 * turn


def ridge_columns(planes, y0, tall, shade):
    """Follow A Thin, Soft-Edged Line By The Most Colorful Pixel In Each Column.

    Exact Color Matching Misses A Line Too Thin To Hold Its Full Color In Every Column.
    Here A Column Counts When Its Most Colorful Pixel Shares The Line's Hue.
    """
    w, px = planes.width, planes.pixels
    band = planes.chroma[y0 * w : (y0 + tall) * w]
    wanted, least = hue(shade), max(40, 0.35 * (max(shade) - min(shade)))
    tables, columns = {}, []
    for x in range(w):
        strip = band[x::w]
        peak = max(strip)
        found = []
        if peak >= least and wanted is not None:
            at = 3 * ((y0 + strip.index(peak)) * w + x)
            tint = hue(px[at : at + 3])
            if tint is not None and min(abs(tint - wanted), 360 - abs(tint - wanted)) <= 25:
                floor = int(0.85 * peak)
                if floor not in tables:
                    tables[floor] = _table(lambda v, floor=floor: v >= floor)
                found = list(_ones(strip.translate(tables[floor])))
        columns.append(found)
    return columns


def trace(planes, group, color, tolerance):
    """Follow The Curve Between One Set Of Gridlines And Confirm It Fits Them.

    The Curve Is Searched Across The Whole Image Width, Because Labels Can Shorten The
    Gridlines. The Time Axis Runs From The Curve's First Column To Its Last.
    """
    w, h = planes.width, planes.height
    rows = [line["y"] for line in group]
    top, bottom = rows[0], rows[-1]
    left = int(statistics.median(line["left"] for line in group))
    right = int(statistics.median(line["right"] for line in group))
    extent = right - left + 1
    pad = max(3, round(0.02 * (bottom - top)))
    beyond = max(pad, int(0.6 * (bottom - top) / (len(rows) - 1)))
    y0, y1 = max(0, top - beyond), min(h - 1, bottom + beyond)
    tall = y1 - y0 + 1
    if color is None:
        choices = vivid_colors(
            planes, max(0, left - 3), max(0, top - pad), min(w - 1, right + 3), min(h - 1, bottom + pad)
        )
    else:
        choices = [list(color)]
    problem = None
    for shade in choices:
        for method in ("color match", "color ridge"):
            if method == "color match":
                columns = match_columns(planes.pixels, w, 0, y0, w, tall, shade, tolerance)
            else:
                columns = ridge_columns(planes, y0, tall, shade)
            hit = [x for x, found in enumerate(columns) if found]
            runs, begin, last = [], None, None
            for x in hit:
                if begin is None:
                    begin = last = x
                elif x - last - 1 <= max(2, w // 200):
                    last = x
                else:
                    runs.append((begin, last))
                    begin = last = x
            if begin is not None:
                runs.append((begin, last))
            first, final = max(runs, key=lambda r: r[1] - r[0], default=(0, -1))
            span = final - first + 1
            kept = [x for x in hit if first <= x <= final]
            shared = min(final, right) - max(first, left) + 1
            if shared < 0.85 * extent or len(kept) < 0.9 * span:
                share = max(0, min(100, round(100 * shared / extent)))
                problem = problem or Unsure(
                    f"The Curve Color Covers Only {share} Percent Of The Plot Width"
                )
                continue
            inside = {
                x: [y + y0 for y in columns[x] if top - pad <= y + y0 <= bottom + pad]
                for x in kept
            }
            # A selected-point marker or a tooltip fills far more rows than the line does.
            if sum(1 for x in kept if not inside[x]) > max(2, 0.02 * len(kept)):
                problem = problem or Unsure("The Curve Runs Outside The Detected Gridlines")
                break
            heights = [len(inside[x]) for x in kept if inside[x]]
            limit = max(4 * statistics.median(heights), 0.15 * (bottom - top)) if heights else 0
            traced = [x for x in kept if inside[x] and len(inside[x]) <= limit]
            if len(traced) < 0.9 * len(kept):
                problem = problem or Unsure(
                    "Something In The Curve's Color Covers Part Of The Plot"
                )
                continue
            notes = []
            if first - left > 0.05 * extent or right - final > 0.05 * extent:
                notes.append(
                    f"The Curve Spans Columns {first} To {final} But The Gridlines Span "
                    f"{left} To {right}. The Time Axis Follows The Curve. If The Curve "
                    "Is Cut Short In The Screenshot, Pass --plot."
                )
            return {
                "plot": [first, top, final, bottom],
                "color": shade,
                "gridlines": rows,
                "gridline_extent": [left, right],
                "theme": "dark" if group[0]["tone"] == "light" else "light",
                "trace": method,
                "rows": [
                    ((x - first) / (final - first), statistics.median(inside[x])) for x in traced
                ],
                "coverage": round(len(traced) / span, 3),
                "notes": notes,
            }
    raise problem or Unsure("No Saturated Curve Color Was Found In The Plot")


def find_chart(pixels, width, height, color=None, tolerance=20):
    """Locate One Retention Chart From Its Gridlines And Its Curve Color."""
    planes = Planes(pixels, width, height)
    groups = ladders(gridline_candidates(planes), width, height)
    if not groups:
        raise Unsure("Fewer Than Three Evenly Spaced Horizontal Gridlines Were Found")
    charts, problem = [], None
    for group in groups[:12]:
        if any(
            group[0]["y"] <= other["plot"][3] and group[-1]["y"] >= other["plot"][1]
            for other in charts
        ):
            continue
        try:
            charts.append(trace(planes, group, color, tolerance))
        except Unsure as exc:
            problem = problem or exc
    if not charts:
        raise problem
    if len(charts) > 1:
        boxes = " Or ".join(" ".join(map(str, found["plot"])) for found in charts)
        raise Unsure(f"More Than One Chart Was Found. Their Plot Rectangles Are {boxes}")
    return charts[0]


def auto_chart(pixels, width, height, a):
    """Read A Chart Without A Supplied Plot Rectangle."""
    try:
        found = find_chart(pixels, width, height, a.color, a.tolerance)
    except Unsure as exc:
        raise ValueError(
            f"Automatic Calibration Is Not Confident. {exc}. {BY_HAND} "
            "Cropping The Screenshot To The Chart Can Also Help."
        ) from exc
    left, top, right, bottom = found["plot"]
    low, high = min(a.top, a.bottom), max(a.top, a.bottom)
    samples = [
        (
            share * a.seconds,
            min(high, max(low, a.top + (a.bottom - a.top) * (y - top) / (bottom - top))),
        )
        for share, y in found["rows"]
    ]
    a.plot, a.color = found["plot"], found["color"]
    return samples, found["coverage"], found


def read_image(a):
    """Return Samples, Coverage, And The Calibration Used For A Chart Image."""
    if any(not 0 <= v <= 255 for v in a.color or ()) or not 0 <= a.tolerance <= 255:
        raise ValueError("Color Channels And Tolerance Must Be Between 0 And 255.")
    assumed = a.top is None or a.bottom is None
    a.top = 100.0 if a.top is None else a.top
    a.bottom = 0.0 if a.bottom is None else a.bottom
    if not (
        math.isfinite(a.seconds)
        and a.seconds > 0
        and math.isfinite(a.top)
        and math.isfinite(a.bottom)
        and a.top > a.bottom
    ):
        raise ValueError("Check Duration And Vertical Axis Bounds.")
    if not a.file.is_file():
        raise ValueError(f"No Image File At {a.file}.")
    given_plot, given_color = a.plot is not None, a.color is not None
    found = {}
    if given_plot:
        samples, coverage = chart(a)
    else:
        width, height = image_size(a.file)
        samples, coverage, found = auto_chart(decode(a.file), width, height, a)
    calibration = {
        "plot": list(a.plot),
        "plot_source": "supplied" if given_plot else "detected",
        "color": list(a.color),
        "color_source": "supplied" if given_color else "detected",
        "tolerance": a.tolerance,
        "axis_top": a.top,
        "axis_bottom": a.bottom,
        "axis_source": "assumed" if assumed else "supplied",
    }
    for key in ("theme", "gridlines", "gridline_extent", "trace"):
        if key in found:
            calibration[key] = found[key]
    if not (given_plot and given_color):
        print(calibration_note(calibration), file=sys.stderr)
    notes = found.get("notes", []) + axis_notes(
        found.get("gridlines", ()), assumed, samples[0][1]
    )
    return samples, coverage, calibration, notes


def axis_notes(gridlines, assumed, first):
    """Warn When The Vertical Axis Probably Does Not Run From 0 To 100 As Read."""
    notes = []
    parts = len(gridlines) - 1
    if assumed and parts > 0 and 100 % parts:
        notes.append(
            f"{parts + 1} Gridlines Split The Axis Into {parts} Equal Parts, Which Does "
            "Not Divide 0 To 100 Evenly. A Gridline May Be Missing Or The Axis May Not "
            "Run From 0 To 100. Check The Labels And Pass --top And --bottom."
        )
    if assumed and gridlines and not notes:
        notes.append(
            "The Axis Was Assumed To Run From 0 At The Bottom Gridline To 100 At The Top "
            "One. Check The Labels, Then Pass --top And --bottom To Confirm Or Correct It."
        )
    if not 90 <= first <= 110:
        notes.append(
            f"The Curve Starts At {number_text(first)} Percent. Retention Starts "
            "Near 100, So Check The Axis Bounds, The Plot Rectangle, And The Line Color."
        )
    return notes


def calibration_note(calibration):
    parts = []
    if calibration["plot_source"] == "detected":
        parts.append(
            "Detected Plot Rectangle {} {} {} {}".format(*calibration["plot"])
            + f" From {len(calibration['gridlines'])} Gridlines"
            + f" On A {calibration['theme'].title()} Theme"
        )
    if calibration["color_source"] == "detected":
        parts.append("Detected Line Color {} {} {}".format(*calibration["color"]))
    note = " And ".join(parts) + ". Check Each Against The Screenshot."
    if calibration["axis_source"] == "assumed":
        edge = "Gridline" if calibration["plot_source"] == "detected" else "Edge"
        note += (
            f" The Top {edge} Is Read As {number_text(calibration['axis_top'], 2)} "
            f"Percent And The Bottom {edge} As {number_text(calibration['axis_bottom'], 2)} "
            "Percent. Pass --top And --bottom When The Axis Labels Differ."
        )
    return note


# Practice Charts And The Self Test


def png_bytes(width, height, pixels):
    """Encode RGB Bytes As A PNG File Using Only The Standard Library."""

    def chunk(kind, body):
        check = zlib.crc32(kind + body) & 0xFFFFFFFF
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", check)

    row = 3 * width
    raw = b"".join(b"\x00" + pixels[y * row : (y + 1) * row] for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def practice_level(points, seconds, at):
    scaled = [(share * seconds, pct) for share, pct in points]
    return reading(scaled, [t for t, _ in scaled], min(max(at, 0.0), seconds))


def synthetic_chart(
    theme="dark", dashed=True, fill=False, scale=1, seconds=30.0, points=PRACTICE_CURVE
):
    """Draw A Practice Retention Chart And Return It With Its True Calibration."""
    s = scale
    width, height = 640 * s, 480 * s
    if theme == "dark":
        ground, grid, ink, line = (18, 18, 20), (58, 58, 64), (168, 170, 178), (64, 196, 255)
    else:
        ground, grid, ink, line = (255, 255, 255), (224, 227, 232), (96, 100, 110), (232, 62, 112)
    pixels = bytearray(bytes(ground) * (width * height))

    def blend(over, under, share):
        return bytes(round(share * a + (1 - share) * b) for a, b in zip(over, under))

    def block(x0, y0, x1, y1, color):
        for y in range(y0, y1):
            pixels[3 * (y * width + x0) : 3 * (y * width + x1)] = bytes(color) * (x1 - x0)

    left, right, top, bottom = 72 * s, 599 * s, 170 * s, 410 * s
    block(24 * s, 24 * s, 220 * s, 40 * s, ink)
    block(24 * s, 50 * s, 140 * s, 58 * s, blend(ink, ground, 0.5))
    block(0, 76 * s, width, 76 * s + s, grid)
    for tile in range(3):
        block((24 + 200 * tile) * s, 96 * s, (120 + 200 * tile) * s, 112 * s, ink)
        block((24 + 200 * tile) * s, 122 * s, (90 + 200 * tile) * s, 130 * s, grid)
    block(left, (bottom + 14 * s), left + 28 * s, bottom + 22 * s, ink)
    block(right - 28 * s, bottom + 14 * s, right, bottom + 22 * s, ink)
    block(0, 452 * s, width, 452 * s + s, grid)
    rows = [top + n * (bottom - top) // 4 for n in range(5)]
    grid_rows = set()
    for row in rows:
        block(24 * s, row - 4 * s, 56 * s, row + 4 * s, ink)
        for y in range(row - (s - 1) // 2, row + s // 2 + 1):
            grid_rows.add(y)
            for x in range(left, right + 1, 10 * s if dashed else right - left + 1):
                block(x, y, min(right + 1, x + (6 * s if dashed else right - left + 1)), y + 1, grid)

    def dash_on(x):
        return not dashed or (x - left) % (10 * s) < 6 * s

    def row_of(x):
        at = min(max((x - left) / (right - left), 0.0), 1.0) * seconds
        return top + (100 - practice_level(points, seconds, at)) / 100 * (bottom - top)

    half = 1.5 * s
    for x in range(left, right + 1):
        a, b = row_of(x - 0.5), row_of(x + 0.5)
        first, last = round(min(a, b) - half), round(max(a, b) + half)
        if fill:
            start, end = last + 2, bottom
            if end > start:
                veil = blend(line, ground, 0.16)
                for c in range(3):
                    pixels[
                        3 * (start * width + x) + c : 3 * (end * width + x) + c : 3 * width
                    ] = bytes([veil[c]]) * (end - start)
                if dash_on(x):
                    for y in grid_rows:
                        if start <= y < end:
                            at = 3 * (y * width + x)
                            pixels[at : at + 3] = blend(line, grid, 0.16)
        for y in range(first, last + 1):
            at = 3 * (y * width + x)
            pixels[at : at + 3] = bytes(line)
        for y in (first - 1, last + 1):
            at = 3 * (y * width + x)
            pixels[at : at + 3] = blend(line, pixels[at : at + 3], 0.5)
    return {
        "width": width,
        "height": height,
        "pixels": bytes(pixels),
        "plot": (left, top, right, bottom),
        "color": line,
        "seconds": seconds,
        "points": points,
    }


def practice_report(picture, pixels=None):
    """Read A Practice Chart Automatically And Return Its Largest Errors."""
    a = argparse.Namespace(
        color=None, tolerance=20, top=100.0, bottom=0.0, seconds=picture["seconds"]
    )
    samples, _, found = auto_chart(
        picture["pixels"] if pixels is None else pixels, picture["width"], picture["height"], a
    )
    times = [t for t, _ in samples]
    slack = edge_slack(times)
    worst = 0.0
    for second in FIXED_SECONDS:
        if second <= picture["seconds"]:
            read = reading(samples, times, second, slack)
            if read is None:
                raise ValueError(f"No Reading At {second} Seconds.")
            true = practice_level(picture["points"], picture["seconds"], second)
            worst = max(worst, abs(read - true))
    truth = [(share * picture["seconds"], pct) for share, pct in picture["points"]]
    return {
        "plot": found["plot"],
        "color": found["color"],
        "worst_points": worst,
        "average_gap": abs(area_average(samples) - area_average(truth)),
        "box_gap": max(abs(x - y) for x, y in zip(found["plot"], picture["plot"])),
    }


def selftest():
    """Draw Practice Charts, Read Them Back, And Print Whether Each Reading Holds."""
    cases = (
        ("Dark Theme, Dashed Gridlines, Shaded Curve", dict(theme="dark", dashed=True, fill=True)),
        ("Light Theme, Solid Gridlines", dict(theme="light", dashed=False, fill=False)),
    )
    passed = True
    decoded = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
    with tempfile.TemporaryDirectory(prefix="retention selftest ") as folder:
        for name, options in cases:
            picture = synthetic_chart(**options)
            routes = [("Drawn In Memory", None)]
            if decoded:
                path = Path(folder) / (options["theme"] + ".png")
                path.write_bytes(png_bytes(picture["width"], picture["height"], picture["pixels"]))
                routes.append(("Saved As PNG And Decoded With FFmpeg", path))
            for route, path in routes:
                try:
                    pixels = None
                    if path is not None:
                        if image_size(path) != (picture["width"], picture["height"]):
                            raise ValueError("The Decoded Size Differs From The Drawing.")
                        pixels = decode(path)
                        if pixels != picture["pixels"]:
                            raise ValueError("The Decoded Pixels Differ From The Drawing.")
                    result = practice_report(picture, pixels)
                    good = (
                        result["worst_points"] <= SELFTEST_POINTS
                        and result["average_gap"] <= SELFTEST_SECONDS
                        and result["box_gap"] <= 3
                    )
                    detail = (
                        "Plot {} {} {} {}, ".format(*result["plot"])
                        + "Color {} {} {}, ".format(*result["color"])
                        + f"Largest Reading Error {result['worst_points']:.2f} Points, "
                        + f"Average Watch Error {result['average_gap']:.2f} Seconds"
                    )
                except ValueError as exc:
                    good, detail = False, str(exc)
                passed = passed and good
                print(f"{name}, {route}: {detail}. {'Pass' if good else 'Fail'}.")
    if not decoded:
        print(
            "FFmpeg And FFprobe Were Not Found, So The Saved PNG Check Was Skipped. "
            "Image Mode Needs Both On PATH."
        )
    print(
        f"Self Test {'Passed' if passed else 'Failed'}{'' if decoded else ' In Memory Only'}. "
        "The Tolerance Is "
        f"{SELFTEST_POINTS} Retention Points At Each Fixed Second And "
        f"{SELFTEST_SECONDS} Seconds Of Area-Based Average Watch Time."
    )
    return 0 if passed else 1


# Command Line


def build_parser():
    parser = DeskParser(description=__doc__)
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="Draw Practice Charts In Pure Python, Read Them Back, And Report The Error",
    )
    cmds = parser.add_subparsers(dest="cmd", title="Commands", metavar="{csv,image}")
    about = {
        "csv": "Read A CSV With seconds And retention_pct Columns",
        "image": "Read The Curve From A Chart Screenshot",
    }
    for cmd in ("csv", "image"):
        sub = cmds.add_parser(cmd, help=about[cmd], description=about[cmd])
        sub.add_argument("file", type=Path, help="The CSV Or Image File")
        sub.add_argument(
            "--interval",
            type=float,
            default=3,
            help="Minimum Measured Interval In Seconds",
        )
        sub.add_argument(
            "--at",
            type=float,
            nargs="+",
            metavar="SECONDS",
            help="Seconds To Read Instead Of The Fixed List "
            + " ".join(map(str, FIXED_SECONDS)),
        )
        sub.add_argument(
            "--reported-average",
            type=clock,
            metavar="SECONDS",
            help="Average Watch Time Shown By The App, To Check Against The Area Under The Curve",
        )
        sub.add_argument(
            "--average-tolerance",
            type=float,
            default=AVERAGE_TOLERANCE,
            metavar="SECONDS",
            help=f"Largest Accepted Gap From The Reported Average. Default {AVERAGE_TOLERANCE}",
        )
        sub.add_argument(
            "--count",
            type=int,
            default=LIST_LENGTH,
            help=f"How Many Steep Drops And Flat Stretches To List. Default {LIST_LENGTH}",
        )
        sub.add_argument(
            "--output",
            type=Path,
            metavar="FILE",
            help="Also Save The Report With Its Curve To A New JSON File",
        )
        if cmd == "csv":
            sub.add_argument(
                "--runtime",
                type=clock,
                metavar="SECONDS",
                help="Video Runtime When It Is Longer Than The Last CSV Row",
            )
        else:
            sub.add_argument(
                "--plot",
                type=int,
                nargs=4,
                metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
                help="Plot Rectangle In Image Pixels. Found From The Gridlines When Omitted",
            )
            sub.add_argument(
                "--color",
                type=int,
                nargs=3,
                metavar=("RED", "GREEN", "BLUE"),
                help="Line Color. Found From The Dominant Saturated Color When Omitted",
            )
            sub.add_argument(
                "--seconds", type=float, required=True, help="Video Runtime In Seconds"
            )
            sub.add_argument(
                "--top", type=float, help="Percent At The Top Of The Plot. Default 100"
            )
            sub.add_argument(
                "--bottom", type=float, help="Percent At The Bottom Of The Plot. Default 0"
            )
            sub.add_argument(
                "--tolerance", type=int, default=20, help="Color Match Range Per Channel"
            )
    return parser


def run(argv=None):
    guard_streams()
    parser = build_parser()
    a = parser.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.cmd:
        parser.error("Choose The csv Or image Command, Or Pass --selftest.")
    try:
        if a.cmd == "image":
            samples, coverage, calibration, notes = read_image(a)
            runtime = a.seconds
        else:
            if not a.file.is_file():
                raise ValueError(f"No CSV File At {a.file}.")
            samples, coverage, calibration, notes = table(a.file), None, None, []
            if samples and max(pct for _, pct in samples) <= 1.5:
                notes.append(
                    "Every Value Is 1.5 Or Less. Retention Is Read In Percent, So Multiply "
                    "Fractions By 100."
                )
            runtime = a.runtime
        report, curve = measure(samples, coverage, a, runtime, calibration, notes)
        if a.output:
            write_new(a.output, tidy_json(dict(report, curve=curve)) + "\n")
            print(f"Saved The Report With Its Curve To {a.output}", file=sys.stderr)
        for warning in report["warnings"]:
            print(f"Warning: {warning}", file=sys.stderr)
        print(tidy_json(report, ascii_only=True))
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as exc:
        parser.exit(1, f"{exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(run())
