"""Measure Approximate Translation Of A Selected Detail Across A Short Reference Shot."""

import argparse
import json
import math
import subprocess
from pathlib import Path


def follow(frames, w, h, cx, cy, patch, search):
    result = [
        {
            "frame": 0,
            "x": round(cx / (w - 1), 4),
            "y": round(cy / (h - 1), 4),
            "match": None,
        }
    ]
    stride = 2

    def feature(frame, x, y):
        pix = [
            frame[(y + dy) * w + x + dx]
            for dy in range(-patch, patch + 1, stride)
            for dx in range(-patch, patch + 1, stride)
        ]
        mean = sum(pix) / len(pix)
        return [p - mean for p in pix]

    for index in range(1, len(frames)):
        old = feature(frames[index - 1], cx, cy)
        energy = sum(v * v for v in old)
        best = None
        if energy >= len(old) * 9:
            for y in range(max(patch, cy - search), min(h - patch, cy + search + 1)):
                for x in range(
                    max(patch, cx - search), min(w - patch, cx + search + 1)
                ):
                    cur = feature(frames[index], x, y)
                    den = math.sqrt(energy * sum(v * v for v in cur))
                    if den == 0:
                        continue
                    score = sum(a * b for a, b in zip(old, cur)) / den
                    item = (score, -((x - cx) ** 2 + (y - cy) ** 2), x, y)
                    if best is None or item > best:
                        best = item
        if best is None or best[0] < 0.5:
            result.append({"frame": index, "status": "lost"})
            break
        cx, cy = best[2:]
        result.append(
            {
                "frame": index,
                "x": round(cx / (w - 1), 4),
                "y": round(cy / (h - 1), 4),
                "match": round(best[0], 4),
            }
        )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source", type=Path)
    p.add_argument(
        "--point",
        nargs=2,
        type=float,
        required=True,
        metavar=("X", "Y"),
        help="Normalized Coordinates From 0 To 1",
    )
    p.add_argument("--start", type=float, default=0)
    p.add_argument("--seconds", type=float, default=3)
    p.add_argument("--fps", type=int, default=6)
    p.add_argument("--search", type=int, default=5)
    a = p.parse_args()
    if (
        not 0 < a.seconds <= 30
        or not 1 <= a.fps <= 12
        or not 1 <= a.search <= 12
        or not math.isfinite(a.start)
        or a.start < 0
    ):
        p.error("Use Up To 30 Seconds, 1 To 12 FPS, And A Search Radius Of 1 To 12.")
    if not all(0 <= v <= 1 for v in a.point):
        p.error("Use Normalized Point Coordinates From 0 To 1.")
    try:
        w, h, patch = 128, 96, 5
        args = [
            "ffmpeg",
            "-v",
            "error",
            "-ss",
            str(a.start),
            "-i",
            str(a.source),
            "-t",
            str(a.seconds),
            "-vf",
            f"fps={a.fps},scale={w}:{h},format=gray",
            "-an",
            "-pix_fmt",
            "gray",
            "-f",
            "rawvideo",
            "-",
        ]
        raw = subprocess.check_output(args)
        size = w * h
        frames = [
            raw[i : i + size] for i in range(0, len(raw), size) if len(raw) - i >= size
        ]
        if len(frames) < 2:
            raise ValueError("Need Two Or More Decoded Frames.")
        cx, cy = (round(n * (d - 1)) for n, d in zip(a.point, (w, h)))
        if not (patch <= cx < w - patch and patch <= cy < h - patch):
            raise ValueError("Choose A Detail Away From The Outside Edge.")
        points = follow(frames, w, h, cx, cy, patch, a.search)
        for pt in points:
            pt["seconds"] = round(a.start + pt["frame"] / a.fps, 4)
        print(
            json.dumps({"measure": "detail_translation", "samples": points}, indent=2)
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        p.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
