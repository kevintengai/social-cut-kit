"""Check A Supplied Master Against An Edit Without Producing A New Video."""

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path
import re
import subprocess

from timeline import EditError, load, prepare


def read_master(path, timeline):
    run = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    info = json.loads(run.stdout)
    video = next(
        (
            s
            for s in info["streams"]
            if s["codec_type"] == "video"
            and not s.get("disposition", {}).get("attached_pic")
        ),
        None,
    )
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if video is None:
        raise ValueError("No Picture Stream Was Found.")
    rate = str(video.get("avg_frame_rate", "0/1"))
    fps = float(Fraction(rate)) if rate not in ("0/0", "N/A") else 0
    length = float(info["format"]["duration"])
    if not math.isfinite(length) or length <= 0:
        raise ValueError("No Finite Master Duration Was Available.")
    issues = []
    if timeline:
        m = prepare(load(timeline), timeline.parent)
        if (video["width"], video["height"]) != (m["width"], m["height"]):
            issues.append("Picture Size Differs From Timeline")
        if abs(fps - m["fps"]) > 0.02:
            issues.append("Frame Rate Differs From Timeline")
        if abs(length - m["duration"]) > max(0.08, 2 / m["fps"]):
            issues.append("Master Duration Differs From Timeline")
        if audio is None:
            issues.append("Missing Timeline Audio Stream")
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-xerror",
        "-i",
        str(path),
        "-map",
        "0:V:0",
        "-vf",
        "blackdetect=d=0.5:pix_th=0.10",
    ]
    if audio:
        command.extend(
            ["-map", "0:a:0", "-af", "silencedetect=n=-50dB:d=0.5,volumedetect"]
        )
    command.extend(["-f", "null", "-"])
    log = subprocess.run(command, check=True, capture_output=True, text=True).stderr

    def events(pattern):
        return [float(x) for x in re.findall(pattern, log)]

    return {
        "dimensions": [video["width"], video["height"]],
        "fps": round(fps, 4),
        "seconds": length,
        "audio_channels": audio["channels"] if audio else 0,
        "peak_dbfs": next(iter(events(r"max_volume:\s*([-\d.]+) dB")), None),
        "silence_start_seconds": events(r"silence_start:\s*([\d.]+)"),
        "black_ranges": [
            [float(a), float(b)]
            for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", log)
        ],
        "mismatches": issues,
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("master", type=Path)
    cli.add_argument("--timeline", type=Path)
    a = cli.parse_args()
    try:
        obj = read_master(
            a.master.resolve(strict=True),
            a.timeline.resolve(strict=True) if a.timeline else None,
        )
        print(json.dumps(obj, indent=2))
        if obj["mismatches"]:
            raise SystemExit(2)
    except (
        EditError,
        OSError,
        KeyError,
        ValueError,
        subprocess.CalledProcessError,
    ) as exc:
        cli.exit(1, f"{exc}\n")
