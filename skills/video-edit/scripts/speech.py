"""Prepare Timed Speech, Map Captions To A Cut, And Align Two Recordings."""

import argparse
from array import array
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
from tempfile import TemporaryDirectory


def stamp(raw):
    parts = raw.replace(",", ".").split(":")
    return sum(float(part) * (60**i) for i, part in enumerate(reversed(parts)))


def load_words(file):
    if file.suffix.lower() in (".srt", ".vtt"):
        words = []
        timing = re.compile(r"([\d:]+[.,]\d+)\s+-->\s+([\d:]+[.,]\d+)")
        for block in re.split(r"\n\s*\n", file.read_text(encoding="utf-8-sig").strip()):
            match = timing.search(block)
            if match:
                body = block[match.end() :].split("\n", 1)
                if len(body) > 1:
                    words.append(
                        (stamp(match[1]), stamp(match[2]), " ".join(body[1].split()))
                    )
    else:
        raw = json.loads(file.read_text(encoding="utf-8-sig"))
        if isinstance(raw, list):
            entries = raw
        elif "segments" in raw:
            entries = [
                w
                for segment in raw["segments"]
                for w in (segment.get("words") or [segment])
            ]
        else:
            entries = raw["words"]
        words = [
            (
                float(w["start"]),
                float(w["end"]),
                (w.get("word") or w.get("text") or "").strip(),
            )
            for w in entries
        ]
    if not words or any(
        not math.isfinite(s) or not math.isfinite(e) or s < 0 or e <= s or not t
        for s, e, t in words
    ):
        raise ValueError("Expected Nonempty Timed Words Or Subtitle Cues.")
    return sorted(words)


def project(words, timeline, source):
    if source not in timeline["assets"]:
        raise ValueError(f"Unknown Timeline Asset: {source}")
    fps = float(timeline["canvas"]["fps"])
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("Expected A Positive Frame Rate.")
    at = 0.0
    pieces = []
    clipped = 0
    for cut, shot in enumerate(timeline["shots"]):
        lo = float(shot["in"]) - float(shot.get("lead", 0))
        hi = float(shot["out"]) + float(shot.get("tail", 0))
        speed = float(shot.get("speed", 1))
        if not all(math.isfinite(x) for x in (lo, hi, speed)) or hi <= lo or speed <= 0:
            raise ValueError("Invalid Shot Trim Or Speed.")
        length = math.floor(((hi - lo) / speed) * fps + 0.5) / fps
        if shot["asset"] == source:
            for start, end, text in words:
                if start < hi and end > lo:
                    if start < lo - 0.0001 or end > hi + 0.0001:
                        clipped += 1
                        continue
                    s = at + max(0.0, (start - lo) / speed)
                    e = at + min(length, (end - lo) / speed)
                    if e > s:
                        pieces.append((s, e, text, cut))
        at += length
    return pieces, clipped


def captions(words):
    cues, active = [], []

    def flush():
        if active:
            cues.append(
                {
                    "at": round(active[0][0], 3),
                    "end": round(max(w[1] for w in active), 3),
                    "text": " ".join(w[2] for w in active),
                    "position": "bottom",
                }
            )
            active.clear()

    for word in words:
        if active and (
            word[3] != active[-1][3]
            or word[0] - active[-1][1] > 0.4
            or word[1] - active[0][0] > 3
            or sum(len(w[2]) + 1 for w in active) + len(word[2]) > 44
        ):
            flush()
        active.append(word)
        if word[2].endswith((".", "?", "!")):
            flush()
    flush()
    return cues


def save(path, result):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def envelope(path, seconds):
    raw = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(path),
            "-vn",
            "-t",
            str(seconds),
            "-ac",
            "1",
            "-ar",
            "4000",
            "-f",
            "s16le",
            "pipe:1",
        ]
    )
    pcm = array("h")
    pcm.frombytes(raw)
    if sys.byteorder != "little":
        pcm.byteswap()
    # A 10 ms peak envelope is used only for analysis. Original media is never changed.
    return [
        math.log1p(max(abs(v) for v in pcm[i : i + 40]))
        for i in range(0, len(pcm) - 39, 40)
    ]


def sync(a):
    if not 1 <= a.seconds <= 300 or not 0 <= a.lag <= min(30, a.seconds / 2):
        raise ValueError(
            "Use A 1 To 300 Second Sample And A Lag At Most Half Its Length, Up To 30 Seconds."
        )
    x, y = (envelope(p, a.seconds) for p in (a.primary, a.secondary))
    if min(len(x), len(y)) < 50:
        raise ValueError("At Least Half A Second Of Overlapping Audio Is Needed.")
    candidates = []
    for delta in range(-round(a.lag * 100), round(a.lag * 100) + 1):
        s, t = max(-delta, 0), max(delta, 0)
        size = min(len(x) - s, len(y) - t)
        if size < max(50, min(len(x), len(y)) // 2):
            continue
        a1, a2 = x[s : s + size], y[t : t + size]
        m1, m2 = statistics.fmean(a1), statistics.fmean(a2)
        den = math.sqrt(sum((v - m1) ** 2 for v in a1) * sum((v - m2) ** 2 for v in a2))
        if den > 0.001:
            candidates.append(
                (sum((v - m1) * (w - m2) for v, w in zip(a1, a2)) / den, delta)
            )
    if not candidates:
        raise ValueError("Neither Track Supplied A Distinct Alignment Signal.")
    score, lag = max(candidates)
    others = [c for c, d in candidates if abs(d - lag) >= 10]
    print(
        json.dumps(
            {
                "secondary_event_later_by_seconds": lag / 100,
                "correlation": round(score, 4),
                "next_distinct_correlation": round(max(others), 4) if others else None,
                "resolution_seconds": 0.01,
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    cmd = parser.add_subparsers(dest="cmd", required=True)
    trans = cmd.add_parser(
        "transcribe", help="Run A Separately Installed Local Whisper CLI"
    )
    trans.add_argument("source", type=Path)
    trans.add_argument("output", type=Path)
    trans.add_argument("--model", default="base")
    trans.add_argument("--language")
    trans.add_argument(
        "--backend", choices=("whisper-cli", "faster-whisper"), default="whisper-cli"
    )
    trans.add_argument("--engine", default="whisper")
    mapping = cmd.add_parser(
        "captions", help="Map A Word Transcript Or SRT/VTT To Timeline Shots"
    )
    mapping.add_argument("transcript", type=Path)
    mapping.add_argument("timeline", type=Path)
    mapping.add_argument("--asset", required=True)
    mapping.add_argument("--output", required=True, type=Path)
    mapping.add_argument(
        "--with-timeline",
        action="store_true",
        help="Append Cues To A New Editable Timeline",
    )
    align = cmd.add_parser(
        "sync", help="Find The Offset Between Camera And External Audio"
    )
    align.add_argument("primary", type=Path)
    align.add_argument("secondary", type=Path)
    align.add_argument("--seconds", type=float, default=30)
    align.add_argument("--lag", type=float, default=5)
    level = cmd.add_parser(
        "levels", help="Measure Source Audio Level And Available Gain Headroom"
    )
    level.add_argument("source", type=Path)
    a = parser.parse_args()
    try:
        if a.cmd == "transcribe":
            if a.output.exists():
                raise FileExistsError(a.output)
            src = a.source.resolve(strict=True)
            if a.backend == "faster-whisper":
                try:
                    from faster_whisper import WhisperModel
                except ImportError as exc:
                    raise ValueError(
                        "Install faster-whisper In This Python Environment Or Select The Whisper CLI."
                    ) from exc
                model = WhisperModel(a.model, device="cpu", compute_type="int8")
                segments, _ = model.transcribe(
                    str(src), language=a.language, word_timestamps=True
                )
                result = [
                    (w.start, w.end, w.word.strip())
                    for segment in segments
                    for w in segment.words or []
                    if w.word.strip() and w.end > w.start
                ]
            else:
                with TemporaryDirectory() as td:
                    args = [
                        a.engine,
                        str(src),
                        "--model",
                        a.model,
                        "--output_format",
                        "json",
                        "--word_timestamps",
                        "True",
                        "--output_dir",
                        td,
                    ]
                    if a.language:
                        args.extend(["--language", a.language])
                    subprocess.run(args, check=True)
                    result = load_words(Path(td) / (a.source.stem + ".json"))
            if not result:
                raise ValueError("No Timed Speech Found.")
            save(
                a.output,
                {"words": [{"start": s, "end": e, "text": t} for s, e, t in result]},
            )
        elif a.cmd == "captions":
            timeline = json.loads(a.timeline.read_text(encoding="utf-8-sig"))
            mapped, clipped = project(load_words(a.transcript), timeline, a.asset)
            cues = captions(mapped)
            if not cues:
                raise ValueError(
                    "No Complete Speech Units Fall Inside This Asset's Cuts."
                )
            if a.with_timeline:
                for asset in timeline["assets"].values():
                    path = (a.timeline.resolve().parent / asset["path"]).resolve()
                    try:
                        asset["path"] = os.path.relpath(path, a.output.resolve().parent)
                    except ValueError:
                        asset["path"] = str(path)
                timeline["captions"] = sorted(
                    timeline.get("captions", []) + cues, key=lambda c: c["at"]
                )
            save(a.output, timeline if a.with_timeline else cues)
            print(
                json.dumps(
                    {"cues": len(cues), "speech_units_cut_at_boundaries": clipped}
                )
            )
        elif a.cmd == "sync":
            sync(a)
        else:
            proc = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-nostats",
                    "-i",
                    str(a.source),
                    "-vn",
                    "-af",
                    "volumedetect",
                    "-f",
                    "null",
                    "-",
                ],
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            vals = dict(
                re.findall(r"(mean_volume|max_volume):\s+([-\d.]+) dB", proc.stderr)
            )
            if "max_volume" not in vals:
                raise ValueError("Could Not Read Audio Level Measurements.")
            print(
                json.dumps(
                    {
                        "mean_dbfs": float(vals["mean_volume"]),
                        "peak_dbfs": float(vals["max_volume"]),
                        "gain_available_to_minus_1_dbfs": round(
                            -1 - float(vals["max_volume"]), 2
                        ),
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
    main()
