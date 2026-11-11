#!/usr/bin/env python3
"""Convert One Untouched Source Clip Into A Standard H.264 Working Copy For Review.

A Working Copy Is A Converted Copy Of Raw Footage, Not A Cut. It Exists So The Browser Editor And Remotion
Can Play A Source They Cannot Decode, Such As 4K HEVC HDR Phone Footage. It Is Still A Video File, So The
Conversion Runs Only With The Flag That Records The Owner's Agreement. The Original File Is Only Read.
"""

import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from media import TONE_FILTERS, available_filters, decimal, tone_filters
from timeline import EditError, binary, frame_total, picture_info, probe, publish_file

AGREEMENT = "--owner-agreed-working-copy"
LONG_SIDE = 1920
REFUSAL = ("Ask The Owner Before Making A Working Copy. A Working Copy Is A Video File, So This Command Runs "
           f"Only With {AGREEMENT} After The Owner Agrees To A Working Copy Of This Source. Use --plan Or "
           "--check To Inspect The Conversion Without Writing Anything.")


def even(value):
    return max(2, 2 * math.floor(value / 2 + 0.5))


def working_size(shown, long_side=LONG_SIDE):
    """The Displayed Picture Fitted Inside The Long Side, With Even Dimensions And No Enlargement."""
    scale = min(1, long_side / max(shown))
    return [min(even(side * scale), max(2, 2 * (side // 2))) for side in shown]


def conversion(meta, long_side=LONG_SIDE):
    """The Picture Filter Chain And Encoder Arguments For One Probed Source. Nothing Is Run."""
    video, audio, info = meta.get("video"), meta.get("audio"), meta.get("picture") or picture_info(meta.get("video"))
    if not video or not info or not info.get("displayed_size"):
        raise EditError("A Working Copy Needs A Source With A Picture Stream.")
    if re.search(r"image2|_pipe", meta.get("format") or ""):
        raise EditError("A Still Image Needs No Working Copy. Convert It To PNG Or JPEG Instead.")
    if info["rotation"] % 90:
        raise EditError(f"The Source Has A {info['rotation']} Degree Display Rotation. Only Right-Angle Rotations "
                        "Can Be Stored Upright.")
    if (info.get("dolby_vision") or {}).get("profile") == 5 and not info["hdr"]:
        raise EditError("The Source Is Dolby Vision Profile 5 Without A Standard Base Layer. The Kit Cannot Convert "
                        "Its Colors. Use A Version Recorded Or Converted As HLG, HDR10, Or SDR.")
    if type(long_side) is not int or not 320 <= long_side <= 8192:
        raise EditError("Choose A Long Side Between 320 And 8192 Pixels.")
    width, height = working_size(info["displayed_size"], long_side)
    # FFmpeg Turns Rotated Frames Upright Before Any Filter Runs. The Order Matches The Composition Graph:
    # Scale The Displayed Picture, Then Apply The Single HDR Conversion.
    tone = tone_filters(video)
    chain = f"scale={width}:{height},setsar=1,{tone}format=yuv420p"
    rate = info.get("frame_rate") or 30
    picture = ["-map", f"0:{video['index']}", "-filter:v", chain, "-fps_mode", "passthrough",
               "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
               "-g", str(max(1, math.floor(rate + 0.5)))]
    if tone:
        picture += ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]
    notes = []
    if audio:
        codec = str(audio.get("codec_name") or "")
        # No Filter Touches The Sound, So Its Level, Channels, And Sample Rate Stay As Recorded.
        if codec == "aac":
            sound, handled = ["-map", f"0:{audio['index']}", "-c:a", "copy"], "copied"
        else:
            sound, handled = ["-map", f"0:{audio['index']}", "-c:a", "aac", "-b:a", "256k"], "encoded"
            notes.append(f"The Sound Is {codec or 'An Unknown Codec'}, Which Browsers Play Unreliably In An MP4 File, "
                         "So It Is Encoded As AAC With No Filter And No Level Change.")
    else:
        sound, handled = ["-an"], "none"
    if info["hdr"]:
        notes.append("The Picture Carries The Kit's Single HDR Conversion, The Same One Check, Still, And Render "
                     "Apply To The Original.")
    elif info.get("color_primaries") == "bt2020":
        notes.append("The Source Has bt2020 Primaries Without A PQ Or HLG Transfer. Its Colors Are Left Unconverted.")
    if info["rotation"]:
        notes.append(f"The Source Is Stored With A {info['rotation']} Degree Display Rotation. The Working Copy Is "
                     "Stored Upright.")
    return {"filter": chain, "picture": picture, "sound": sound, "sound_handling": handled,
            "size": [width, height], "tone_mapped": bool(tone), "frame_rate": rate, "notes": notes}


def command(source, name, recipe, seconds=None):
    """The Complete FFmpeg Command. A Missing Output Name Selects A Null Sink That Writes Nothing."""
    start = [binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-progress", "pipe:1",
             "-i", str(source)]
    limit = ["-t", decimal(seconds)] if seconds else []
    if name is None:
        return start + recipe["picture"][:6] + ["-an", *limit, "-f", "null", "-"]
    return (start + recipe["picture"] + recipe["sound"] + limit +
            ["-map_metadata", "-1", "-map_chapters", "-1", "-movflags", "+faststart", name])


def require_filters(recipe):
    missing = [name for name in TONE_FILTERS if name not in available_filters()] if recipe["tone_mapped"] else []
    if missing:
        raise EditError(f"This FFmpeg Build Lacks The {' And '.join(missing)} Filter{'s' if len(missing) > 1 else ''} "
                        "Needed To Convert HDR Footage To Standard Dynamic Range. Install A Build That Includes "
                        "zscale (libzimg) And tonemap.")


def targets(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_file():
        raise EditError(f"Missing Source {source}.")
    if output.suffix.lower() != ".mp4":
        raise EditError("Choose An MP4 Output Filename.")
    if output == source:
        raise EditError("The Working Copy Must Be A New File. The Original Is Never Replaced.")
    if output.exists():
        raise EditError(f"Output Already Exists {output}.")
    if not output.parent.is_dir():
        raise EditError(f"Output Folder Does Not Exist {output.parent}.")
    return source, output


def frames_done(text):
    found = re.findall(r"^frame=\s*(\d+)\s*$", text or "", re.MULTILINE)
    return int(found[-1]) if found else None


def verify(original, made, recipe):
    """Refuse A Result Whose Size, Duration, Or Frame Count Disagrees With Its Original."""
    shown = (made.get("picture") or {}).get("displayed_size")
    if not made.get("video") or shown != recipe["size"]:
        raise EditError("The Working Copy Picture Size Failed Verification.")
    a, b = original.get("duration"), made.get("duration")
    if a is not None and (b is None or abs(a - b) > max(0.05, 1 / recipe["frame_rate"])):
        raise EditError("The Working Copy Duration Does Not Match Its Original.")
    a, b = frame_total(original.get("video")), frame_total(made.get("video"))
    if a is not None and b is not None and abs(a - b) > 1:
        raise EditError(f"The Working Copy Has {b} Frames And Its Original Has {a}.")


def summary(source, output, meta, recipe):
    info = meta["picture"]
    return {"command": "working-copy", "source": str(source), "output": str(output),
            "displayed_size": info["displayed_size"], "working_size": recipe["size"],
            "frame_rate": recipe["frame_rate"], "tone_mapped": recipe["tone_mapped"],
            "sound": recipe["sound_handling"], "filter": recipe["filter"], "notes": recipe["notes"]}


def make(source, output, long_side=LONG_SIDE, agreed=False, plan=False, check=False, seconds=None):
    """Plan, Check, Or Write One Working Copy. Only The Agreed Conversion Writes A File."""
    if seconds is not None and (not check or not 0 < seconds <= 86400):
        raise EditError("Use --seconds Together With --check, With A Length Above 0.")
    if not (agreed or plan or check):
        raise EditError(REFUSAL)
    source, output = targets(source, output)
    meta = probe(source)
    recipe = conversion(meta, long_side)
    report = summary(source, output, meta, recipe)
    if plan:
        report.update(wrote="Nothing. This Is The Planned Command.", ffmpeg=command(source, output.name, recipe))
        return report
    require_filters(recipe)
    if check:
        args = command(source, None, recipe, seconds)
        done = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if done.returncode:
            raise EditError(done.stderr[-4000:] or "The Conversion Check Failed.")
        report.update(wrote="Nothing. The Picture Conversion Ran Into A Null Sink.", frames=frames_done(done.stdout))
        return report
    with tempfile.TemporaryDirectory(prefix="social-cut-", dir=output.parent) as tmp:
        work = Path(tmp)
        done = subprocess.run(command(source, "working.mp4", recipe), cwd=work, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if done.returncode:
            raise EditError(done.stderr[-4000:] or "The Working Copy Conversion Failed.")
        made = probe(work / "working.mp4")
        verify(meta, made, recipe)
        publish_file(work / "working.mp4", output)
    report.update(wrote="A Working Copy For Review. It Is Not An Export Of The Edit.",
                  duration_seconds=made["duration"], frames=frame_total(made["video"]),
                  next_step="Name This File In The Asset's working_copy Field And Keep The Path Field On The Original.")
    return report


def add_arguments(cli):
    cli.add_argument("source", type=Path, help="The Untouched Source Clip. It Is Only Read.")
    cli.add_argument("output", type=Path, help="A New MP4 File For The Working Copy. An Existing File Is Never Replaced.")
    cli.add_argument(AGREEMENT, action="store_true",
                     help="Use After The Owner Agrees To A Working Copy Of This Source. It Does Not Approve Any Export Of An Edit.")
    cli.add_argument("--long-side", type=int, default=LONG_SIDE, metavar="PIXELS",
                     help="Longest Side Of The Working Copy. The Picture Is Never Enlarged. The Default Is 1920.")
    cli.add_argument("--plan", action="store_true", help="Print The Conversion Command And Write Nothing.")
    cli.add_argument("--check", action="store_true",
                     help="Run The Picture Conversion Into A Null Sink And Write Nothing.")
    cli.add_argument("--seconds", type=float, help="With --check, Convert Only This Many Seconds From The Start.")


def run(args):
    return make(args.source, args.output, args.long_side, args.owner_agreed_working_copy, args.plan, args.check,
                args.seconds)


def main(argv=None):
    cli = argparse.ArgumentParser(description="Convert One Untouched Source Clip Into A Standard H.264 Working Copy For Review.")
    add_arguments(cli)
    print(json.dumps(run(cli.parse_args(argv)), indent=2))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EditError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
