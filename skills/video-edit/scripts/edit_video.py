#!/usr/bin/env python3
"""Edit And Review A Social Cut Kit Timeline."""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

# Resolve's Bundled Python May Start With An Isolated Module Search Path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import loudness
from example import example
from handoff import otio
from media import LAYERS, analyze, missing_tone_filters, mix, process, still
from review import review
from timeline import EditError, load, number, prepare, probe, srt, write_new


WORKFLOWS = {
    "camera": ("camera_transfer.py", "Transfer Pan, Zoom, And Rotation Between Clips."),
    "resolve": ("resolve_native.py", "Build An Editable Timeline Directly In DaVinci Resolve."),
    "post": ("posting.py", "Prepare And Verify A Post Or Scheduled Release."),
    "setup": ("setup_check.py", "Check This Machine For The Tools The Kit Uses."),
    "defaults": ("defaults.py", "Show Or Update The Saved Editing Defaults File."),
}


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True, metavar="COMMAND")
    def command(key, description):
        return commands.add_parser(key, help=description, description=description)
    for key, (_, description) in WORKFLOWS.items():
        command(key, description)
    command("example", "Create A New Self-Contained Example Folder.").add_argument("folder", type=Path)
    command("probe", "Inspect Media Streams.").add_argument("source", type=Path)
    scan = command("analyze", "Locate Silence And Picture Changes.")
    scan.add_argument("source", type=Path)
    scan.add_argument("--silence-db", type=float, default=-40)
    scan.add_argument("--silence-length", type=float, default=.4)
    scan.add_argument("--scene-threshold", type=float, default=.32)
    for name, desc in [("validate", "Check The Project And Probe The Sources."),
                       ("check", "Decode The Composition Into A Null Sink."),
                       ("review", "Open The Local Editable Source Player."),
                       ("handoff", "Write An OpenTimelineIO Cut List."),
                       ("captions", "Write Timed SubRip Captions."),
                       ("still", "Write One Composed Frame As A PNG For Inspection."),
                       ("mix", "Write The Composed Sound As A WAV For Listening Checks."),
                       ("loudness", "Measure The Composed Mix Through A Null Sink."),
                       ("remotion", "Prepare A Remotion Project For Owner Review Without Writing A Video."),
                       ("render", "Encode An Owner-Approved MP4.")]:
        cmd = command(name, desc)
        cmd.add_argument("project", type=Path)
        if name in ("handoff", "captions", "still", "mix", "render"):
            cmd.add_argument("output", type=Path)
        if name == "remotion":
            cmd.add_argument("output", type=Path, metavar="folder", help="A New Folder For The Remotion Project.")
            cmd.add_argument("--allow-hdr", action="store_true",
                             help="Prepare HDR Sources Anyway. Remotion Converts Them Its Own Way, Unlike The Checked Stills.")
            cmd.add_argument("--link-media", action="store_true",
                             help="Hard Link Media Into The Project Where The Disk Allows, Instead Of Copying It.")
        if name == "review":
            cmd.add_argument("--port", type=int, default=0)
            cmd.add_argument("--no-open", action="store_true", help="Print The Local URL Without Opening A Browser.")
        if name in ("check", "still", "render"):
            cmd.add_argument("--no-burn", action="store_true", help="Omit Burned Captions From The Composition.")
        if name == "still":
            cmd.add_argument("--at", type=float, required=True, metavar="SECONDS",
                             help="Edit Time Of The Frame, Snapped To The Nearest Output Frame.")
        if name in ("mix", "loudness"):
            cmd.add_argument("--layer", choices=LAYERS, default="mix",
                             help="The Whole Mix, The Shot Audio Alone, Or The Added Cues Alone.")
            cmd.add_argument("--start", type=float, metavar="SECONDS", help="Start Of A Window In Edit Time.")
            cmd.add_argument("--seconds", type=float, help="Length Of The Window.")
        if name == "loudness":
            cmd.add_argument("--loudness-target", type=float, default=loudness.TARGET_LUFS, metavar="LUFS",
                             help="Integrated Loudness To Plan A Gain Toward. The Default Is -14.")
            cmd.add_argument("--true-peak-ceiling", type=float, default=loudness.CEILING_DBTP, metavar="DBTP",
                             help="Highest True Peak The Planned Gain May Produce. The Default Is -1.5.")
            cmd.add_argument("--cues", action="store_true",
                             help="Compare Each Added Cue With The Speech Under It In A Short Window.")
            cmd.add_argument("--cue-window", type=float, default=3.0, metavar="SECONDS",
                             help="Longest Window Measured At Each Cue. The Default Is 3.")
            cmd.add_argument("--cue-aim", type=float, metavar="DB",
                             help="Also Suggest The Cue Gain That Places It This Many dB From Speech.")
        if name == "render":
            cmd.add_argument("--owner-approved", action="store_true", help="Use After The Owner Reviews This Edit And Approves Export.")
            cmd.add_argument("--loudness-target", type=float, metavar="LUFS",
                             help="Opt In To One Constant Gain On The Whole Mix Toward This Integrated Loudness.")
            cmd.add_argument("--true-peak-ceiling", type=float, metavar="DBTP",
                             help="Highest True Peak The Gain May Produce. The Default Is -1.5.")
            cmd.add_argument("--if-over-ceiling", choices=("refuse", "cap"),
                             help="Refuse The Render, Or Cap The Gain, When The Target Would Pass The Ceiling. The Default Is refuse.")
    return cli


def remotion_project(project, folder, allow_hdr, link_media):
    """Hand A Validated Timeline To The Node Adapter. It Writes Project Files And Media Copies, Never A Video."""
    node = shutil.which("node")
    if not node:
        raise EditError("Install Node.js And Add It To PATH To Prepare A Remotion Project.")
    script = Path(__file__).resolve().parents[1] / "remotion" / "prepare-remotion.cjs"
    flags = (["--allow-hdr"] if allow_hdr else []) + (["--link-media"] if link_media else [])
    result = subprocess.run([node, str(script), str(project), str(folder), "--json", *flags],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise EditError(result.stderr.strip()[-4000:] or "Remotion Project Preparation Failed.")
    report = json.loads(result.stdout)
    notes = report.pop("warnings", [])
    wanted = ("composition", "frames", "overlays", "audio_cues", "captions", "media_files")
    extra = {key: report[key] for key in wanted}
    extra["next_steps"] = ["npm install", "npm run studio", "Owner Reviews The Whole Cut In Remotion Studio",
                           "npm run render-reviewed -- Approved-Cut.mp4"]
    return extra, notes


def window(args, model):
    if (args.start is None) != (args.seconds is None):
        raise EditError("Supply Both --start And --seconds For A Window.")
    if args.start is not None:
        number(args.start, "Window Start", 0, model["duration"])
        number(args.seconds, "Window Length", .001, model["duration"])
    return args.start, args.seconds


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in WORKFLOWS:
        script, _ = WORKFLOWS[argv[0]]
        return subprocess.run([sys.executable, str(Path(__file__).with_name(script)), *argv[1:]]).returncode
    args = parser().parse_args(argv)
    command = args.command
    if command == "render" and not args.owner_approved:
        raise EditError("Open The Editable Timeline For Owner Review. Render Requires Explicit Owner Approval For This Edit.")
    if command == "example":
        print(example(args.folder))
        return
    if command == "probe":
        print(json.dumps(probe(args.source.resolve()), indent=2))
        return
    if command == "analyze":
        number(args.silence_db, "Silence Threshold", -120, 0)
        number(args.silence_length, "Silence Length", .001, 600)
        number(args.scene_threshold, "Scene Threshold", .001, 1)
        print(json.dumps(analyze(args.source.resolve(), args.silence_db, args.silence_length, args.scene_threshold), indent=2))
        return
    project = args.project.resolve()
    if command == "review":
        if not 0 <= args.port <= 65535:
            raise EditError("Choose A Port Between 0 And 65535.")
        review(project, args.port, not args.no_open)
        return
    model = prepare(load(project), project.parent)
    extra, warnings = {}, list(model["warnings"])
    if command == "validate":
        missing = missing_tone_filters(model)
        if missing:
            warnings.append(f"This FFmpeg Build Lacks {' And '.join(missing)}. Check, Still, And Render Stop On The "
                            "Tone Mapped Shots Until A Build With zscale And tonemap Is Installed Or tone_map Is "
                            "Set To false.")
    elif command == "handoff":
        write_new(args.output, json.dumps(otio(model), ensure_ascii=False, indent=2) + "\n")
    elif command == "captions":
        write_new(args.output, srt(model))
    elif command == "check":
        process(model, burn=not args.no_burn)
    elif command == "still":
        number(args.at, "Still Time", 0, model["duration"])
        extra = still(model, args.at, args.output, not args.no_burn)
    elif command == "mix":
        extra = mix(model, args.output, args.layer, *window(args, model))
    elif command == "loudness":
        start, seconds = window(args, model)
        extra = loudness.report(model, args.loudness_target, args.true_peak_ceiling, args.layer, start, seconds,
                                args.cues, args.cue_window, args.cue_aim)
    elif command == "remotion":
        extra, notes = remotion_project(project, args.output.resolve(), args.allow_hdr, args.link_media)
        warnings += notes
    elif command == "render":
        if args.loudness_target is None:
            if args.true_peak_ceiling is not None or args.if_over_ceiling is not None:
                raise EditError("Add --loudness-target To Use The Ceiling Options.")
            process(model, args.output, not args.no_burn)
        else:
            ceiling = loudness.CEILING_DBTP if args.true_peak_ceiling is None else args.true_peak_ceiling
            extra = {"loudness": loudness.render(model, args.output, not args.no_burn, args.loudness_target,
                                                 ceiling, args.if_over_ceiling or "refuse")}
    summary = {"command": command, "title": model["title"], "duration_seconds": model["duration"],
               "fps": model["fps"], "shots": len(model["shots"]),
               **({"output": str(args.output.resolve())} if hasattr(args, "output") else {}), **extra}
    if warnings:
        summary["warnings"] = warnings
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EditError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
