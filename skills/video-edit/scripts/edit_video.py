#!/usr/bin/env python3
"""Edit And Review A Social Cut Kit Timeline."""

import argparse
import json
import sys
from pathlib import Path

from example import example
from handoff import otio
from media import analyze, process
from review import review
from timeline import EditError, load, number, prepare, probe, srt, write_new


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True, metavar="COMMAND")
    def command(key, description):
        return commands.add_parser(key, help=description, description=description)
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
                       ("render", "Encode An Owner-Approved MP4.")]:
        cmd = command(name, desc)
        cmd.add_argument("project", type=Path)
        if name in ("handoff", "captions", "render"):
            cmd.add_argument("output", type=Path)
        if name == "review":
            cmd.add_argument("--port", type=int, default=0)
            cmd.add_argument("--no-open", action="store_true", help="Print The Local URL Without Opening A Browser.")
        if name in ("check", "render"):
            cmd.add_argument("--no-burn", action="store_true", help="Omit Burned Captions From The Composition.")
        if name == "render":
            cmd.add_argument("--owner-approved", action="store_true", help="Use After The Owner Reviews This Edit And Approves Export.")
    return cli


def main(argv=None):
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
    if command == "handoff":
        write_new(args.output, json.dumps(otio(model), ensure_ascii=False, indent=2) + "\n")
    elif command == "captions":
        write_new(args.output, srt(model))
    elif command == "check":
        process(model, burn=not args.no_burn)
    elif command == "render":
        process(model, args.output, not args.no_burn)
    print(json.dumps({"command": command, "title": model["title"], "duration_seconds": model["duration"],
                      "fps": model["fps"], "shots": len(model["shots"]),
                      **({"output": str(args.output.resolve())} if hasattr(args, "output") else {})}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (EditError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
