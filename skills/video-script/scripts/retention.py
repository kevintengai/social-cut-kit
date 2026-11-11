"""Measure Audience Retention From A CSV Or A Calibrated Chart Image."""

import argparse
import csv
import json
import math
import statistics
import subprocess
from pathlib import Path


def chart(a):
    left, top, right, bottom = a.plot
    if min(left, top) < 0 or right <= left or bottom <= top:
        raise ValueError("Use A Positive Plot Rectangle In Image Coordinates.")
    if any(not 0 <= v <= 255 for v in a.color) or not 0 <= a.tolerance <= 255:
        raise ValueError("Color Channels And Tolerance Must Be Between 0 And 255.")
    if not (
        math.isfinite(a.seconds)
        and a.seconds > 0
        and math.isfinite(a.top)
        and math.isfinite(a.bottom)
        and a.top > a.bottom
    ):
        raise ValueError("Check Duration And Vertical Axis Bounds.")
    size = subprocess.check_output(
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
            str(a.file),
        ],
        text=True,
    )
    iw, ih = map(int, size.strip().split(",")[:2])
    if right >= iw or bottom >= ih:
        raise ValueError("The Plot Extends Outside The Image.")
    w, h = right - left + 1, bottom - top + 1
    buf = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(a.file),
            "-vf",
            f"format=rgb24,crop={w}:{h}:{left}:{top}",
            "-frames:v",
            "1",
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "-",
        ]
    )
    if len(buf) != w * h * 3:
        raise ValueError("Incomplete Input Image.")
    samples = []
    for x in range(w):
        hits = []
        for y in range(h):
            pos = 3 * (y * w + x)
            if all(abs(buf[pos + c] - a.color[c]) <= a.tolerance for c in range(3)):
                hits.append(y)
        if hits:
            pct = a.top + (a.bottom - a.top) * statistics.median(hits) / (h - 1)
            samples.append((x * a.seconds / (w - 1), pct))
    if len(samples) < 2:
        raise ValueError("Too Few Line Pixels. Check The Plot And Line Color.")
    return samples, round(len(samples) / w, 3)


def table(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [(float(row["seconds"]), float(row["retention_pct"])) for row in reader]


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    cmds = parser.add_subparsers(dest="cmd", required=True)
    for cmd in ("csv", "image"):
        sub = cmds.add_parser(cmd)
        sub.add_argument("file", type=Path)
        sub.add_argument(
            "--interval",
            type=float,
            default=3,
            help="Minimum Measured Interval In Seconds",
        )
        if cmd == "image":
            sub.add_argument("--plot", type=int, nargs=4, required=True)
            sub.add_argument("--color", type=int, nargs=3, required=True)
            sub.add_argument("--seconds", type=float, required=True)
            sub.add_argument("--top", type=float, required=True)
            sub.add_argument("--bottom", type=float, required=True)
            sub.add_argument("--tolerance", type=int, default=20)
    a = parser.parse_args()
    try:
        samples, coverage = chart(a) if a.cmd == "image" else (table(a.file), None)
        if len(samples) < 2 or any(
            not math.isfinite(v) or v < 0 for pair in samples for v in pair
        ):
            raise ValueError("Supply At Least Two Finite Nonnegative Measurements.")
        if any(b[0] <= c[0] for c, b in zip(samples, samples[1:])):
            raise ValueError("Measurement Times Must Increase.")
        if a.interval <= 0 or not math.isfinite(a.interval):
            raise ValueError("Use A Positive Comparison Interval.")
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
        print(
            json.dumps(
                {
                    "samples": len(samples),
                    "chart_coverage": coverage,
                    "first_pct": round(samples[0][1], 2),
                    "last_pct": round(samples[-1][1], 2),
                    "largest_drop": drop if drop and drop["delta_points"] < 0 else None,
                    "largest_lift": lift if lift and lift["delta_points"] > 0 else None,
                },
                indent=2,
            )
        )
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    run()
