#!/usr/bin/env python3
"""Show Or Update The Saved Editing Defaults File."""

import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import sys
import tempfile

FILENAME = "video-edit.md"
SECTIONS = ("Where Videos Are Posted", "Usual Length", "Music And Effects", "Hook Headlines", "Caption Style",
            "Editor", "Export Approval", "Asset Libraries", "Habits")
INTRO = ("# Video Edit Defaults\n\n"
         "The Video Edit Skill Reads These Free-Form Notes At The Start Of A Session. "
         "Current Instructions Always Override Them. Edit Or Delete Any Line.\n")


def defaults_path():
    """The Defaults File Lives In The User's Home Folder Unless SOCIAL_CUT_KIT_HOME Names Another Folder."""
    root = os.environ.get("SOCIAL_CUT_KIT_HOME")
    folder = Path(root).expanduser() if root else Path.home() / ".social-cut-kit"
    return folder / FILENAME


def template():
    return INTRO + "".join(f"\n## {name}\n" for name in SECTIONS)


def read(path):
    try:
        return path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        return None


def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent,
                                     prefix=".defaults-", suffix=".tmp", delete=False) as staged:
        staged.write(content)
        staged_path = Path(staged.name)
    try:
        os.replace(staged_path, path)
    finally:
        staged_path.unlink(missing_ok=True)


def add_note(content, note, section, today=None):
    """Place One Dated Line At The End Of A Section, Creating The Section When It Is Absent."""
    note = " ".join(note.split())
    section = " ".join(section.split())
    if not note or not section:
        raise ValueError("Supply The Text To Record And A Section Name.")
    line = f"- {(today or date.today()).isoformat()}: {note}"
    lines = content.rstrip("\n").split("\n")
    heading = re.compile(r"#{1,6}\s+(.*?)\s*#*\s*$")
    start = next((i for i, text in enumerate(lines)
                  if heading.match(text) and heading.match(text)[1].casefold() == section.casefold()), None)
    if start is None:
        return "\n".join(lines + ["", f"## {section}", "", line]) + "\n"
    end = next((i for i in range(start + 1, len(lines)) if heading.match(lines[i])), len(lines))
    body = lines[start + 1:end]
    while body and not body[-1].strip():
        body.pop()
    while body and not body[0].strip():
        body.pop(0)
    rest = [""] + lines[end:] if end < len(lines) else []
    return "\n".join(lines[:start + 1] + [""] + body + [line] + rest) + "\n"


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--init", action="store_true",
                     help="Create The File With Empty Headings When It Does Not Exist. An Existing File Is Kept.")
    cli.add_argument("--add", metavar="TEXT", help="Record One Dated Line, Such As A Habit The User Asked To Keep.")
    cli.add_argument("--section", default="Habits", help="Heading That Receives The Added Line. The Default Is Habits.")
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    path = defaults_path()
    try:
        content = read(path)
        changed = None
        if args.init and content is None:
            content, changed = template(), "Created The Defaults File With Empty Headings."
        if args.add is not None:
            content = add_note(content if content is not None else template(), args.add, args.section)
            changed = f"Recorded One Line Under {' '.join(args.section.split())}."
        if changed:
            save(path, content)
        result = {"path": str(path), "exists": content is not None, "content": content}
        if changed:
            result["changed"] = changed
        elif content is None:
            result["note"] = "No Saved Defaults Yet. Use --init To Create The File Or --add To Record A Habit."
        # ASCII-Safe JSON Survives Any Console Encoding. Parse It To Recover The Original Characters.
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, UnicodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
